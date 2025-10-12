# -*- coding: utf-8 -*-
"""
해양쓰레기 핫스팟 도출 시스템
- 라그랑지안 입자 추적 기법 기반
- 일본 조사 데이터 검증
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
            'lat_min': 32.5,
            'lat_max': 36.0,
            'lon_min': 125.5,
            'lon_max': 131.0
        }
        
        # 일본 조사 데이터 (검증용)
        self.japan_survey = [
            {'name': '신요마루_No5', 'lat': 31 + 10.9/60, 'lon': 127 + 23.1/60, 'depth': 116},
            {'name': '신요마루_No6', 'lat': 31 + 17.0/60, 'lon': 127 + 40.8/60, 'depth': 137},
        ]
        
    def simulate_current_flow(self, n_particles=1000, days=30):
        """
        해류를 따른 입자 이동 시뮬레이션
        
        Parameters:
        -----------
        n_particles : int
            입자 개수
        days : int
            시뮬레이션 일수
            
        Returns:
        --------
        particles : dict
            입자 위치 정보
        """
        # 초기 입자 분포 (동중국해에서 시작)
        particles = {
            'lat': np.random.uniform(31.0, 33.0, n_particles),
            'lon': np.random.uniform(126.0, 128.0, n_particles),
            'history': []
        }
        
        # 해류 벡터 (단순화된 대마난류)
        # 실제로는 HYCOM 같은 해양 모델 데이터 사용
        current_speed = 0.5  # m/s (약 1 knot)
        current_direction = 45  # 북동쪽
        
        # 시뮬레이션
        dt = 3600 * 24  # 1일 (초 단위)
        
        for day in range(days):
            # 해류에 따른 이동
            # 위도 이동: 약 0.01도 ~ 1.1km
            dlat = (current_speed * dt / 111000) * np.cos(np.radians(current_direction))
            dlon = (current_speed * dt / (111000 * np.cos(np.radians(particles['lat'])))) * np.sin(np.radians(current_direction))
            
            # 난류 효과 추가 (무작위 확산)
            dlat += np.random.normal(0, 0.01, n_particles)
            dlon += np.random.normal(0, 0.01, n_particles)
            
            particles['lat'] += dlat
            particles['lon'] += dlon
            
            # 영역 밖으로 나간 입자 제거
            valid_mask = (
                (particles['lat'] >= self.area_bounds['lat_min']) &
                (particles['lat'] <= self.area_bounds['lat_max']) &
                (particles['lon'] >= self.area_bounds['lon_min']) &
                (particles['lon'] <= self.area_bounds['lon_max'])
            )
            
            particles['lat'] = particles['lat'][valid_mask]
            particles['lon'] = particles['lon'][valid_mask]
            
            # 히스토리 저장
            particles['history'].append({
                'day': day,
                'positions': np.column_stack([particles['lat'].copy(), particles['lon'].copy()])
            })
        
        return particles
    
    def detect_hotspots(self, particles, grid_size=0.1):
        """
        입자 밀집도 기반 핫스팟 탐지
        
        Parameters:
        -----------
        particles : dict
            입자 위치 정보
        grid_size : float
            격자 크기 (도 단위)
            
        Returns:
        --------
        hotspots : pd.DataFrame
            핫스팟 정보
        """
        # 격자 생성
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
        
        # 2D 히스토그램 (입자 밀도)
        density, lat_edges, lon_edges = np.histogram2d(
            particles['lat'],
            particles['lon'],
            bins=[lat_bins, lon_bins]
        )
        
        # 핫스팟 탐지 (상위 10% 밀도)
        threshold = np.percentile(density[density > 0], 90)
        hotspot_indices = np.where(density > threshold)
        
        # 핫스팟 데이터프레임 생성
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
    
    def validate_with_japan_data(self, hotspots_df):
        """
        일본 조사 데이터로 검증
        
        Parameters:
        -----------
        hotspots_df : pd.DataFrame
            탐지된 핫스팟
            
        Returns:
        --------
        validation_result : dict
            검증 결과
        """
        validation = []
        
        for survey in self.japan_survey:
            # 가장 가까운 핫스팟 찾기
            distances = np.sqrt(
                (hotspots_df['lat'] - survey['lat'])**2 + 
                (hotspots_df['lon'] - survey['lon'])**2
            )
            
            min_dist_idx = distances.idxmin()
            min_dist = distances.min()
            
            validation.append({
                'survey_name': survey['name'],
                'survey_lat': survey['lat'],
                'survey_lon': survey['lon'],
                'nearest_hotspot_lat': hotspots_df.loc[min_dist_idx, 'lat'],
                'nearest_hotspot_lon': hotspots_df.loc[min_dist_idx, 'lon'],
                'distance_km': min_dist * 111,  # 도를 km로 변환
                'match': min_dist < 0.5  # 50km 이내면 일치로 판단
            })
        
        return pd.DataFrame(validation)
    
    def visualize_hotspots(self, particles, hotspots_df, density, lat_edges, lon_edges):
        """
        핫스팟 시각화
        
        Parameters:
        -----------
        particles : dict
            입자 정보
        hotspots_df : pd.DataFrame
            핫스팟 정보
        density : np.array
            밀도 격자
        lat_edges, lon_edges : np.array
            격자 경계
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # 1. 입자 분포
        ax1.scatter(particles['lon'], particles['lat'], 
                   alpha=0.3, s=1, c='blue', label='쓰레기 입자')
        
        # 일본 조사 지점
        for survey in self.japan_survey:
            ax1.plot(survey['lon'], survey['lat'], 'r*', 
                    markersize=15, label=f"{survey['name']}")
        
        ax1.set_xlabel('경도')
        ax1.set_ylabel('위도')
        ax1.set_title('입자 추적 결과')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 핫스팟 히트맵
        im = ax2.contourf(lon_edges[:-1], lat_edges[:-1], density, 
                         levels=20, cmap='YlOrRd')
        
        # 탐지된 핫스팟 표시
        ax2.scatter(hotspots_df['lon'][:5], hotspots_df['lat'][:5], 
                   s=200, c='red', marker='X', 
                   edgecolors='black', linewidths=2,
                   label='핫스팟 (Top 5)', zorder=5)
        
        # 일본 조사 지점
        for survey in self.japan_survey:
            ax2.plot(survey['lon'], survey['lat'], 'b*', 
                    markersize=15, label=f"{survey['name']}")
        
        plt.colorbar(im, ax=ax2, label='입자 밀도')
        ax2.set_xlabel('경도')
        ax2.set_ylabel('위도')
        ax2.set_title('해양쓰레기 핫스팟 히트맵')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('C:/ClaudeFolder/marine_cleanup_nav/hotspot_analysis.png', dpi=300, bbox_inches='tight')
        print("✅ 시각화 결과 저장: hotspot_analysis.png")
        plt.show()


