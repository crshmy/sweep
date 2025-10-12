# -*- coding: utf-8 -*-
"""
해양쓰레기 핫스팟 도출 시스템 (개선 버전)
- 라그랑지안 입자 추적 기법 기반
- 일본 조사 데이터 상세 반영
- 에러 핸들링 및 입자 생존율 개선
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 한글 폰트 설정
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False


class HotspotDetector:
    """해양쓰레기 핫스팟 탐지 클래스"""
    
    def __init__(self):
        """초기화"""
        # 대한해협 영역 (위도, 경도)
        self.area_bounds = {
            'lat_min': 30.0,
            'lat_max': 37.0,
            'lon_min': 125.5,
            'lon_max': 132.0
        }
        
        # 일본 조사 데이터 (보고서 기반 - 상세 버전)
        self.japan_survey = self._load_japan_survey_data()
        
    def _load_japan_survey_data(self):
        """일본 조사 데이터 로드 (보고서 Table IV-1 기반)"""
        survey_data = []
        
        # 동중국해 조사 데이터 (2021년 7-11월)
        east_china_sea = [
            {'ship': '해응환', 'date': '2021-07-17', 'lat': 31.497, 'lon': 127.699, 'depth': 135, 'plastic': 0.071, 'eps': 0.007, 'fishing': 0.005},
            {'ship': '신응환', 'date': '2021-07-18', 'lat': 31.182, 'lon': 127.385, 'depth': 116, 'plastic': 0.794, 'eps': 0.315, 'fishing': 0.028},
            {'ship': '신응환', 'date': '2021-07-18', 'lat': 31.279, 'lon': 127.307, 'depth': 112, 'plastic': 0.442, 'eps': 0.122, 'fishing': 0.025},
            {'ship': '신응환', 'date': '2021-08-25', 'lat': 31.283, 'lon': 127.680, 'depth': 137, 'plastic': 0.085, 'eps': 0.349, 'fishing': 0.015},
            {'ship': '장기환', 'date': '2021-05-26', 'lat': 31.850, 'lon': 127.818, 'depth': 149, 'plastic': 0.181, 'eps': 0.023, 'fishing': 0.015},
            {'ship': '카고시마환', 'date': '2021-09-23', 'lat': 31.087, 'lon': 127.938, 'depth': 151, 'plastic': 1.032, 'eps': 0.000, 'fishing': 0.035},
            {'ship': '카고시마환', 'date': '2021-10-18', 'lat': 31.447, 'lon': 127.899, 'depth': 142, 'plastic': 0.452, 'eps': 0.037, 'fishing': 0.200},
        ]
        
        # 히다카 앞바다 (깊은 해역)
        hidaka = [
            {'ship': '오쇼로마루', 'date': '2021-11-24', 'lat': 42.209, 'lon': 141.681, 'depth': 690, 'plastic': 5259, 'eps': 1026, 'fishing': 155},
            {'ship': '오쇼로마루', 'date': '2021-11-24', 'lat': 42.210, 'lon': 141.667, 'depth': 675, 'plastic': 0.86, 'eps': 0.00, 'fishing': 0.07},
        ]
        
        return east_china_sea + hidaka
    
    def simulate_current_flow(self, n_particles=1000, days=30):
        """
        해류를 따른 입자 이동 시뮬레이션 (개선 버전)
        - 입자 생존율 향상을 위해 초기 분포 범위 조정
        - 해류 속도 최적화
        """
        # 초기 입자 분포 (동중국해 중심부에 집중 배치)
        lat_center = 32.0
        lon_center = 127.0
        lat_spread = 1.5  # 기존 2.0에서 축소
        lon_spread = 1.5  # 기존 2.0에서 축소
        
        lat_init = np.random.uniform(lat_center - lat_spread/2, lat_center + lat_spread/2, n_particles)
        lon_init = np.random.uniform(lon_center - lon_spread/2, lon_center + lon_spread/2, n_particles)
        
        particles = {
            'lat': lat_init.copy(),
            'lon': lon_init.copy(),
            'history': []
        }
        
        # 해류 벡터 (단순화된 대마난류 - 속도 감소)
        current_speed = 0.3  # m/s (0.5에서 감소)
        current_direction = 45  # 북동쪽
        
        dt = 3600 * 24  # 1일 (초)
        
        for day in range(days):
            n_current = len(particles['lat'])  # 현재 남아있는 입자 수
            
            if n_current == 0:
                break
            
            # 해류에 따른 이동
            dlat = (current_speed * dt / 111000) * np.cos(np.radians(current_direction))
            dlon = (current_speed * dt / (111000 * np.cos(np.radians(particles['lat'])))) * np.sin(np.radians(current_direction))
            
            # 난류 효과 추가 (현재 입자 수에 맞춰서)
            dlat += np.random.normal(0, 0.01, n_current)
            dlon += np.random.normal(0, 0.01, n_current)
            
            particles['lat'] += dlat
            particles['lon'] += dlon
            
            # 영역 밖으로 나간 입자 필터링
            valid_mask = (
                (particles['lat'] >= self.area_bounds['lat_min']) &
                (particles['lat'] <= self.area_bounds['lat_max']) &
                (particles['lon'] >= self.area_bounds['lon_min']) &
                (particles['lon'] <= self.area_bounds['lon_max'])
            )
            
            particles['lat'] = particles['lat'][valid_mask]
            particles['lon'] = particles['lon'][valid_mask]
            
            # 히스토리 저장
            if len(particles['lat']) > 0:
                particles['history'].append({
                    'day': day,
                    'count': len(particles['lat']),
                    'positions': np.column_stack([particles['lat'].copy(), particles['lon'].copy()])
                })
        
        return particles
    
    def detect_hotspots(self, particles, grid_size=0.1):
        """입자 밀집도 기반 핫스팟 탐지 (에러 핸들링 추가)"""
        
        # 입자가 없는 경우 처리
        if len(particles['lat']) == 0:
            print("⚠️  경고: 입자가 없어 핫스팟을 탐지할 수 없습니다.")
            empty_df = pd.DataFrame(columns=['lat', 'lon', 'density', 'density_normalized'])
            empty_density = np.array([[0]])
            empty_edges = (np.array([self.area_bounds['lat_min'], self.area_bounds['lat_max']]), 
                          np.array([self.area_bounds['lon_min'], self.area_bounds['lon_max']]))
            return empty_df, empty_density, empty_edges[0], empty_edges[1]
        
        lat_bins = np.arange(
            self.area_bounds['lat_min'], 
            self.area_bounds['lat_max'] + grid_size, 
            grid_size
        )
        lon_bins = np.arange(
            self.area_bounds['lon_min'], 
            self.area_bounds['lon_max'] + grid_size, 
            grid_size
        )
        
        # 2D 히스토그램
        density, lat_edges, lon_edges = np.histogram2d(
            particles['lat'],
            particles['lon'],
            bins=[lat_bins, lon_bins]
        )
        
        # 밀도가 있는 셀이 없는 경우 처리
        if not np.any(density > 0):
            print("⚠️  경고: 모든 셀의 밀도가 0입니다.")
            empty_df = pd.DataFrame(columns=['lat', 'lon', 'density', 'density_normalized'])
            return empty_df, density, lat_edges, lon_edges
        
        # 핫스팟 탐지
        threshold = np.percentile(density[density > 0], 90)
        hotspot_indices = np.where(density > threshold)
        
        hotspots = []
        for i, j in zip(hotspot_indices[0], hotspot_indices[1]):
            lat_center = (lat_edges[i] + lat_edges[i+1]) / 2
            lon_center = (lon_edges[j] + lon_edges[j+1]) / 2
            
            hotspots.append({
                'lat': lat_center,
                'lon': lon_center,
                'density': density[i, j],
                'density_normalized': density[i, j] / density.max()
            })
        
        hotspots_df = pd.DataFrame(hotspots)
        hotspots_df = hotspots_df.sort_values('density', ascending=False).reset_index(drop=True)
        
        return hotspots_df, density, lat_edges, lon_edges
    
    def create_japan_dataframe(self):
        """일본 조사 데이터를 데이터프레임으로 변환"""
        return pd.DataFrame(self.japan_survey)
    
    def visualize_hotspots(self, particles, hotspots_df, density, lat_edges, lon_edges):
        """핫스팟 시각화 (일본 데이터 상세 표시)"""
        
        fig = plt.figure(figsize=(18, 10))
        
        # 1. 전체 입자 분포 + 핫스팟
        ax1 = plt.subplot(2, 2, 1)
        
        if len(particles['lat']) > 0:
            ax1.scatter(particles['lon'], particles['lat'], 
                       alpha=0.2, s=1, c='lightblue', label='입자 궤적')
        
        # 핫스팟 표시
        if len(hotspots_df) > 0:
            scatter1 = ax1.scatter(hotspots_df['lon'][:10], hotspots_df['lat'][:10], 
                       s=hotspots_df['density'][:10]*2, 
                       c=hotspots_df['density_normalized'][:10],
                       cmap='YlOrRd', marker='o', 
                       edgecolors='black', linewidths=1.5,
                       label='탐지 핫스팟', zorder=5, alpha=0.7)
            plt.colorbar(scatter1, ax=ax1, label='밀도 (정규화)')
        else:
            ax1.text(0.5, 0.5, '핫스팟 없음', 
                    transform=ax1.transAxes, ha='center', va='center', fontsize=20)
        
        ax1.set_xlabel('경도')
        ax1.set_ylabel('위도')
        ax1.set_title('입자 추적 + 핫스팟 탐지')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 히트맵
        ax2 = plt.subplot(2, 2, 2)
        if density.max() > 0:
            im = ax2.contourf(lon_edges[:-1], lat_edges[:-1], density, 
                             levels=20, cmap='YlOrRd')
            plt.colorbar(im, ax=ax2, label='입자 밀도')
        else:
            ax2.text(0.5, 0.5, '밀도 데이터 없음', 
                    transform=ax2.transAxes, ha='center', va='center', fontsize=20)
        
        ax2.set_xlabel('경도')
        ax2.set_ylabel('위도')
        ax2.set_title('쓰레기 밀도 히트맵')
        ax2.grid(True, alpha=0.3)
        
        # 3. 일본 조사 데이터 - 플라스틱 밀도
        ax3 = plt.subplot(2, 2, 3)
        japan_df = self.create_japan_dataframe()
        
        # 동중국해 데이터만 필터링 (히다카는 스케일이 너무 달라서)
        ecs_data = japan_df[japan_df['lat'] < 35]
        
        scatter3 = ax3.scatter(ecs_data['lon'], ecs_data['lat'], 
                   s=ecs_data['plastic']*500, 
                   c=ecs_data['plastic'],
                   cmap='Reds', marker='s', 
                   edgecolors='black', linewidths=1.5,
                   label='일본 조사 (플라스틱)', alpha=0.7)
        
        plt.colorbar(scatter3, ax=ax3, label='플라스틱 밀도 (개/km²)')
        ax3.set_xlabel('경도')
        ax3.set_ylabel('위도')
        ax3.set_title('일본 조사 - 플라스틱 분포 (동중국해)')
        ax3.grid(True, alpha=0.3)
        
        # 4. 일본 조사 데이터 - 발포스티롤 밀도
        ax4 = plt.subplot(2, 2, 4)
        scatter4 = ax4.scatter(ecs_data['lon'], ecs_data['lat'], 
                   s=ecs_data['eps']*500, 
                   c=ecs_data['eps'],
                   cmap='Blues', marker='^', 
                   edgecolors='black', linewidths=1.5,
                   label='일본 조사 (발포스티롤)', alpha=0.7)
        
        plt.colorbar(scatter4, ax=ax4, label='발포스티롤 밀도 (개/km²)')
        ax4.set_xlabel('경도')
        ax4.set_ylabel('위도')
        ax4.set_title('일본 조사 - 발포스티롤 분포 (동중국해)')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('C:/ClaudeFolder/marine_cleanup_nav/hotspot/hotspot_analysis_detailed.png', 
                   dpi=300, bbox_inches='tight')
        print("✅ 상세 시각화 저장: hotspot_analysis_detailed.png")
        plt.show()


def main():
    """메인 실행 함수"""
    print("="*70)
    print("해양쓰레기 핫스팟 도출 시스템 (개선 버전)")
    print("="*70)
    
    # 1. 초기화
    detector = HotspotDetector()
    print("\n[1단계] 라그랑지안 입자 추적 시뮬레이션 시작...")
    
    # 2. 입자 시뮬레이션 (파라미터 최적화)
    particles = detector.simulate_current_flow(n_particles=2000, days=30)
    remaining = len(particles['lat'])
    survival_rate = remaining / 2000 * 100
    print(f"   ✓ 최종 {remaining}개 입자 (초기 2000개, 생존율 {survival_rate:.1f}%)")
    
    if remaining < 100:
        print(f"   ⚠️  경고: 생존 입자가 {remaining}개로 너무 적습니다.")
        print(f"   → 시뮬레이션 기간 단축 또는 초기 위치 조정을 권장합니다.")
    
    # 3. 핫스팟 탐지
    print("\n[2단계] 핫스팟 탐지 중...")
    hotspots_df, density, lat_edges, lon_edges = detector.detect_hotspots(particles)
    
    if len(hotspots_df) > 0:
        print(f"   ✓ {len(hotspots_df)}개 핫스팟 탐지")
    else:
        print(f"   ⚠️  핫스팟을 탐지하지 못했습니다.")
    
    # 4. 상위 핫스팟 출력
    if len(hotspots_df) > 0:
        print("\n[3단계] 탐지된 핫스팟 (Top 5):")
        print("-" * 70)
        for idx, row in hotspots_df.head(5).iterrows():
            print(f"{idx+1}. 위도: {row['lat']:.3f}°, 경도: {row['lon']:.3f}°")
            print(f"   입자 밀도: {row['density']:.0f} (상대밀도: {row['density_normalized']:.2%})")
    
    # 5. 일본 조사 데이터 출력
    print("\n[4단계] 일본 조사 데이터 요약:")
    print("-" * 70)
    japan_df = detector.create_japan_dataframe()
    print(f"총 조사 지점: {len(japan_df)}개")
    print(f"\n동중국해 평균 밀도:")
    ecs_data = japan_df[japan_df['lat'] < 35]
    print(f"  - 플라스틱: {ecs_data['plastic'].mean():.3f} 개/km²")
    print(f"  - 발포스티롤: {ecs_data['eps'].mean():.3f} 개/km²")
    print(f"  - 어구류: {ecs_data['fishing'].mean():.3f} 개/km²")
    
    # 6. 시각화
    print("\n[5단계] 결과 시각화 중...")
    detector.visualize_hotspots(particles, hotspots_df, density, lat_edges, lon_edges)
    
    # 7. 결과 저장
    print("\n[6단계] 결과 저장 중...")
    
    if len(hotspots_df) > 0:
        hotspots_df.to_csv('C:/ClaudeFolder/marine_cleanup_nav/hotspot/hotspots_detected.csv', 
                           index=False, encoding='utf-8-sig')
        print("   ✓ 탐지 핫스팟: hotspots_detected.csv")
    else:
        print("   ⚠️  저장할 핫스팟 데이터가 없습니다.")
    
    japan_df.to_csv('C:/ClaudeFolder/marine_cleanup_nav/hotspot/japan_survey_data.csv', 
                   index=False, encoding='utf-8-sig')
    print("   ✓ 일본 조사 데이터: japan_survey_data.csv")
    
    print("\n" + "="*70)
    print("✅ 핫스팟 도출 완료!")
    print("="*70)


if __name__ == "__main__":
    main()
