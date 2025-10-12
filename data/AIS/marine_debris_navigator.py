"""
AIS 기반 해양쓰레기 수거 네비게이션 분석 도구
시간대별 분석 + 위험도 평가 + 최적 경로 추천
"""

import pandas as pd
import folium
from folium import plugins
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class MarineDebrisNavigator:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.df = None
        
    def load_data(self, folder_name=None, limit_files=None):
        """CSV 데이터 로드"""
        all_data = []
        
        if folder_name:
            folders = [self.base_path / folder_name]
        else:
            folders = [f for f in self.base_path.iterdir() if f.is_dir()]
        
        for folder in folders:
            print(f"\n처리중: {folder.name}")
            csv_files = list(folder.glob("*.csv"))
            
            if len(csv_files) == 0:
                continue
            
            if limit_files:
                csv_files = csv_files[:limit_files]
            
            print(f"  로드: {len(csv_files)}개 파일")
            
            for i, file in enumerate(csv_files):
                try:
                    df = pd.read_csv(file)
                    df['folder'] = folder.name
                    df['file'] = file.name
                    all_data.append(df)
                    
                    if (i + 1) % 20 == 0:
                        print(f"    {i + 1}개 완료")
                        
                except Exception as e:
                    pass
        
        if all_data:
            self.df = pd.concat(all_data, ignore_index=True)
            # datetime 파싱
            self.df['datetime'] = pd.to_datetime(self.df['datetime'])
            self.df['date'] = self.df['datetime'].dt.date
            self.df['time_hour'] = self.df['datetime'].dt.hour
            self.df['weekday'] = self.df['datetime'].dt.dayofweek
            
            print(f"\n총 {len(self.df):,}개 데이터 로드 완료")
            return self.df
        return None
    
    def calculate_risk_score(self, lat, lon, time_hour=None, grid_size=0.01):
        """특정 위치의 위험도 점수 계산"""
        mask = (
            (self.df['lat'] >= lat - grid_size) & 
            (self.df['lat'] <= lat + grid_size) &
            (self.df['lon'] >= lon - grid_size) & 
            (self.df['lon'] <= lon + grid_size)
        )
        
        if time_hour is not None:
            mask = mask & (self.df['time_hour'] == time_hour)
        
        grid_data = self.df[mask]
        
        if len(grid_data) == 0:
            return 0
        
        density = len(grid_data)
        avg_speed = grid_data['sog'].mean()
        
        density_score = min(density / 10, 50)
        speed_score = min(avg_speed * 5, 50)
        total_score = density_score + speed_score
        
        return min(total_score, 100)
    
    def create_time_analysis_map(self, output_file="navigation_time_analysis.html"):
        """시간대별 분석 지도 생성"""
        print("\n시간대별 분석 지도 생성 중...")
        
        center_lat = self.df['lat'].mean()
        center_lon = self.df['lon'].mean()
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=9,
            tiles='OpenStreetMap'
        )
        
        # 시간대별 레이어
        time_groups = {}
        for hour in range(24):
            time_groups[hour] = folium.FeatureGroup(name=f'{hour:02d}:00', show=False)
        
        all_layer = folium.FeatureGroup(name='전체 경로', show=True)
        
        folder_colors = {
            'TS_01.자망': '#FF4444',
            'TS_02.안강망': '#4444FF', 
            'TS_03.채낚기': '#44FF44',
            'TS_04.연승': '#FF44FF',
            'TS_05.통발': '#FFAA44',
            'TS_06.트롤': '#AA4444',
            'TS_07.선망': '#4444AA'
        }
        
        print("  경로 처리 중...")
        
        processed = 0
        for (folder, file), group in self.df.groupby(['folder', 'file']):
            if processed >= 150:
                break
                
            file_df = group.sort_values('datetime')
            if len(file_df) < 2:
                continue
            
            color = folder_colors.get(folder, '#888888')
            coordinates = [[row['lat'], row['lon']] for _, row in file_df.iterrows()]
            
            popup_html = f"""
            <b>{folder.split('.')[1]}</b><br>
            포인트: {len(coordinates)}개<br>
            시작: {file_df.iloc[0]['datetime']}<br>
            속도: {file_df['sog'].mean():.1f} knots
            """
            
            folium.PolyLine(
                coordinates, color=color, weight=2, opacity=0.5,
                popup=popup_html
            ).add_to(all_layer)
            
            for _, row in file_df.iterrows():
                folium.CircleMarker(
                    [row['lat'], row['lon']], radius=3,
                    popup=f"{row['datetime']}<br>{row['sog']:.1f}kt",
                    tooltip=f"{row['datetime'].strftime('%H:%M')}",
                    color=color, fill=True, fillOpacity=0.6
                ).add_to(time_groups[row['time_hour']])
            
            processed += 1
        
        all_layer.add_to(m)
        for group in time_groups.values():
            group.add_to(m)
        
        folium.LayerControl(collapsed=False).add_to(m)
        
        legend_html = '''
        <div style="position:fixed; bottom:50px; right:50px; width:250px; 
                    background:white; z-index:9999; border:2px solid #333; 
                    border-radius:8px; padding:15px; font-family:Arial;">
        <h3 style="margin:0 0 10px 0;">🗺️ 조업 유형</h3>
        '''
        for folder, color in folder_colors.items():
            legend_html += f'<p style="margin:5px 0;"><span style="color:{color};">●</span> {folder.split(".")[1]}</p>'
        legend_html += '''
        <hr><h4>💡 사용법</h4>
        <ul style="font-size:11px; padding-left:20px;">
        <li>레이어로 시간대 선택</li>
        <li>마커 클릭/마우스 올리기</li>
        </ul></div>'''
        
        m.get_root().html.add_child(folium.Element(legend_html))
        m.save(output_file)
        print(f"  ✓ 저장: {output_file}")
        return m
    
    def create_risk_heatmap(self, output_file="risk_map.html", time_hour=None):
        """위험도 히트맵"""
        print(f"\n위험도 히트맵 생성... (시간: {time_hour if time_hour is not None else '전체'})")
        
        m = folium.Map(
            location=[self.df['lat'].mean(), self.df['lon'].mean()],
            zoom_start=9, tiles='OpenStreetMap'
        )
        
        heat_df = self.df[self.df['time_hour'] == time_hour] if time_hour is not None else self.df
        heat_data = [[r['lat'], r['lon']] for _, r in heat_df.iterrows()]
        
        plugins.HeatMap(
            heat_data, radius=20, blur=30, max_zoom=13,
            gradient={0.0: 'blue', 0.5: 'lime', 0.75: 'yellow', 1.0: 'red'}
        ).add_to(m)
        
        info = f'''
        <div style="position:fixed; top:10px; left:50px; width:300px;
                    background:white; z-index:9999; border:3px solid #e74c3c;
                    border-radius:8px; padding:20px;">
        <h2 style="margin:0; color:#e74c3c;">⚠️ 어선 밀집도</h2><hr>
        <b>시간:</b> {f"{time_hour:02d}:00" if time_hour is not None else "전체"}<br>
        <b>데이터:</b> {len(heat_data):,}개<br><br>
        <b>색상:</b><br>
        🔵 안전 | 🟢 주의 | 🟡 경계 | 🔴 위험
        </div>'''
        
        m.get_root().html.add_child(folium.Element(info))
        m.save(output_file)
        print(f"  ✓ 저장: {output_file}")
        return m
    
    def create_hourly_comparison(self, output_file="hourly_comparison.html"):
        """24시간 비교"""
        print("\n24시간 비교 맵 생성...")
        
        m = folium.Map(
            location=[self.df['lat'].mean(), self.df['lon'].mean()],
            zoom_start=9, tiles='OpenStreetMap'
        )
        
        periods = [
            (0, 4, "🌙 심야", True), (4, 8, "🌅 새벽", False),
            (8, 12, "☀️ 오전", False), (12, 16, "🌤️ 오후", False),
            (16, 20, "🌆 저녁", False), (20, 24, "🌃 밤", False)
        ]
        
        for start, end, label, show in periods:
            period_df = self.df[(self.df['time_hour'] >= start) & (self.df['time_hour'] < end)]
            heat_data = [[r['lat'], r['lon']] for _, r in period_df.iterrows()]
            
            fg = folium.FeatureGroup(name=label, show=show)
            plugins.HeatMap(heat_data, radius=18, blur=28).add_to(fg)
            fg.add_to(m)
        
        folium.LayerControl(collapsed=False).add_to(m)
        
        info = '''
        <div style="position:fixed; top:10px; left:50px; width:280px;
                    background:white; z-index:9999; border:3px solid #3498db;
                    border-radius:8px; padding:20px;">
        <h2 style="color:#3498db;">⏰ 시간대별 활동</h2><hr>
        레이어에서 시간대를 선택하여 비교하세요!<br><br>
        💡 심야/새벽이 가장 안전합니다.
        </div>'''
        
        m.get_root().html.add_child(folium.Element(info))
        m.save(output_file)
        print(f"  ✓ 저장: {output_file}")
        return m
    
    def find_optimal_route(self, start_lat, start_lon, target_lat, target_lon, departure_hour=None):
        """최적 경로 분석"""
        print(f"\n경로 분석: ({start_lat:.4f},{start_lon:.4f}) → ({target_lat:.4f},{target_lon:.4f})")
        
        waypoints = []
        for i in range(16):
            ratio = i / 15
            lat = start_lat + (target_lat - start_lat) * ratio
            lon = start_lon + (target_lon - start_lon) * ratio
            risk = self.calculate_risk_score(lat, lon, departure_hour)
            waypoints.append({'lat': lat, 'lon': lon, 'risk': risk})
        
        avg_risk = np.mean([w['risk'] for w in waypoints])
        max_risk = np.max([w['risk'] for w in waypoints])
        
        if avg_risk < 20:
            safety, color = "매우 안전 ✅", "green"
        elif avg_risk < 40:
            safety, color = "안전 ✔️", "lightgreen"
        elif avg_risk < 60:
            safety, color = "주의 ⚠️", "orange"
        else:
            safety, color = "위험 ⛔", "red"
        
        print(f"  평균 위험도: {avg_risk:.1f} | 최대: {max_risk:.1f} | {safety}")
        
        best_hours = []
        if avg_risk > 30 or departure_hour is None:
            for hour in range(24):
                risks = [self.calculate_risk_score(
                    start_lat + (target_lat - start_lat) * i/15,
                    start_lon + (target_lon - start_lon) * i/15,
                    hour
                ) for i in range(16)]
                best_hours.append((hour, np.mean(risks)))
            
            best_hours.sort(key=lambda x: x[1])
            print("  추천 시간대:")
            for i, (h, r) in enumerate(best_hours[:3], 1):
                print(f"    {i}. {h:02d}:00 (위험도 {r:.1f})")
        
        return {
            'waypoints': waypoints, 'avg_risk': avg_risk, 'max_risk': max_risk,
            'safety_level': safety, 'color': color, 'best_hours': best_hours[:5] if best_hours else None
        }
    
    def create_route_planning_map(self, start_lat, start_lon, target_lat, target_lon,
                                  departure_hour=None, output_file="route_planning.html"):
        """경로 계획 지도"""
        print("\n경로 계획 지도 생성...")
        
        route = self.find_optimal_route(start_lat, start_lon, target_lat, target_lon, departure_hour)
        
        m = folium.Map(
            location=[(start_lat + target_lat)/2, (start_lon + target_lon)/2],
            zoom_start=10, tiles='OpenStreetMap'
        )
        
        folium.Marker([start_lat, start_lon], popup="🚢 출발지",
                     icon=folium.Icon(color='green', icon='play', prefix='fa')).add_to(m)
        folium.Marker([target_lat, target_lon], popup="🎯 목표지",
                     icon=folium.Icon(color='red', icon='trash', prefix='fa')).add_to(m)
        
        coords = [[w['lat'], w['lon']] for w in route['waypoints']]
        folium.PolyLine(coords, color=route['color'], weight=5, opacity=0.8,
                       popup=f"경로 - {route['safety_level']}").add_to(m)
        
        for wp in route['waypoints']:
            c = 'green' if wp['risk'] < 30 else 'orange' if wp['risk'] < 60 else 'red'
            folium.CircleMarker([wp['lat'], wp['lon']], radius=8,
                              popup=f"위험도: {wp['risk']:.1f}", color=c,
                              fill=True, fillOpacity=0.7).add_to(m)
        
        best_hours_html = ""
        if route['best_hours']:
            best_hours_html = "<hr><h4>🕐 추천 시간</h4><ol style='font-size:12px;'>"
            for h, r in route['best_hours']:
                best_hours_html += f"<li>{h:02d}:00 (위험 {r:.1f})</li>"
            best_hours_html += "</ol>"
        
        info = f'''
        <div style="position:fixed; top:10px; right:10px; width:340px;
                    background:white; z-index:9999; border:4px solid {route['color']};
                    border-radius:10px; padding:20px; font-family:Arial;">
        <h2 style="color:{route['color']}; text-align:center;">🧭 경로 분석</h2>
        <div style="background:linear-gradient(135deg,#667eea,#764ba2); color:white;
                    padding:15px; border-radius:8px; margin:10px 0; text-align:center;">
        <h3 style="margin:0;">{route['safety_level']}</h3>
        </div>
        <table style="width:100%; font-size:13px;">
        <tr style="background:#f8f9fa;"><td style="padding:8px;"><b>평균 위험도</b></td>
        <td style="text-align:right; padding:8px;"><b>{route['avg_risk']:.1f}/100</b></td></tr>
        <tr><td style="padding:8px;"><b>최대 위험도</b></td>
        <td style="text-align:right; padding:8px;"><b>{route['max_risk']:.1f}/100</b></td></tr>
        <tr style="background:#f8f9fa;"><td style="padding:8px;"><b>출발 시간</b></td>
        <td style="text-align:right; padding:8px;"><b>{f"{departure_hour:02d}:00" if departure_hour else "미정"}</b></td></tr>
        </table>
        {best_hours_html}
        <div style="margin-top:15px; padding:12px; background:{'#d4edda' if route['avg_risk']<40 else '#fff3cd'};
                    border-radius:5px; border-left:5px solid {'#28a745' if route['avg_risk']<40 else '#ffc107'};">
        <b>💡 권장:</b><br>
        {('안전한 경로입니다!' if route['avg_risk']<40 else '다른 시간대 고려를 권장합니다.')}
        </div>
        </div>'''
        
        m.get_root().html.add_child(folium.Element(info))
        m.save(output_file)
        print(f"  ✓ 저장: {output_file}")
        return m, route