def main():
    """메인 실행 함수"""
    print("="*60)
    print("해양쓰레기 핫스팟 도출 시스템")
    print("="*60)
    
    # 1. 핫스팟 탐지기 초기화
    detector = HotspotDetector()
    print("\n[1단계] 라그랑지안 입자 추적 시뮬레이션 시작...")
    
    # 2. 입자 시뮬레이션
    particles = detector.simulate_current_flow(n_particles=2000, days=30)
    print(f"   ✓ {len(particles['lat'])}개 입자 추적 완료")
    
    # 3. 핫스팟 탐지
    print("\n[2단계] 핫스팟 탐지 중...")
    hotspots_df, density, lat_edges, lon_edges = detector.detect_hotspots(particles)
    print(f"   ✓ {len(hotspots_df)}개 핫스팟 탐지")
    
    # 4. 상위 5개 핫스팟 출력
    print("\n[3단계] 탐지된 핫스팟 (Top 5):")
    print("-" * 60)
    for idx, row in hotspots_df.head(5).iterrows():
        print(f"{idx+1}. 위도: {row['lat']:.3f}°, 경도: {row['lon']:.3f}°")
        print(f"   밀도: {row['density']:.0f} (정규화: {row['density_normalized']:.2%})")
    
    # 5. 일본 데이터 검증
    print("\n[4단계] 일본 조사 데이터 검증:")
    print("-" * 60)
    validation = detector.validate_with_japan_data(hotspots_df)
    for _, row in validation.iterrows():
        status = "✓ 일치" if row['match'] else "✗ 불일치"
        print(f"{status} - {row['survey_name']}")
        print(f"   거리: {row['distance_km']:.1f}km")
    
    # 6. 시각화
    print("\n[5단계] 결과 시각화 중...")
    detector.visualize_hotspots(particles, hotspots_df, density, lat_edges, lon_edges)
    
    # 7. 결과 저장
    print("\n[6단계] 결과 저장 중...")
    hotspots_df.to_csv('C:/ClaudeFolder/marine_cleanup_nav/hotspots.csv', 
                       index=False, encoding='utf-8-sig')
    print("   ✓ 핫스팟 데이터: hotspots.csv")
    
    validation.to_csv('C:/ClaudeFolder/marine_cleanup_nav/validation.csv', 
                     index=False, encoding='utf-8-sig')
    print("   ✓ 검증 결과: validation.csv")
    
    print("\n" + "="*60)
    print("✅ 핫스팟 도출 완료!")
    print("="*60)


if __name__ == "__main__":
    main()
