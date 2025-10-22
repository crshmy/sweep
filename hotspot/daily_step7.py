# -*- coding: utf-8 -*-
"""
Step 6-Extended: 실제 지도 위에 경로/핫스팟 오버레이 (Folium)
- 기준 앵커(위도 34.919, 경도 129.1212)로 km 오프셋을 위경도로 변환
- 전체 평행이동 지원: SHIFT_X_KM (동+ / 서-), SHIFT_Y_KM (북+ / 남-)
"""

import os
import json
import math
import pandas as pd
import numpy as np
import folium
from folium import plugins
from typing import Optional


BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
FINAL_DIR  = os.path.join(BASE_DIR, "daily_results_final_251013")
ROUTE_DIR  = os.path.join(BASE_DIR, "daily_results_route_251013")

XLSX_PATH  = os.path.join(DATA_DIR, "대한해협.xlsx")  # 선택적

# ==== 파일 이름 (Step6 산출물 표준) ====
ROUTE_WAYPOINTS_CSV = os.path.join(ROUTE_DIR, "route_hybrid_waypoints.csv")
ROUTE_GEOJSON       = os.path.join(ROUTE_DIR, "route_hybrid.geojson")
OUTPUT_HTML         = os.path.join(ROUTE_DIR, "route_hybrid_interactive_map.html")
HOTSPOTS_JSON       = os.path.join(FINAL_DIR, "hotspots.json")

# ==== 기준 앵커(실제 현장 포인트) ====
BASE_LAT = 34.919
BASE_LON = 129.1212

# ==== 평행이동 (km) — 필요에 따라 조정하세요 ====
# 동쪽(+) / 서쪽(-)
SHIFT_X_KM = 15.0
# 북쪽(+) / 남쪽(-)  ← 요청: 더 위로 올리기 → 기본 +28km
SHIFT_Y_KM = +20.0