def main():
    base_path = r"E:\sohyeon_project\133.어선 조업패턴 항적 데이터\3.개방데이터\1.데이터\Training\01.원천데이터"
    
    print("="*60)
    print("🌊 해양쓰레기 수거 네비게이션 분석 도구")
    print("="*60)
    
    navigator = MarineDebrisNavigator(base_path)
    
    limit = int(input("\n각 폴더당 파일 수 (권장 10-20): "))
    df = navigator.load_data(limit_files=limit)
    
    if df is None or len(df) == 0:
        print("\n데이터 로드 실패")
        return
    
    output_dir = Path("C:/Temp")
    
    print(f"\n{'='*60}")
    print(f"데이터: {len(df):,}개 | 조업: {df['folder'].nunique()}개")
    print(f"기간: {df['date'].min()} ~ {df['date'].max()}")
    print(f"{'='*60}")
    
    while True:
        print("\n\n📊 메뉴")
        print("-"*60)
        print("[1] 시간대별 분석 지도")
        print("[2] 위험도 히트맵")
        print("[3] 24시간 비교")
        print("[4] 경로 계획 시뮬레이션")
        print("[5] 모두 생성")
        print("[0] 종료")
        print("-"*60)
        
        choice = input("선택: ").strip()
        
        if choice == '0':
            print("\n종료합니다.")
            break
            
        elif choice == '1':
            navigator.create_time_analysis_map(str(output_dir / "time_analysis.html"))
            
        elif choice == '2':
            hour_input = input("시간 (0-23, 전체=Enter): ").strip()
            hour = int(hour_input) if hour_input else None
            navigator.create_risk_heatmap(
                str(output_dir / f"risk_{hour if hour else 'all'}.html"), hour)
            
        elif choice == '3':
            navigator.create_hourly_comparison(str(output_dir / "hourly_comparison.html"))
            
        elif choice == '4':
            print("\n🎯 경로 시뮬레이션")
            s_lat = float(input("출발 위도: "))
            s_lon = float(input("출발 경도: "))
            t_lat = float(input("목표 위도: "))
            t_lon = float(input("목표 경도: "))
            h_input = input("출발 시간 (0-23, 미정=Enter): ").strip()
            hour = int(h_input) if h_input else None
            navigator.create_route_planning_map(
                s_lat, s_lon, t_lat, t_lon, hour,
                str(output_dir / "route_planning.html"))
            
        elif choice == '5':
            print("\n모든 지도 생성 중...")
            navigator.create_time_analysis_map(str(output_dir / "time_analysis.html"))
            navigator.create_risk_heatmap(str(output_dir / "risk_all.html"))
            navigator.create_hourly_comparison(str(output_dir / "hourly_comparison.html"))
            print("\n✅ 모든 지도 생성 완료!")
            print(f"저장 위치: {output_dir}")
        
        else:
            print("잘못된 선택입니다.")
    
    print(f"\n{'='*60}")
    print("프로그램을 종료합니다. 좋은 하루 되세요! 🌊")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
