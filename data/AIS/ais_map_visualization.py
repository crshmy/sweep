"""
AIS 경로 지도 시각화 프로그램
실제 지도 위에 경로 표시
"""

import pandas as pd
import folium
from folium import plugins
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class AISMapVisualizer:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        
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
            
            print(f"  발견된 파일 수: {len(csv_files)}개")
            
            if len(csv_files) == 0:
                continue
            
            if limit_files:
                csv_files = csv_files[:limit_files]
            
            print(f"  로드할 파일 수: {len(csv_files)}개")
            
            for i, file in enumerate(csv_files):
                try:
                    df = pd.read_csv(file)
                    df['folder'] = folder.name
                    df['file'] = file.name
                    all_data.append(df)
                    
                    if (i + 1) % 10 == 0:
                        print(f"    {i + 1}개 파일 로드 완료")
                        
                except Exception as e:
                    print(f"    오류 - {file.name}: {e}")
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            print(f"\n{'='*60}")
            print(f"총 {len(combined_df):,}개 데이터 포인트 로드 완료")
            return combined_df
        else:
            print("\n데이터를 찾을 수 없습니다.")
            return None
    
    def create_interactive_map(self, df, output_file="ais_interactive_map.html"):
        """인터랙티브 지도 생성"""
        print("\n인터랙티브 지도 생성 중...")
        
        # 지도 중심 계산
        center_lat = df['lat'].mean()
        center_lon = df['lon'].mean()
        
        # 지도 생성 (OpenStreetMap 타일)
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=8,
            tiles='OpenStreetMap'
        )
        
        # 조업 유형별 색상
        folder_colors = {
            'TS_01.자망': 'red',
            'TS_02.안강망': 'blue',
            'TS_03.채낚기': 'green',
            'TS_04.연승': 'purple',
            'TS_05.통발': 'orange',
            'TS_06.트롤': 'darkred',
            'TS_07.선망': 'darkblue'
        }
        
        # 폴더별로 경로 그리기
        for folder in df['folder'].unique():
            folder_df = df[df['folder'] == folder]
            color = folder_colors.get(folder, 'gray')
            
            # 파일별로 선 그리기
            for file in folder_df['file'].unique():
                file_df = folder_df[folder_df['file'] == file].sort_values('datetime')
                
                # 좌표 리스트 생성
                coordinates = file_df[['lat', 'lon']].values.tolist()
                
                # 경로 선 추가
                folium.PolyLine(
                    coordinates,
                    color=color,
                    weight=2,
                    opacity=0.7,
                    popup=f"{folder}<br>{file}"
                ).add_to(m)
        
        # 범례 추가
        legend_html = '''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 200px; height: auto; 
                    background-color: white; z-index:9999; font-size:14px;
                    border:2px solid grey; border-radius: 5px; padding: 10px">
        <p style="margin:0; font-weight:bold;">조업 유형</p>
        '''
        for folder, color in folder_colors.items():
            folder_name = folder.split('.')[1]
            legend_html += f'<p style="margin:5px 0;"><span style="color:{color};">●</span> {folder_name}</p>'
        legend_html += '</div>'
        
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # 지도 저장
        m.save(output_file)
        print(f"  ✓ 인터랙티브 지도 저장: {output_file}")
        
        return m
    
    def create_heatmap(self, df, output_file="ais_heatmap.html"):
        """히트맵 생성"""
        print("\n히트맵 생성 중...")
        
        # 지도 중심 계산
        center_lat = df['lat'].mean()
        center_lon = df['lon'].mean()
        
        # 지도 생성
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=8,
            tiles='OpenStreetMap'
        )
        
        # 히트맵 데이터 준비
        heat_data = df[['lat', 'lon']].values.tolist()
        
        # 히트맵 추가
        plugins.HeatMap(
            heat_data,
            radius=15,
            blur=25,
            max_zoom=13
        ).add_to(m)
        
        # 지도 저장
        m.save(output_file)
        print(f"  ✓ 히트맵 저장: {output_file}")
        
        return m
    
    def create_cluster_map(self, df, output_file="ais_cluster_map.html"):
        """클러스터 지도 생성"""
        print("\n클러스터 지도 생성 중...")
        
        # 지도 중심 계산
        center_lat = df['lat'].mean()
        center_lon = df['lon'].mean()
        
        # 지도 생성
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=8,
            tiles='OpenStreetMap'
        )
        
        # 마커 클러스터 추가
        marker_cluster = plugins.MarkerCluster().add_to(m)
        
        # 데이터 샘플링 (너무 많으면 느려짐)
        sample_df = df.sample(min(1000, len(df)))
        
        # 조업 유형별 색상
        folder_colors = {
            'TS_01.자망': 'red',
            'TS_02.안강망': 'blue',
            'TS_03.채낚기': 'green',
            'TS_04.연승': 'purple',
            'TS_05.통발': 'orange',
            'TS_06.트롤': 'darkred',
            'TS_07.선망': 'lightblue'
        }
        
        # 마커 추가
        for idx, row in sample_df.iterrows():
            color = folder_colors.get(row['folder'], 'gray')
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=3,
                popup=f"""
                    <b>조업 유형:</b> {row['folder']}<br>
                    <b>속도:</b> {row['sog']:.2f} knots<br>
                    <b>시간:</b> {row['datetime']}
                """,
                color=color,
                fill=True,
                fillColor=color
            ).add_to(marker_cluster)
        
        # 지도 저장
        m.save(output_file)
        print(f"  ✓ 클러스터 지도 저장: {output_file}")
        
        return m


