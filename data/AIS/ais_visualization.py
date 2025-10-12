"""
AIS 경로 시각화 프로그램 (CSV 버전)
어선 조업패턴 항적 데이터 시각화
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
import numpy as np
from matplotlib.collections import LineCollection
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows
plt.rcParams['axes.unicode_minus'] = False

class AISVisualizer:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        
    def load_data(self, folder_name=None, limit_files=None):
        """
        CSV 데이터 로드
        folder_name: 특정 폴더만 로드 (예: 'TS_01.자망')
        limit_files: 로드할 파일 수 제한
        """
        all_data = []
        
        if folder_name:
            folders = [self.base_path / folder_name]
        else:
            folders = [f for f in self.base_path.iterdir() if f.is_dir()]
        
        for folder in folders:
            print(f"\n처리중: {folder.name}")
            
            # CSV 파일 검색
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
    
    def plot_routes(self, df, color_by='folder', figsize=(15, 12)):
        """
        경로 시각화
        color_by: 'folder', 'sog', 'month' 등
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        if color_by == 'folder':
            # 폴더별로 다른 색상
            folders = df['folder'].unique()
            colors = plt.cm.tab10(np.linspace(0, 1, len(folders)))
            
            for i, folder in enumerate(folders):
                folder_df = df[df['folder'] == folder]
                ax.scatter(folder_df['lon'], folder_df['lat'], 
                          c=[colors[i]], label=folder, alpha=0.6, s=1)
        
        elif color_by == 'sog':
            # 속도에 따라 색상
            scatter = ax.scatter(df['lon'], df['lat'], 
                               c=df['sog'], cmap='viridis', 
                               alpha=0.6, s=1)
            plt.colorbar(scatter, ax=ax, label='속도 (SOG, knots)')
        
        ax.set_xlabel('경도 (Longitude)', fontsize=12)
        ax.set_ylabel('위도 (Latitude)', fontsize=12)
        ax.set_title('AIS 경로 시각화', fontsize=16, pad=20, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        if color_by == 'folder':
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
        
        plt.tight_layout()
        return fig
    
    def plot_individual_tracks(self, df, max_tracks=5, figsize=(15, 10)):
        """
        개별 선박 궤적을 선으로 표시
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # 파일별로 그룹화 (각 파일이 하나의 선박 궤적)
        files = df['file'].unique()[:max_tracks]
        colors = plt.cm.tab10(np.linspace(0, 1, len(files)))
        
        for i, file in enumerate(files):
            file_df = df[df['file'] == file].sort_values('datetime')
            ax.plot(file_df['lon'], file_df['lat'], 
                   c=colors[i], label=f"{file[:30]}...", 
                   alpha=0.7, linewidth=1.5)
            
            # 시작점 표시
            ax.scatter(file_df['lon'].iloc[0], file_df['lat'].iloc[0],
                      c=[colors[i]], marker='o', s=100, edgecolors='black',
                      linewidths=2, zorder=5)
        
        ax.set_xlabel('경도 (Longitude)', fontsize=12)
        ax.set_ylabel('위도 (Latitude)', fontsize=12)
        ax.set_title(f'개별 선박 궤적 (최대 {max_tracks}개)', fontsize=16, pad=20, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        
        plt.tight_layout()
        return fig
    
    def plot_heatmap(self, df, bins=100, figsize=(15, 12)):
        """
        밀도 히트맵
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # 2D 히스토그램
        h, xedges, yedges, im = ax.hist2d(df['lon'], df['lat'], 
                                          bins=bins, cmap='hot', 
                                          cmin=1)
        
        plt.colorbar(im, ax=ax, label='빈도')
        ax.set_xlabel('경도 (Longitude)', fontsize=12)
        ax.set_ylabel('위도 (Latitude)', fontsize=12)
        ax.set_title('AIS 경로 밀도 히트맵', fontsize=16, pad=20, fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    def plot_speed_distribution(self, df, figsize=(15, 5)):
        """
        속도 분포 분석
        """
        fig, axes = plt.subplots(1, 3, figsize=figsize)
        
        # 히스토그램
        axes[0].hist(df['sog'], bins=50, edgecolor='black', alpha=0.7, color='steelblue')
        axes[0].set_xlabel('속도 (SOG, knots)', fontsize=11)
        axes[0].set_ylabel('빈도', fontsize=11)
        axes[0].set_title('속도 분포', fontsize=12, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        
        # 폴더별 평균 속도
        folder_speed = df.groupby('folder')['sog'].mean().sort_values()
        axes[1].barh(range(len(folder_speed)), folder_speed.values, color='coral')
        axes[1].set_yticks(range(len(folder_speed)))
        axes[1].set_yticklabels(folder_speed.index, fontsize=9)
        axes[1].set_xlabel('평균 속도 (knots)', fontsize=11)
        axes[1].set_title('조업 유형별 평균 속도', fontsize=12, fontweight='bold')
        axes[1].grid(True, alpha=0.3, axis='x')
        
        # 시간대별 평균 속도
        hour_speed = df.groupby('hour')['sog'].mean()
        axes[2].plot(hour_speed.index, hour_speed.values, marker='o', 
                    linewidth=2, markersize=6, color='green')
        axes[2].set_xlabel('시간 (hour)', fontsize=11)
        axes[2].set_ylabel('평균 속도 (knots)', fontsize=11)
        axes[2].set_title('시간대별 평균 속도', fontsize=12, fontweight='bold')
        axes[2].grid(True, alpha=0.3)
        axes[2].set_xticks(range(0, 24, 3))
        
        plt.tight_layout()
        return fig


def main():
    # 데이터 경로 설정
    base_path = r"E:\sohyeon_project\133.어선 조업패턴 항적 데이터\3.개방데이터\1.데이터\Training\01.원천데이터"
    
    print("="*60)
    print("AIS 경로 시각화 프로그램")
    print("="*60)
    
    # 시각화 객체 생성
    visualizer = AISVisualizer(base_path)
    
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
    print(f"\n데이터 정보:")
    print(f"  총 데이터 포인트: {len(df):,}개")
    print(f"  위도 범위: {df['lat'].min():.4f} ~ {df['lat'].max():.4f}")
    print(f"  경도 범위: {df['lon'].min():.4f} ~ {df['lon'].max():.4f}")
    print(f"  조업 유형: {df['folder'].nunique()}개")
    print(f"  파일 수: {df['file'].nunique()}개")
    
    # 시각화 생성
    print("\n시각화 생성 중...")
    
    # 저장 경로
    output_dir = Path("C:/Temp")
    
    # 1. 전체 경로 (폴더별)
    print("  1/5 폴더별 경로 생성 중...")
    fig1 = visualizer.plot_routes(df, color_by='folder')
    fig1.savefig(output_dir / "ais_routes_by_folder.png", dpi=300, bbox_inches='tight')
    print("      ✓ 저장 완료")
    plt.close(fig1)
    
    # 2. 전체 경로 (속도별)
    print("  2/5 속도별 경로 생성 중...")
    fig2 = visualizer.plot_routes(df, color_by='sog')
    fig2.savefig(output_dir / "ais_routes_by_speed.png", dpi=300, bbox_inches='tight')
    print("      ✓ 저장 완료")
    plt.close(fig2)
    
    # 3. 개별 궤적
    print("  3/5 개별 궤적 생성 중...")
    fig3 = visualizer.plot_individual_tracks(df, max_tracks=5)
    fig3.savefig(output_dir / "ais_individual_tracks.png", dpi=300, bbox_inches='tight')
    print("      ✓ 저장 완료")
    plt.close(fig3)
    
    # 4. 히트맵
    print("  4/5 히트맵 생성 중...")
    fig4 = visualizer.plot_heatmap(df, bins=100)
    fig4.savefig(output_dir / "ais_heatmap.png", dpi=300, bbox_inches='tight')
    print("      ✓ 저장 완료")
    plt.close(fig4)
    
    # 5. 속도 분석
    print("  5/5 속도 분석 생성 중...")
    fig5 = visualizer.plot_speed_distribution(df)
    fig5.savefig(output_dir / "ais_speed_analysis.png", dpi=300, bbox_inches='tight')
    print("      ✓ 저장 완료")
    plt.close(fig5)
    
    print(f"\n{'='*60}")
    print(f"✅ 모든 시각화가 완료되었습니다!")
    print(f"{'='*60}")
    print(f"\n저장 위치: {output_dir}")
    print("\n생성된 파일:")
    print("  1. ais_routes_by_folder.png  - 조업 유형별 경로")
    print("  2. ais_routes_by_speed.png   - 속도별 경로")
    print("  3. ais_individual_tracks.png - 개별 선박 궤적")
    print("  4. ais_heatmap.png          - 경로 밀도 히트맵")
    print("  5. ais_speed_analysis.png   - 속도 분석")
    
    # 그래프 표시 여부
    show_plot = input("\n그래프를 화면에 표시하시겠습니까? (y/n): ").strip().lower()
    if show_plot == 'y':
        # 다시 그래프 생성하여 표시
        visualizer.plot_routes(df, color_by='folder')
        plt.show()


if __name__ == "__main__":
    main()
