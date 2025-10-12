"""
해양쓰레기 수거 네비게이션 분석 도구 (최적화 버전)
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
        
    def load_data(self, limit_files=None):
        """데이터 로드"""
        all_data = []
        folders = [f for f in self.base_path.iterdir() if f.is_dir()]
        
        for folder in folders:
            print(f"\n{folder.name}")
            csv_files = list(folder.glob("*.csv"))
            if limit_files:
                csv_files = csv_files[:limit_files]
            
            for file in csv_files:
                try:
                    df = pd.read_csv(file)
                    df['folder'] = folder.name
                    df['file'] = file.name
                    all_data.append(df)
                except:
                    pass
        
        if all_data:
            self.df = pd.concat(all_data, ignore_index=True)
            self.df['datetime'] = pd.to_datetime(self.df['datetime'])
            self.df['time_hour'] = self.df['datetime'].dt.hour
            print(f"\n✓ 총 {len(self.df):,}개 로드")
            return self.df
        return None
    
    def calculate_risk(self, lat, lon, hour=None):
        """위험도 계산"""
        mask = (
            (self.df['lat'] >= lat - 0.01) & (self.df['lat'] <= lat + 0.01) &
            (self.df['lon'] >= lon - 0.01) & (self.df['lon'] <= lon + 0.01)
        )
        if hour is not None:
            mask &= (self.df['time_hour'] == hour)
        
        data = self.df[mask]
        if len(data) == 0:
            return 0
        
        return min((len(data) / 10 + data['sog'].mean() * 5), 100)
    
    def create_simple_map(self, output_file="simple_map.html"):
        """간단한 지도 (빠른 버전)"""
        print("\n지도 생성 중...")
        
        m = folium.Map(
            location=[self.df['lat'].mean(), self.df['lon'].mean()],
            zoom_start=9, tiles='OpenStreetMap'
        )
        
        colors = {'TS_01.자망': 'red', 'TS_02.안강망': 'blue', 'TS_03.채낚기': 'green',
                 'TS_04.연승': 'purple', 'TS_05.통발': 'orange', 'TS_06.트롤': 'darkred', 'TS_07.선망': 'darkblue'}
        
        # 파일별로 처리
        files = self.df.groupby(['folder', 'file'])
        total = len(files)
        
        print(f"  총 {total}개 파일 처리")
        
        for i, ((folder, file), group) in enumerate(files, 1):
            print(f"  [{i}/{total}] {folder.split('.')[1]}", end='\r')
            
            df = group.sort_values('datetime')
            if len(df) < 2:
                continue
            
            coords = [[r['lat'], r['lon']] for _, r in df.iterrows()]
            
            folium.PolyLine(
                coords,
                color=colors.get(folder, 'gray'),
                weight=2,
                opacity=0.6,
                popup=f"{folder.split('.')[1]}<br>{len(coords)}개 포인트"
            ).add_to(m)
        
        print(f"\n  ✓ 저장: {output_file}")
        m.save(output_file)
        return m
    
    def create_heatmap(self, hour=None, output_file="heatmap.html"):
        """히트맵"""
        print(f"\n히트맵 생성 (시간: {hour if hour else '전체'})")
        
        m = folium.Map(
            location=[self.df['lat'].mean(), self.df['lon'].mean()],
            zoom_start=9
        )
        
        df = self.df[self.df['time_hour'] == hour] if hour else self.df
        heat = [[r['lat'], r['lon']] for _, r in df.iterrows()]
        
        plugins.HeatMap(heat, radius=20, blur=30).add_to(m)
        
        print(f"  ✓ 저장: {output_file}")
        m.save(output_file)
        return m
    
    def plan_route(self, s_lat, s_lon, t_lat, t_lon, hour=None, output_file="route.html"):
        """경로 계획"""
        print(f"\n경로 분석 중...")
        
        # 위험도 계산
        risks = []
        waypoints = []
        for i in range(11):
            r = i / 10
            lat = s_lat + (t_lat - s_lat) * r
            lon = s_lon + (t_lon - s_lon) * r
            risk = self.calculate_risk(lat, lon, hour)
            risks.append(risk)
            waypoints.append([lat, lon])
        
        avg = np.mean(risks)
        
        if avg < 30:
            safety, color = "안전 ✅", "green"
        elif avg < 60:
            safety, color = "주의 ⚠️", "orange"
        else:
            safety, color = "위험 ⛔", "red"
        
        print(f"  위험도: {avg:.1f} | {safety}")
        
        # 최적 시간 찾기
        best = []
        for h in range(24):
            h_risks = [self.calculate_risk(
                s_lat + (t_lat - s_lat) * i/10,
                s_lon + (t_lon - s_lon) * i/10, h
            ) for i in range(11)]
            best.append((h, np.mean(h_risks)))
        
        best.sort(key=lambda x: x[1])
        
        print("  추천 시간:")
        for h, r in best[:3]:
            print(f"    {h:02d}:00 (위험 {r:.1f})")
        
        # 지도 생성
        m = folium.Map(
            location=[(s_lat + t_lat)/2, (s_lon + t_lon)/2],
            zoom_start=10
        )
        
        folium.Marker([s_lat, s_lon], popup="출발", icon=folium.Icon(color='green')).add_to(m)
        folium.Marker([t_lat, t_lon], popup="목표", icon=folium.Icon(color='red')).add_to(m)
        folium.PolyLine(waypoints, color=color, weight=4).add_to(m)
        
        info = f'''
        <div style="position:fixed; top:10px; right:10px; width:280px; 
                    background:white; border:3px solid {color}; border-radius:8px; 
                    padding:20px; z-index:9999;">
        <h2 style="color:{color};">경로 분석</h2>
        <h3>{safety}</h3>
        <p><b>평균 위험도:</b> {avg:.1f}/100</p>
        <hr>
        <h4>추천 시간</h4>
        <ol>
        {"".join([f"<li>{h:02d}:00 (위험 {r:.1f})</li>" for h, r in best[:3]])}
        </ol>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(info))
        
        print(f"  ✓ 저장: {output_file}")
        m.save(output_file)
        return m


def main():
    base_path = r"E:\sohyeon_project\133.어선 조업패턴 항적 데이터\3.개방데이터\1.데이터\Training\01.원천데이터"
    
    print("="*60)
    print("🌊 해양쓰레기 수거 네비게이션 (빠른 버전)")
    print("="*60)
    
    nav = MarineDebrisNavigator(base_path)
    
    limit = int(input("\n각 폴더당 파일 수: "))
    df = nav.load_data(limit)
    
    if df is None:
        print("데이터 로드 실패")
        return
    
    out_dir = Path("C:/Temp")
    
    while True:
        print("\n\n📊 메뉴")
        print("-"*60)
        print("[1] 전체 경로 지도")
        print("[2] 히트맵")
        print("[3] 경로 시뮬레이션")
        print("[0] 종료")
        print("-"*60)
        
        choice = input("선택: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            nav.create_simple_map(str(out_dir / "route_map.html"))
            print(f"\n✅ 완료! C:/Temp/route_map.html 확인하세요")
        elif choice == '2':
            h = input("시간 (0-23, 전체=Enter): ").strip()
            hour = int(h) if h else None
            nav.create_heatmap(hour, str(out_dir / f"heat_{hour if hour else 'all'}.html"))
            print(f"\n✅ 완료!")
        elif choice == '3':
            print("\n출발지:")
            s_lat = float(input("  위도: "))
            s_lon = float(input("  경도: "))
            print("목표지:")
            t_lat = float(input("  위도: "))
            t_lon = float(input("  경도: "))
            h = input("시간 (0-23, 미정=Enter): ").strip()
            hour = int(h) if h else None
            nav.plan_route(s_lat, s_lon, t_lat, t_lon, hour, str(out_dir / "route_plan.html"))
            print(f"\n✅ 완료! C:/Temp/route_plan.html 확인하세요")
    
    print("\n프로그램 종료 🌊")


if __name__ == "__main__":
    main()