def main():
    # 데이터 경로 설정
    base_path = r"E:\sohyeon_project\133.어선 조업패턴 항적 데이터\3.개방데이터\1.데이터\Training\01.원천데이터"
    
    print("="*60)
    print("AIS 경로 지도 시각화 프로그램")
    print("="*60)
    
    # 시각화 객체 생성
    visualizer = AISMapVisualizer(base_path)
    
    # 옵션 선택
    print("\n[옵션 1] 특정 폴더만 로드")
    print("[옵션 2] 모든 폴더 로드 (샘플링)")
    choice = input("선택 (1/2): ").strip()
    
    if choice == '1':
        print("\n사용 가능한 폴더:")
        folders = [f.name for f in Path(base_path).iterdir() if f.is_dir()]
        for i, folder in enumerate(folders, 1):
            print(f"  {i}. {folder}")
        folder_name = input("\n폴더 이름 입력: ").strip()
        limit_files = int(input("로드할 파일 수 (예: 10): ").strip())
        df = visualizer.load_data(folder_name=folder_name, limit_files=limit_files)
    else:
        limit_files = int(input("각 폴더당 로드할 파일 수 (예: 5): ").strip())
        df = visualizer.load_data(limit_files=limit_files)
    
    if df is None or len(df) == 0:
        print("\n데이터를 로드할 수 없습니다.")
        input("Enter 키를 눌러 종료...")
        return
    
    # 데이터 정보 출력
    print(f"\n{'='*60}")
    print(f"데이터 정보:")
    print(f"  총 데이터 포인트: {len(df):,}개")
    print(f"  위도 범위: {df['lat'].min():.4f} ~ {df['lat'].max():.4f}")
    print(f"  경도 범위: {df['lon'].min():.4f} ~ {df['lon'].max():.4f}")
    print(f"  조업 유형: {df['folder'].nunique()}개")
    print(f"  파일 수: {df['file'].nunique()}개")
    
    # 저장 경로
    output_dir = Path("C:/Temp")
    
    # 지도 유형 선택
    print(f"\n{'='*60}")
    print("생성할 지도 유형을 선택하세요:")
    print("[1] 경로 선 지도 (권장)")
    print("[2] 히트맵")
    print("[3] 클러스터 지도")
    print("[4] 모두 생성")
    
    map_choice = input("선택 (1/2/3/4): ").strip()
    
    print(f"\n{'='*60}")
    
    if map_choice in ['1', '4']:
        visualizer.create_interactive_map(
            df, 
            output_file=str(output_dir / "ais_interactive_map.html")
        )
    
    if map_choice in ['2', '4']:
        visualizer.create_heatmap(
            df,
            output_file=str(output_dir / "ais_heatmap.html")
        )
    
    if map_choice in ['3', '4']:
        visualizer.create_cluster_map(
            df,
            output_file=str(output_dir / "ais_cluster_map.html")
        )
    
    print(f"\n{'='*60}")
    print(f"✅ 지도 생성 완료!")
    print(f"{'='*60}")
    print(f"\n저장 위치: {output_dir}")
    print("\n생성된 파일:")
    if map_choice in ['1', '4']:
        print("  - ais_interactive_map.html (경로 선 지도)")
    if map_choice in ['2', '4']:
        print("  - ais_heatmap.html (히트맵)")
    if map_choice in ['3', '4']:
        print("  - ais_cluster_map.html (클러스터 지도)")
    
    print("\n💡 HTML 파일을 웹 브라우저로 열어보세요!")
    print("   (파일을 더블클릭하거나 드래그해서 브라우저에 드롭)")


if __name__ == "__main__":
    main()
