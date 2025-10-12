"""
AIS 기반 해양 안전 네비게이션 시스템
Marine Safety Navigation System based on AIS Data

주요 기능:
- 실시간 어선 경로 시각화
- 날짜별/시간대별 필터링
- 위험도 분석 및 히트맵
- 최적 경로 추천
- 시간대별 안전도 평가

작성자: [이름]
작성일: 2025-10-05
"""

import pandas as pd
import folium
from folium import plugins
from pathlib import Path
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class AISNavigationSystem:
    """AIS 데이터 기반 해양 네비게이션 시스템"""
    
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.df = None
        self.vessel_types = {
            'TS_01.자망': {'color': '#FF4444', 'name': '자망'},
            'TS_02.안강망': {'color': '#4444FF', 'name': '안강망'},
            'TS_03.채낚기': {'color': '#44FF44', 'name': '채낚기'},
            'TS_04.연승': {'color': '#FF44FF', 'name': '연승'},
            'TS_05.통발': {'color': '#FFAA44', 'name': '통발'},
            'TS_06.트롤': {'color': '#AA4444', 'name': '트롤'},
            'TS_07.선망': {'color': '#4444AA', 'name': '선망'}
        }
        
    def load_data(self, limit_files=None):
        """AIS 데이터 로드 및 전처리"""
        print("\n" + "="*60)
        print("📡 AIS 데이터 로딩 중...")
        print("="*60)
        
        all_data = []
        folders = [f for f in self.base_path.iterdir() if f.is_dir()]
        
        for folder in folders:
            vessel_name = self.vessel_types.get(folder.name, {}).get('name', folder.name)
            print(f"\n📂 {vessel_name} 데이터 처리 중...")
            
            csv_files = list(folder.glob("*.csv"))
            if limit_files:
                csv_files = csv_files[:limit_files]
            
            print(f"   파일 수: {len(csv_files)}개")
            
            for i, file in enumerate(csv_files, 1):
                try:
                    df = pd.read_csv(file)
                    df['folder'] = folder.name
                    df['file'] = file.name
                    df['vessel_type'] = vessel_name
                    all_data.append(df)
                    
                    if i % 5 == 0:
                        print(f"   진행: {i}/{len(csv_files)}", end='\r')
                except Exception as e:
                    continue
            
            if csv_files:
                print(f"   ✓ 완료: {len(csv_files)}개 파일 로드")
        
        if not all_data:
            print("\n⚠️ 데이터를 찾을 수 없습니다.")
            return None
        
        # 데이터 통합 및 전처리
        print("\n🔄 데이터 전처리 중...")
        self.df = pd.concat(all_data, ignore_index=True)
        self.df['datetime'] = pd.to_datetime(self.df['datetime'])
        self.df['date'] = self.df['datetime'].dt.date
        self.df['time_hour'] = self.df['datetime'].dt.hour
        self.df['weekday'] = self.df['datetime'].dt.day_name()
        
        # 통계 정보
        print("\n" + "="*60)
        print("📊 데이터 로드 완료")
        print("="*60)
        print(f"총 데이터 포인트: {len(self.df):,}개")
        print(f"조업 유형: {self.df['folder'].nunique()}개")
        print(f"기간: {self.df['date'].min()} ~ {self.df['date'].max()}")
        print(f"위도 범위: {self.df['lat'].min():.4f}° ~ {self.df['lat'].max():.4f}°")
        print(f"경도 범위: {self.df['lon'].min():.4f}° ~ {self.df['lon'].max():.4f}°")
        print("="*60)
        
        return self.df
    
    def analyze_time_safety(self):
        """시간대별 안전도 분석"""
        hourly_data = []
        for hour in range(24):
            hour_df = self.df[self.df['time_hour'] == hour]
            vessel_count = len(hour_df)
            avg_speed = hour_df['sog'].mean() if len(hour_df) > 0 else 0
            
            # 안전도 점수 계산
            safety_score = 100 - min((vessel_count / len(self.df) * 100) * 0.7 + avg_speed * 3, 100)
            
            if safety_score >= 70:
                safety_level = "매우 안전"
            elif safety_score >= 50:
                safety_level = "안전"
            elif safety_score >= 30:
                safety_level = "주의"
            else:
                safety_level = "위험"
            
            hourly_data.append({
                'hour': hour,
                'vessel_count': vessel_count,
                'avg_speed': avg_speed,
                'safety_score': safety_score,
                'safety_level': safety_level
            })
        
        return pd.DataFrame(hourly_data)
    
    def create_comprehensive_map(self, output_file="ais_navigation_system.html"):
        """통합 네비게이션 지도 생성"""
        print("\n🗺️ 통합 네비게이션 시스템 생성 중...")
        
        center_lat = self.df['lat'].mean()
        center_lon = self.df['lon'].mean()
        
        # 기본 지도 생성
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=9,
            tiles='OpenStreetMap',
            control_scale=True
        )
        
        # 날짜별 레이어
        dates = sorted(self.df['date'].unique())
        date_groups = {}
        
        print(f"   날짜별 레이어: {len(dates)}개")
        
        for date in dates[:15]:
            date_str = str(date)
            date_groups[date_str] = folium.FeatureGroup(
                name=f"📅 {date_str}", 
                show=(date == dates[0])
            )
        
        # 시간대별 레이어
        time_groups = {
            0: folium.FeatureGroup(name="🌙 심야 (00-06시)", show=False),
            6: folium.FeatureGroup(name="🌅 새벽 (06-12시)", show=False),
            12: folium.FeatureGroup(name="☀️ 오후 (12-18시)", show=False),
            18: folium.FeatureGroup(name="🌆 저녁 (18-24시)", show=False)
        }
        
        # 전체 경로 레이어
        all_routes = folium.FeatureGroup(name="🚢 전체 경로", show=True)
        
        print("   경로 처리 중...")
        
        # 파일별 경로 생성
        file_groups = self.df.groupby(['folder', 'file'])
        total = len(file_groups)
        
        for idx, ((folder, file), group) in enumerate(file_groups, 1):
            if idx > 200:
                break
            
            if idx % 20 == 0:
                print(f"   진행: {idx}/{min(total, 200)}", end='\r')
            
            file_df = group.sort_values('datetime')
            if len(file_df) < 2:
                continue
            
            vessel_info = self.vessel_types.get(folder, {'color': '#888888', 'name': folder})
            color = vessel_info['color']
            vessel_name = vessel_info['name']
            
            coordinates = [[row['lat'], row['lon']] for _, row in file_df.iterrows()]
            
            # 팝업
            popup_html = f"""
            <div style="font-family: Arial; width: 280px; padding: 10px;">
                <h3 style="margin: 0 0 10px 0; color: {color}; border-bottom: 2px solid {color};">
                    🚢 {vessel_name}
                </h3>
                <table style="width: 100%; font-size: 12px;">
                    <tr><td><b>포인트:</b></td><td>{len(coordinates)}개</td></tr>
                    <tr><td><b>시작:</b></td><td>{file_df.iloc[0]['datetime']}</td></tr>
                    <tr><td><b>종료:</b></td><td>{file_df.iloc[-1]['datetime']}</td></tr>
                    <tr><td><b>평균속도:</b></td><td>{file_df['sog'].mean():.2f} knots</td></tr>
                </table>
            </div>
            """
            
            # 경로 추가
            folium.PolyLine(
                coordinates, color=color, weight=2.5, opacity=0.7,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(all_routes)
            
            # 날짜별 추가
            date_str = str(file_df.iloc[0]['date'])
            if date_str in date_groups:
                folium.PolyLine(coordinates, color=color, weight=2, opacity=0.6).add_to(date_groups[date_str])
            
            # 시간대별 마커
            for _, row in file_df.iterrows():
                hour = row['time_hour']
                for start_h in [0, 6, 12, 18]:
                    if start_h <= hour < start_h + 6:
                        folium.CircleMarker(
                            [row['lat'], row['lon']], radius=3,
                            popup=f"{row['datetime']}<br>{row['sog']:.1f}kt",
                            tooltip=f"{row['datetime'].strftime('%H:%M')}",
                            color=color, fill=True, fillOpacity=0.6
                        ).add_to(time_groups[start_h])
                        break
        
        print(f"\n   ✓ {min(idx, 200)}개 경로 완료")
        
        # 레이어 추가
        all_routes.add_to(m)
        for g in date_groups.values():
            g.add_to(m)
        for g in time_groups.values():
            g.add_to(m)
        
        # 히트맵
        print("   히트맵 생성...")
        heat_data = [[r['lat'], r['lon']] for _, r in self.df.iterrows()]
        heat_layer = folium.FeatureGroup(name="🔥 밀집도 히트맵", show=False)
        plugins.HeatMap(
            heat_data, radius=20, blur=30, max_zoom=13,
            gradient={0.0: 'blue', 0.5: 'lime', 0.75: 'yellow', 1.0: 'red'}
        ).add_to(heat_layer)
        heat_layer.add_to(m)
        
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        
        # 안전도 분석
        safety_df = self.analyze_time_safety()
        safe_hours = safety_df.nlargest(5, 'safety_score')
        danger_hours = safety_df.nsmallest(5, 'safety_score')
        
        safe_html = "".join([f"<li>{r['hour']:02d}:00 - {r['safety_score']:.0f}/100 ({r['safety_level']})</li>" 
                            for _, r in safe_hours.iterrows()])
        danger_html = "".join([f"<li>{r['hour']:02d}:00 - {r['safety_score']:.0f}/100 ({r['safety_level']})</li>" 
                              for _, r in danger_hours.iterrows()])
        
        # 정보 패널
        info_panel = f"""
        <div style="position: fixed; bottom: 20px; right: 20px; width: 350px; 
                    background: white; border: 3px solid #2c3e50; border-radius: 10px; 
                    padding: 20px; z-index: 9999; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    font-family: Arial; max-height: 80vh; overflow-y: auto;">
            
            <h2 style="margin: 0 0 15px 0; color: #2c3e50; text-align: center; 
                       border-bottom: 3px solid #3498db; padding-bottom: 10px;">
                🧭 AIS 네비게이션 시스템
            </h2>
            
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px 0;">📊 데이터 요약</h3>
                <table style="width: 100%; color: white; font-size: 12px;">
                    <tr><td>총 데이터:</td><td style="text-align: right;"><b>{len(self.df):,}개</b></td></tr>
                    <tr><td>조업 유형:</td><td style="text-align: right;"><b>{self.df['folder'].nunique()}개</b></td></tr>
                    <tr><td>분석 기간:</td><td style="text-align: right;"><b>{len(dates)}일</b></td></tr>
                </table>
            </div>
            
            <div style="margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px 0; color: #27ae60;">✅ 안전 시간대 TOP 5</h3>
                <ol style='margin: 5px 0; padding-left: 20px; font-size: 12px;'>{safe_html}</ol>
            </div>
            
            <div style="margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px 0; color: #e74c3c;">⚠️ 주의 시간대 TOP 5</h3>
                <ol style='margin: 5px 0; padding-left: 20px; font-size: 12px;'>{danger_html}</ol>
            </div>
            
            <div style="background: #ecf0f1; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
                <h4 style="margin: 0 0 8px 0; color: #2c3e50;">🗺️ 조업 유형</h4>
        """
        
        for folder, info in self.vessel_types.items():
            count = len(self.df[self.df['folder'] == folder])
            info_panel += f'<p style="margin: 3px 0;"><span style="color: {info["color"]}; font-size: 16px;">●</span> {info["name"]} ({count:,}개)</p>'
        
        info_panel += f"""
            </div>
            
            <div style="background: #d4edda; padding: 12px; border-radius: 8px; border-left: 4px solid #28a745;">
                <h4 style="margin: 0 0 8px 0; color: #155724;">💡 사용법</h4>
                <ul style="margin: 0; padding-left: 20px; font-size: 11px; color: #155724;">
                    <li>레이어에서 날짜/시간 선택</li>
                    <li>경로 클릭 → 상세정보</li>
                    <li>마커에 마우스 → 시간/속도</li>
                    <li>히트맵으로 밀집지역 확인</li>
                </ul>
            </div>
            
            <div style="margin-top: 15px; text-align: center; font-size: 10px; color: #7f8c8d;">
                <p style="margin: 5px 0;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(info_panel))
        m.save(output_file)
        
        print(f"\n✅ 저장: {output_file}")
        return m, safety_df
    
    def generate_report_summary(self):
        """보고서용 요약 정보"""
        print("\n" + "="*60)
        print("📋 보고서용 요약 정보")
        print("="*60)
        
        safety_df = self.analyze_time_safety()
        
        print(f"\n1. 데이터 개요")
        print(f"   - 총 데이터: {len(self.df):,}개")
        print(f"   - 조업 유형: {self.df['folder'].nunique()}개")
        print(f"   - 기간: {self.df['date'].min()} ~ {self.df['date'].max()}")
        print(f"   - 범위: 위도 {self.df['lat'].min():.2f}~{self.df['lat'].max():.2f}°, "
              f"경도 {self.df['lon'].min():.2f}~{self.df['lon'].max():.2f}°")
        
        print(f"\n2. 조업 유형별 활동량")
        for folder in self.df['folder'].unique():
            count = len(self.df[self.df['folder'] == folder])
            pct = (count / len(self.df)) * 100
            name = self.vessel_types.get(folder, {}).get('name', folder)
            print(f"   - {name}: {count:,}개 ({pct:.1f}%)")
        
        print(f"\n3. 시간대별 안전도")
        print(f"   최고 안전:")
        for _, r in safety_df.nlargest(3, 'safety_score').iterrows():
            print(f"   - {r['hour']:02d}:00: {r['safety_score']:.1f}/100 ({r['safety_level']})")
        
        print(f"\n   주의:")
        for _, r in safety_df.nsmallest(3, 'safety_score').iterrows():
            print(f"   - {r['hour']:02d}:00: {r['safety_score']:.1f}/100 ({r['safety_level']})")
        
        print(f"\n4. 권장 운항시간")
        safe = safety_df[safety_df['safety_score'] >= 60]
        hours = [f"{r['hour']:02d}:00" for _, r in safe.iterrows()]
        print(f"   안전 시간대 ({len(safe)}시간): {', '.join(hours)}")
        
        print("\n" + "="*60)


def main():
    """메인 실행"""
    print("\n" + "="*70)
    print("🌊 AIS 기반 해양 안전 네비게이션 시스템")
    print("   Marine Safety Navigation System based on AIS Data")
    print("="*70)
    
    base_path = r"E:\sohyeon_project\133.어선 조업패턴 항적 데이터\3.개방데이터\1.데이터\Training\01.원천데이터"
    output_dir = Path("C:/Temp")
    
    nav = AISNavigationSystem(base_path)
    
    print("\n📥 데이터 로드 설정")
    print("-" * 70)
    limit = int(input("각 조업 유형당 파일 수 (권장: 10-15): "))
    
    df = nav.load_data(limit_files=limit)
    
    if df is None:
        print("\n❌ 실패")
        return
    
    while True:
        print("\n" + "="*70)
        print("📊 메뉴")
        print("="*70)
        print("[1] 🗺️  통합 네비게이션 지도 (날짜/시간 필터링)")
        print("[2] 📋 보고서용 요약 정보")
        print("[3] 🎯 모두 생성 (지도 + 요약)")
        print("[0] 🚪 종료")
        print("="*70)
        
        choice = input("\n선택: ").strip()
        
        if choice == '0':
            print("\n👋 종료")
            break
        
        elif choice == '1':
            file = str(output_dir / "ais_navigation_system.html")
            nav.create_comprehensive_map(file)
            print(f"\n✅ 완료: {file}")
            print("   브라우저에서 열어 날짜/시간별 필터링 가능!")
        
        elif choice == '2':
            nav.generate_report_summary()
            print("\n위 정보를 보고서에 활용하세요!")
        
        elif choice == '3':
            print("\n🚀 모든 결과물 생성...\n")
            
            file = str(output_dir / "ais_navigation_system.html")
            nav.create_comprehensive_map(file)
            nav.generate_report_summary()
            
            print("\n" + "="*70)
            print("✅ 모두 완료!")
            print("="*70)
            print(f"\n📁 생성 파일:")
            print(f"   • {file}")
            print(f"     → 날짜/시간별 필터링 가능한 통합 지도")
            print(f"   • 콘솔 출력")
            print(f"     → 보고서용 요약 정보")
            print("\n💡 HTML 파일을 브라우저로 열어 확인하세요!")
            print("   레이어 메뉴에서 날짜와 시간대를 체크/해제하며")
            print("   경로를 클릭하고 마커에 마우스를 올려보세요!\n")
            print("="*70)
    
    print("\n프로그램 종료! 🌊")


if __name__ == "__main__":
    main()