def create_interactive_map(
    geojson_path: Optional[str],
    csv_path: str,
    output_html: str,
    # 보기용 맵 초기 중심 (계산에는 사용하지 않음)
    center_lat: float = BASE_LAT,
    center_lon: float = BASE_LON,
    hotspots_json: Optional[str] = None,
    # 좌표계 보정
    base_lat: float = BASE_LAT,
    base_lon: float = BASE_LON,
    swap_xy: bool = False,
    invert_x: bool = False,
    invert_y: bool = False,    # ❗요청: 반전하지 않음
    rotation_deg: float = 0.0,
    shift_x_km: float = SHIFT_X_KM,
    shift_y_km: float = SHIFT_Y_KM
):
    """
    CSV의 (x_km, y_km)를 '앵커(base_lat/lon) 기준 동/북 km 오프셋'으로 보고 위경도로 변환해 지도 표시.
    - swap_xy/invert_x/invert_y/rotation_deg: 축/부호/회전 보정
    - shift_x_km/shift_y_km: 전체 평행이동 (동/북 km)
    """
    # 1) CSV 로드 & 컬럼 체크
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"경유지 CSV를 찾을 수 없습니다: {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    required_cols = {'x_km', 'y_km', 'cum_dist_km', 'eta_hour_from_start', 'order'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV에 필요한 컬럼이 없습니다: {missing}")

    # 2) 축/부호/회전 보정
    X = df['x_km'].to_numpy(dtype=float)
    Y = df['y_km'].to_numpy(dtype=float)

    if swap_xy:
        X, Y = Y, X
    if invert_x:
        X = -X
    if invert_y:
        Y = -Y
    if abs(rotation_deg) > 1e-9:
        theta = math.radians(rotation_deg)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        X_rot = cos_t * X - sin_t * Y
        Y_rot = sin_t * X + cos_t * Y
        X, Y = X_rot, Y_rot

    # 2-1) 전체 평행이동 (km)
    X = X + float(shift_x_km)
    Y = Y + float(shift_y_km)

    # 3) km -> 위경도 변환 (앵커 기준)
    #    위도 1km ≈ 1/111 deg, 경도 1km ≈ 1/(111*cos(lat)) deg
    lat_per_km = 1.0 / 111.0
    lon_per_km = 1.0 / (111.0 * math.cos(math.radians(base_lat)))

    df['lat'] = base_lat + (Y * lat_per_km)
    df['lon'] = base_lon + (X * lon_per_km)

    # 4) 지도 생성 (보기 중심은 데이터 평균)
    view_lat = float(np.mean(df['lat'])) if len(df) > 0 else base_lat
    view_lon = float(np.mean(df['lon'])) if len(df) > 0 else base_lon
    m = folium.Map(location=[view_lat, view_lon], zoom_start=11, tiles='OpenStreetMap')

    # 4-1) 기준 앵커 위치 마커(검증용)
    folium.Marker(
        location=[base_lat, base_lon],
        popup=f"기준 앵커 ({base_lat:.6f}, {base_lon:.6f})",
        icon=folium.Icon(color='blue', icon='flag', prefix='fa')
    ).add_to(m)

    # 5) 경로 라인
    route_coords = list(zip(df['lat'], df['lon']))
    folium.PolyLine(route_coords, color='#FF4444', weight=4, opacity=0.8, popup='수거 경로').add_to(m)

    # 6) 시작/경유/종점
    folium.Marker(
        location=[df['lat'].iloc[0], df['lon'].iloc[0]],
        popup=f"<b>출발점</b><br>위경도: ({df['lat'].iloc[0]:.5f}, {df['lon'].iloc[0]:.5f})<br>"
              f"거리 {df['cum_dist_km'].iloc[0]:.2f} km / ETA {df['eta_hour_from_start'].iloc[0]:.2f} h",
        icon=folium.Icon(color='green', icon='play', prefix='fa'),
        tooltip='출발'
    ).add_to(m)

    for idx, row in df.iterrows():
        if idx % 10 == 0 and idx > 0:
            popup_text = (
                f"<b>경유지 #{int(row['order'])}</b><br>"
                f"누적거리: {row['cum_dist_km']:.2f} km<br>"
                f"ETA: {row['eta_hour_from_start']:.2f} h"
            )
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=5, popup=popup_text,
                color='#FFD700', fill=True, fillColor='#FFD700', fillOpacity=0.7
            ).add_to(m)

    folium.Marker(
        location=[df['lat'].iloc[-1], df['lon'].iloc[-1]],
        popup=f"<b>종점</b><br>총 거리: {df['cum_dist_km'].iloc[-1]:.2f} km<br>"
              f"총 시간: {df['eta_hour_from_start'].iloc[-1]:.2f} h",
        icon=folium.Icon(color='red', icon='stop', prefix='fa'),
        tooltip='종점'
    ).add_to(m)

    # 7) 핫스팟 (있을 때 동일 평행이동/보정 적용)
    if hotspots_json and os.path.exists(hotspots_json):
        try:
            with open(hotspots_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            hotspots = data.get('hotspots', [])
            for i, hs in enumerate(hotspots[:15]):  # 상위 15개
                hx = float(hs['x'])
                hy = float(hs['y'])
                # 동일 보정
                if swap_xy:
                    hx, hy = hy, hx
                if invert_x:
                    hx = -hx
                if invert_y:
                    hy = -hy
                if abs(rotation_deg) > 1e-9:
                    theta = math.radians(rotation_deg)
                    cos_t, sin_t = math.cos(theta), math.sin(theta)
                    hx2 = cos_t * hx - sin_t * hy
                    hy2 = sin_t * hx + cos_t * hy
                    hx, hy = hx2, hy2
                # 동일 평행이동
                hx = hx + float(shift_x_km)
                hy = hy + float(shift_y_km)

                hs_lat = base_lat + (hy * lat_per_km)
                hs_lon = base_lon + (hx * lon_per_km)
                folium.Circle(
                    location=[hs_lat, hs_lon],
                    radius=500,  # 500m
                    popup=f"<b>핫스팟 #{i+1}</b><br>강도: {hs.get('value', 0):.2f}",
                    color='orange', fill=True, fillColor='orange', fillOpacity=0.3
                ).add_to(m)
        except Exception as e:
            print(f"[경고] 핫스팟 표시 중 오류: {e}")

    # 8) 히트맵/도구/범례
    heat_data = [[row['lat'], row['lon']] for _, row in df.iterrows()]
    if len(heat_data) >= 2:
        plugins.HeatMap(heat_data, radius=15, blur=25, max_zoom=13).add_to(m)

    plugins.MeasureControl(position='topleft').add_to(m)
    plugins.Fullscreen().add_to(m)

    legend_html = '''
    <div style="position: fixed; bottom: 50px; right: 50px; width: 220px; background: white;
                z-index:9999; font-size:14px; border:2px solid grey; border-radius: 5px; padding: 10px">
        <p style="margin:0"><b>범례</b></p>
        <p style="margin:5px 0"><i class="fa fa-flag" style="color:blue"></i> 기준 앵커</p>
        <p style="margin:5px 0"><i class="fa fa-play" style="color:green"></i> 출발점</p>
        <p style="margin:5px 0"><i class="fa fa-stop" style="color:red"></i> 종점</p>
        <p style="margin:5px 0">🟡 경유지 (10개마다)</p>
        <p style="margin:5px 0">🟠 쓰레기 핫스팟</p>
        <p style="margin:5px 0"><span style="color:#FF4444">━━</span> 수거 경로</p>
        <hr style="margin:6px 0">
        <p style="margin:4px 0">SHIFT_X_KM = ''' + f'{shift_x_km:.1f}' + ''' km</p>
        <p style="margin:4px 0">SHIFT_Y_KM = ''' + f'{shift_y_km:.1f}' + ''' km</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # 9) 저장 & 요약
    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    m.save(output_html)

    print(f"✅ 지도 저장: {output_html}")
    print(f"   - 경유지: {len(df)}개")
    print(f"   - 첫 점(lat,lon): ({df['lat'].iloc[0]:.6f}, {df['lon'].iloc[0]:.6f})")
    print(f"   - 끝 점(lat,lon): ({df['lat'].iloc[-1]:.6f}, {df['lon'].iloc[-1]:.6f})")
    print(f"   - 기준 앵커: ({base_lat:.6f}, {base_lon:.6f})  (파란 깃발로 표시됨)")
    print(f"   - 평행이동: X={shift_x_km:.1f} km, Y={shift_y_km:.1f} km")


def main():
    # 경로/파일 확인
    if not os.path.exists(ROUTE_DIR):
        raise FileNotFoundError(f"ROUTE_DIR이 존재하지 않습니다: {ROUTE_DIR}")
    if not os.path.exists(ROUTE_WAYPOINTS_CSV):
        raise FileNotFoundError(f"경유지 CSV가 없습니다: {ROUTE_WAYPOINTS_CSV}")
    if not os.path.exists(FINAL_DIR):
        print(f"[안내] FINAL_DIR이 없습니다(선택 항목): {FINAL_DIR}")
    if not os.path.exists(ROUTE_GEOJSON):
        print(f"[안내] GeoJSON이 없습니다(선택 항목): {ROUTE_GEOJSON}")
    if not os.path.exists(HOTSPOTS_JSON):
        print(f"[안내] hotspots.json이 없습니다(선택 항목): {HOTSPOTS_JSON}")

    # 지도 생성 (y축 반전 X, 평행이동만 적용)
    create_interactive_map(
        geojson_path=ROUTE_GEOJSON if os.path.exists(ROUTE_GEOJSON) else None,
        csv_path=ROUTE_WAYPOINTS_CSV,
        output_html=OUTPUT_HTML,
        center_lat=BASE_LAT,
        center_lon=BASE_LON,
        hotspots_json=HOTSPOTS_JSON if os.path.exists(HOTSPOTS_JSON) else None,
        base_lat=BASE_LAT,
        base_lon=BASE_LON,
        swap_xy=False,
        invert_x=False,
        invert_y=False,      # ❗반전 금지
        rotation_deg=0.0,
        shift_x_km=SHIFT_X_KM,
        shift_y_km=SHIFT_Y_KM
    )

    print("\n🌊 실제 해양 지도가 생성되었습니다!")
    print(f"   브라우저에서 다음 파일을 열어보세요 → {OUTPUT_HTML}")


if __name__ == "__main__":
    main()