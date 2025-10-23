# -*- coding: utf-8 -*-
"""
핫스팟 기반 최적 수거 경로 생성 시스템
- Step 3 결과(hotspots.json)를 로드하여 하이브리드 알고리즘에 적용
- 실제 해양 환경 데이터 기반 쓰레기 분포 시뮬레이션
- 최적 경로 시각화 및 성능 평가
- 두번째 핫스팟 지도 및 경로 클로드가 만듦
- 스탭 8에서 네비게이션에 넣는 용도
"""

import os, json, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import heapq
import math
import time
from datetime import datetime
import folium
from folium import plugins
import shutil

# ================================================
# 디렉토리 설정
# ================================================
HOTSPOT_DIR = './daily_results_hotspot_251013'
RESULT_DIR = './sweep_path_results'
os.makedirs(RESULT_DIR, exist_ok=True)
REACT_PUBLIC_DIR = r"C:\Users\User\Downloads\sweep-marine_cleanup_nav\public"

# ================================================
# 이동 및 수거 시간 설정 (실제 값으로 조정 가능)
# ================================================
GRID_CELL_SIZE_M = 100  # 격자 한 칸의 실제 크기 (미터)
VESSEL_SPEED_MS = 2.5   # 선박 평균 속도 (m/s) - 약 5노트
COLLECTION_TIME_S = 30  # 쓰레기 1개 수거 시간 (초)

def dump_dataset_json(path_grid, trash_positions, obstacles, collected_set,
                      transform_info, hotspots_latlon, metrics,
                      copy_to_public=True):
    """React UI에서 그대로 쓰도록 dataset.json 생성 (+원하면 public으로 복사)"""

    def grid_to_latlon_pair(p):
        lat, lng = grid_to_latlon(p[0], p[1], transform_info)
        return {"lat": float(lat), "lng": float(lng)}

    # 경로/포인트들을 위경도로 변환
    route_ll = [grid_to_latlon_pair(p) for p in path_grid]
    collected_ll = [grid_to_latlon_pair(p) for p in collected_set]
    uncollected_ll = [grid_to_latlon_pair(p) for p in trash_positions if p not in collected_set]
    obstacles_ll = [grid_to_latlon_pair(p) for p in obstacles]

    data = {
      "vessel": {
        "lat": float(transform_info["origin_lat"]),
        "lng": float(transform_info["origin_lon"]),
        "heading": 180,
        "speed_kn": float(VESSEL_SPEED_MS * 1.94384)  # m/s → knots
      },
      # Folium과 동일하게 상위 10개
      "hotspots": [{"lat": float(lat), "lng": float(lon)} for (lat, lon) in hotspots_latlon[:10]],
      "route": route_ll,
      "collected": collected_ll,
      "uncollected": uncollected_ll,
      "obstacles": obstacles_ll,
      "metrics": {
        "collection_rate": float(metrics["collection_rate"]),
        "collected_count": int(metrics["collected_count"]),
        "total_trash": int(metrics["total_trash"]),
        "collision_count": int(metrics["collision_count"]),
        "actual_distance_km": float(metrics["actual_distance_km"]),
        "search_distance": int(metrics["search_distance"]),
        "travel_time_min": float(metrics["travel_time_min"]),
        "collection_time_min": float(metrics["collection_time_min"]),
        "total_operation_time_h": float(metrics["total_operation_time_h"])
      }
    }

    # 결과 폴더에 저장
    out_path = os.path.join(RESULT_DIR, "dataset.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ React용 dataset.json 저장:", out_path)

    # (선택) React public으로 복사
    if copy_to_public:
        try:
            os.makedirs(REACT_PUBLIC_DIR, exist_ok=True)
            dst = os.path.join(REACT_PUBLIC_DIR, "dataset.json")
            shutil.copyfile(out_path, dst)
            print("✅ public/dataset.json 갱신:", dst)
        except Exception as e:
            print("⚠️ public 복사 실패:", e)
            
# ================================================
# 핫스팟 데이터 로드 및 좌표 변환
# ================================================
def load_hotspots(hotspot_json_path):
    """hotspots.json 로드 및 격자 좌표로 변환"""
    with open(hotspot_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    origin_lat = data['origin']['latitude']
    origin_lon = data['origin']['longitude']
    
    # km 좌표를 격자 좌표(0~49)로 변환
    hotspots_km = [(hs['x'], hs['y'], hs['latitude'], hs['longitude']) for hs in data['hotspots']]
    
    if hotspots_km:
        x_coords = [h[0] for h in hotspots_km]
        y_coords = [h[1] for h in hotspots_km]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # km → 격자 인덱스 변환 (0~49)
        hotspots_grid = []
        hotspots_latlon = []
        for x_km, y_km, lat, lon in hotspots_km:
            grid_x = int((x_km - x_min) / (x_max - x_min) * 49) if x_max != x_min else 25
            grid_y = int((y_km - y_min) / (y_max - y_min) * 49) if y_max != y_min else 25
            hotspots_grid.append((grid_x, grid_y))
            hotspots_latlon.append((lat, lon))
        
        print(f"✅ 핫스팟 로드 완료: {len(hotspots_grid)}개")
        print(f"   좌표 범위: X({x_min:.2f}~{x_max:.2f}km), Y({y_min:.2f}~{y_max:.2f}km)")
        print(f"   상위 5개 격자 좌표: {hotspots_grid[:5]}")
        
        # 변환 정보 저장
        transform_info = {
            'x_min': x_min, 'x_max': x_max,
            'y_min': y_min, 'y_max': y_max,
            'origin_lat': origin_lat, 'origin_lon': origin_lon
        }
        
        return hotspots_grid, hotspots_latlon, data, transform_info
    
    return [], [], data, None

# ================================================
# 핫스팟 기반 쓰레기 생성 (환경 데이터 반영)
# ================================================
def generate_hotspot_based_trash(grid_size, env_row, hotspots, hotspot_radius=6):
    """
    핫스팟 중심으로 쓰레기 집중 생성 + 환경 기반 확산
    """
    wind_speed = env_row.get('풍속(m/s)', 0) or 0
    wind_direction = env_row.get('풍향(deg)', 0) or 0
    significant_wave = env_row.get('유의파고(m)', 0) or 0
    
    # 총 쓰레기 개수 (환경 영향)
    base_trash = 80
    trash_count = min(base_trash + int(wind_speed*8) + int(significant_wave*15), 400)
    
    trash_positions = []
    
    # 70%를 핫스팟 중심으로 생성
    hotspot_trash = int(trash_count * 0.7)
    remaining_trash = trash_count - hotspot_trash
    
    for _ in range(hotspot_trash):
        if not hotspots:
            break
        # 랜덤 핫스팟 선택
        hx, hy = hotspots[np.random.randint(0, len(hotspots))]
        
        # 핫스팟 주변에 정규분포로 배치
        offset_x = int(np.random.normal(0, hotspot_radius/2))
        offset_y = int(np.random.normal(0, hotspot_radius/2))
        
        # 풍향 영향 추가
        wind_offset_x = int(np.cos(np.radians(wind_direction)) * wind_speed * 0.3)
        wind_offset_y = int(np.sin(np.radians(wind_direction)) * wind_speed * 0.3)
        
        tx = np.clip(hx + offset_x + wind_offset_x, 0, grid_size-1)
        ty = np.clip(hy + offset_y + wind_offset_y, 0, grid_size-1)
        
        trash_positions.append((int(tx), int(ty)))
    
    # 나머지 30%는 랜덤 배치
    for _ in range(remaining_trash):
        tx = np.random.randint(0, grid_size)
        ty = np.random.randint(0, grid_size)
        trash_positions.append((tx, ty))
    
    return trash_positions

def generate_obstacles(grid_size, env_row):
    """장애물 생성 (파고 기반)"""
    max_wave = env_row.get('최대파고(m)', 0) or 0
    gust_speed = env_row.get('GUST풍속(m/s)', 0) or 0
    
    base_obstacles = 15
    obstacle_count = min(base_obstacles + int(max_wave*6) + int(gust_speed*2), 60)
    
    obstacles = []
    for _ in range(obstacle_count):
        ox = np.random.randint(0, grid_size)
        oy = np.random.randint(0, grid_size)
        obstacles.append((ox, oy))
    
    return obstacles

# ================================================
# 하이브리드 알고리즘 (핫스팟 최적화 버전)
# ================================================
def distance(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def adjusted_distance(a, b, wind_direction):
    dx, dy = b[0]-a[0], b[1]-a[1]
    base = math.sqrt(dx*dx + dy*dy)
    if base == 0: return 0.0
    ang = (math.degrees(math.atan2(dy, dx)) % 360)
    diff = abs(wind_direction - ang)
    diff = min(diff, 360 - diff)
    penalty = 1 + (diff/180.0)*0.5
    return base * penalty

def build_hotspot_groups(trash_positions, hotspots, radius=6):
    groups = {h: [] for h in hotspots}
    for t in trash_positions:
        h = min(hotspots, key=lambda x: distance(t, x))
        if distance(t, h) <= radius:
            groups[h].append(t)
    return groups

def hybrid_hotspot_algorithm(
    start, trash_positions, obstacle_positions, 
    env=None, hotspots=None, hotspot_radius=6,
    alpha=1.2, beta=0.15, lookahead=2, max_iterations=5000
):
    """개선된 핫스팟 기반 하이브리드 경로 알고리즘"""
    grid_size = 50
    current = start
    path = [start]
    trash_set = set(trash_positions)
    obstacle_set = set(obstacle_positions)
    collected = set()
    
    if not trash_positions:
        return path[1:], collected
    
    wind_dir = 0
    if env is not None:
        wd = env.get('풍향(deg)', 0)
        if pd.notna(wd): wind_dir = wd
    
    directions8 = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    
    # 간단하고 빠른 A* (타임아웃 포함)
    def find_path_astar(start_pos, goal_pos, max_steps=1000):
        if start_pos == goal_pos:
            return [start_pos]
        
        open_set = [(0, start_pos)]
        came_from = {}
        g_score = {start_pos: 0}
        steps = 0
        
        while open_set and steps < max_steps:
            steps += 1
            _, current_pos = heapq.heappop(open_set)
            
            if current_pos == goal_pos:
                # 경로 재구성
                path_result = []
                while current_pos in came_from:
                    path_result.append(current_pos)
                    current_pos = came_from[current_pos]
                path_result.append(start_pos)
                return list(reversed(path_result))
            
            for dx, dy in directions8:
                nx, ny = current_pos[0] + dx, current_pos[1] + dy
                if not (0 <= nx < grid_size and 0 <= ny < grid_size):
                    continue
                neighbor = (nx, ny)
                if neighbor in obstacle_set:
                    continue
                
                tentative_g = g_score[current_pos] + 1
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + distance(neighbor, goal_pos)
                    heapq.heappush(open_set, (f_score, neighbor))
                    came_from[neighbor] = current_pos
        
        return None  # 경로 없음
    
    # 그리디 최근접 이웃 (폴백)
    def greedy_nearest(current_pos, remaining_trash):
        if not remaining_trash:
            return None
        return min(remaining_trash, key=lambda t: distance(current_pos, t))
    
    # 경로 따라 이동하며 수거
    def follow_path_and_collect(route):
        nonlocal current, collected
        if not route or len(route) <= 1:
            return
        
        for step in route[1:]:
            # 장애물 회피
            if step in obstacle_set:
                # 인접한 빈 칸 찾기
                alternatives = []
                for dx, dy in directions8:
                    alt = (current[0] + dx, current[1] + dy)
                    if (0 <= alt[0] < grid_size and 0 <= alt[1] < grid_size 
                        and alt not in obstacle_set):
                        alternatives.append(alt)
                if alternatives:
                    step = min(alternatives, key=lambda p: distance(p, route[-1]))
                else:
                    break  # 막혔으면 중단
            
            path.append(step)
            current = step
            
            # 쓰레기 수거
            if current in trash_set and current not in collected:
                collected.add(current)
    
    # 핫스팟 기반 전략
    if hotspots and len(hotspots) > 0:
        # 핫스팟별 쓰레기 그룹화
        groups = build_hotspot_groups(list(trash_set), hotspots, radius=hotspot_radius)
        
        # 핫스팟을 거리 + 쓰레기 개수로 정렬
        hotspot_priority = []
        for h, trash_list in groups.items():
            if trash_list:
                dist_to_hotspot = distance(current, h)
                score = len(trash_list) / (1 + dist_to_hotspot * 0.1)  # 개수 우선, 거리는 약간만 패널티
                hotspot_priority.append((score, h, trash_list))
        
        hotspot_priority.sort(reverse=True, key=lambda x: x[0])
        
        # 각 핫스팟 방문
        visited_hotspots = set()
        for _, hotspot, trash_list in hotspot_priority:
            if len(collected) >= len(trash_set) * 0.95:  # 95% 이상 수거하면 종료
                break
            
            if hotspot in visited_hotspots:
                continue
            visited_hotspots.add(hotspot)
            
            # 핫스팟 중심으로 이동
            route_to_hotspot = find_path_astar(current, hotspot, max_steps=500)
            if route_to_hotspot:
                follow_path_and_collect(route_to_hotspot)
            
            # 핫스팟 내 쓰레기 수거 (최근접 이웃)
            remaining_in_hotspot = [t for t in trash_list if t not in collected]
            attempts = 0
            max_attempts = len(remaining_in_hotspot) + 10
            
            while remaining_in_hotspot and attempts < max_attempts:
                attempts += 1
                
                # 가장 가까운 쓰레기 찾기
                nearest = min(remaining_in_hotspot, key=lambda t: distance(current, t))
                
                # 경로 찾기
                route = find_path_astar(current, nearest, max_steps=300)
                
                if route:
                    follow_path_and_collect(route)
                    if nearest in collected:
                        remaining_in_hotspot.remove(nearest)
                else:
                    # 경로 못 찾으면 해당 쓰레기 스킵
                    remaining_in_hotspot.remove(nearest)
                
                # 진전 없으면 다음 핫스팟으로
                if attempts > 5 and len([t for t in trash_list if t in collected]) == 0:
                    break
    
    # 잔여 쓰레기 수거 (핫스팟 외부 + 미수거)
    remaining_trash = [t for t in trash_set if t not in collected]
    attempts = 0
    max_attempts = len(remaining_trash) * 2 + 50
    
    while remaining_trash and attempts < max_attempts:
        attempts += 1
        
        if len(remaining_trash) == 0:
            break
        
        # 가장 가까운 쓰레기
        nearest = min(remaining_trash, key=lambda t: distance(current, t))
        
        # 경로 찾기
        route = find_path_astar(current, nearest, max_steps=500)
        
        if route:
            old_collected_count = len(collected)
            follow_path_and_collect(route)
            
            if nearest in collected:
                remaining_trash.remove(nearest)
            elif len(collected) == old_collected_count:
                # 수거 못했으면 스킵
                remaining_trash.remove(nearest)
        else:
            # 경로 없으면 스킵
            remaining_trash.remove(nearest)
        
        # 추가 주변 쓰레기 기회적 수거
        nearby = [t for t in remaining_trash if distance(current, t) <= 3]
        for t in nearby[:5]:  # 최대 5개
            if t in trash_set and t not in collected:
                route = find_path_astar(current, t, max_steps=100)
                if route and len(route) <= 5:  # 가까운 것만
                    follow_path_and_collect(route)
                    if t in remaining_trash:
                        remaining_trash.remove(t)
    
    return path[1:], collected

# ================================================
# 성능 평가 (이동거리 및 시간 포함)
# ================================================
def calculate_actual_distance(path):
    """경로의 실제 이동 거리 계산 (미터)"""
    if len(path) < 2:
        return 0.0
    
    total_distance = 0.0
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        # 유클리드 거리 * 격자 크기
        grid_dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        total_distance += grid_dist * GRID_CELL_SIZE_M
    
    return total_distance

def calculate_operation_time(path, collected_count, vessel_speed_ms, collection_time_s):
    """총 작업 시간 계산 (초)"""
    # 이동 시간
    distance_m = calculate_actual_distance(path)
    travel_time_s = distance_m / vessel_speed_ms if vessel_speed_ms > 0 else 0
    
    # 수거 시간
    collection_time_total = collected_count * collection_time_s
    
    # 총 시간
    total_time_s = travel_time_s + collection_time_total
    
    return {
        'travel_time_s': travel_time_s,
        'collection_time_s': collection_time_total,
        'total_time_s': total_time_s,
        'travel_time_min': travel_time_s / 60,
        'collection_time_min': collection_time_total / 60,
        'total_time_min': total_time_s / 60,
        'total_time_h': total_time_s / 3600
    }

def evaluate_performance(path, trash_positions, obstacle_positions, collected):
    total_trash = len(trash_positions)
    collected_count = len(collected)
    collection_rate = collected_count / total_trash if total_trash > 0 else 0
    
    collision_count = len([p for p in path if p in set(obstacle_positions)])
    search_distance = len(path)  # 격자 칸 수
    
    # 실제 거리 및 시간 계산
    actual_distance_m = calculate_actual_distance(path)
    actual_distance_km = actual_distance_m / 1000
    
    time_info = calculate_operation_time(path, collected_count, VESSEL_SPEED_MS, COLLECTION_TIME_S)
    
    return {
        "collection_rate": collection_rate,
        "collected_count": collected_count,
        "total_trash": total_trash,
        "collision_count": collision_count,
        "search_distance": search_distance,
        "actual_distance_m": actual_distance_m,
        "actual_distance_km": actual_distance_km,
        "travel_time_min": time_info['travel_time_min'],
        "collection_time_min": time_info['collection_time_min'],
        "total_operation_time_min": time_info['total_time_min'],
        "total_operation_time_h": time_info['total_time_h']
    }

# ================================================
# 격자 좌표를 위경도로 변환
# ================================================
def grid_to_latlon(grid_x, grid_y, transform_info):
    """격자 좌표를 실제 위경도로 변환"""
    # 격자 → km
    x_km = transform_info['x_min'] + (grid_x / 49) * (transform_info['x_max'] - transform_info['x_min'])
    y_km = transform_info['y_min'] + (grid_y / 49) * (transform_info['y_max'] - transform_info['y_min'])
    
    # km → 위경도
    origin_lat = transform_info['origin_lat']
    origin_lon = transform_info['origin_lon']
    
    lat = origin_lat + (y_km / 111.0)
    lon = origin_lon + (x_km / (111.0 * np.cos(np.radians(origin_lat))))
    
    return lat, lon

# ================================================
# 지도 시각화 (Folium)
# ================================================
def visualize_on_map(path, trash_positions, obstacle_positions, hotspots_latlon, 
                     collected, transform_info, save_path, metrics, title="Optimal Sweep Path"):
    """실제 지도 위에 경로 시각화 (레이어별)"""
    
    # 경로를 위경도로 변환
    path_latlon = [grid_to_latlon(x, y, transform_info) for x, y in path]
    
    # 지도 중심 계산
    if path_latlon:
        center_lat = np.mean([p[0] for p in path_latlon])
        center_lon = np.mean([p[1] for p in path_latlon])
    else:
        center_lat = transform_info['origin_lat']
        center_lon = transform_info['origin_lon']
    
    # Folium 지도 생성 (OpenStreetMap 기본)
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # 1️⃣ 핫스팟 레이어
    hotspot_layer = folium.FeatureGroup(name='🔥 Hotspots (상위 10개)', show=True)
    for idx, (lat, lon) in enumerate(hotspots_latlon[:10]):
        # 핫스팟 원형 영역
        folium.Circle(
            location=[lat, lon],
            radius=600,  # 6칸 * 100m
            color='orange',
            fill=True,
            fillColor='yellow',
            fillOpacity=0.3,
            weight=2,
            popup=f'Hotspot #{idx+1}',
            tooltip=f'핫스팟 #{idx+1}'
        ).add_to(hotspot_layer)
        
        # 핫스팟 마커
        folium.Marker(
            location=[lat, lon],
            icon=folium.Icon(color='red', icon='fire', prefix='fa'),
            popup=folium.Popup(f'<b>Hotspot #{idx+1}</b><br>위치: {lat:.5f}, {lon:.5f}', max_width=200),
            tooltip=f'🔥 핫스팟 #{idx+1}'
        ).add_to(hotspot_layer)
    
    hotspot_layer.add_to(m)
    
    # 2️⃣ 수거된 쓰레기 레이어
    collected_layer = folium.FeatureGroup(name='✅ 수거 완료 ({})개'.format(len(collected)), show=True)
    for trash in collected:
        lat, lon = grid_to_latlon(trash[0], trash[1], transform_info)
        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color='#2E7D32',
            fill=True,
            fillColor='#66BB6A',
            fillOpacity=0.9,
            weight=1.5,
            popup=f'✅ 수거 완료<br>격자: ({trash[0]}, {trash[1]})',
            tooltip='수거됨'
        ).add_to(collected_layer)
    
    m.add_child(collected_layer)
    
    # 3️⃣ 미수거 쓰레기 레이어
    uncollected = [t for t in trash_positions if t not in collected]
    uncollected_layer = folium.FeatureGroup(name='❌ 미수거 ({})개'.format(len(uncollected)), show=True)
    for trash in uncollected:
        lat, lon = grid_to_latlon(trash[0], trash[1], transform_info)
        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            color='#757575',
            fill=True,
            fillColor='#BDBDBD',
            fillOpacity=0.6,
            weight=1,
            popup=f'❌ 미수거<br>격자: ({trash[0]}, {trash[1]})',
            tooltip='미수거'
        ).add_to(uncollected_layer)
    
    m.add_child(uncollected_layer)
    
    # 4️⃣ 장애물 레이어
    obstacle_layer = folium.FeatureGroup(name='⚠️ 장애물 ({})개'.format(len(obstacle_positions)), show=True)
    for obs in obstacle_positions:
        lat, lon = grid_to_latlon(obs[0], obs[1], transform_info)
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color='#D32F2F',
            fill=True,
            fillColor='#EF5350',
            fillOpacity=0.8,
            weight=2,
            popup=f'⚠️ 장애물<br>격자: ({obs[0]}, {obs[1]})',
            tooltip='장애물'
        ).add_to(obstacle_layer)
    
    m.add_child(obstacle_layer)
    
    # 5️⃣ 수거 경로 레이어
    path_layer = folium.FeatureGroup(name='🛥️ 수거 경로 ({:.2f}km)'.format(metrics["actual_distance_km"]), show=True)
    
    if len(path_latlon) > 1:
        # 경로 선
        folium.PolyLine(
            locations=path_latlon,
            color='#1976D2',
            weight=4,
            opacity=0.8,
            popup=f'<b>수거 경로</b><br>총 거리: {metrics["actual_distance_km"]:.2f}km<br>소요 시간: {metrics["total_operation_time_h"]:.2f}시간',
            tooltip='수거 경로'
        ).add_to(path_layer)
        
        # 시작점
        folium.Marker(
            location=path_latlon[0],
            icon=folium.DivIcon(html=f'''
                <div style="
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 16px;
                    border: 3px solid white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                ">▶</div>
            '''),
            popup=f'<b>🟢 출발점</b><br>격자: ({path[0][0]}, {path[0][1]})',
            tooltip='출발'
        ).add_to(path_layer)
        
        # 종료점
        folium.Marker(
            location=path_latlon[-1],
            icon=folium.DivIcon(html=f'''
                <div style="
                    background-color: #F44336;
                    color: white;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 16px;
                    border: 3px solid white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                ">■</div>
            '''),
            popup=f'<b>🔴 종료점</b><br>격자: ({path[-1][0]}, {path[-1][1]})',
            tooltip='종료'
        ).add_to(path_layer)
    
    m.add_child(path_layer)
    
    # 6️⃣ 정보 패널 추가
    info_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; 
                width: 280px; 
                background-color: white; 
                border: 2px solid #2196F3;
                border-radius: 10px;
                padding: 15px;
                font-family: Arial, sans-serif;
                font-size: 12px;
                z-index: 9999;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0; color: #2196F3; border-bottom: 2px solid #2196F3; padding-bottom: 5px;">
            📊 작업 성능
        </h4>
        <table style="width: 100%; font-size: 11px;">
            <tr><td><b>🎯 수집률:</b></td><td style="text-align: right;">{metrics['collection_rate']:.1%}</td></tr>
            <tr><td><b>📦 수거량:</b></td><td style="text-align: right;">{metrics['collected_count']}/{metrics['total_trash']}개</td></tr>
            <tr><td><b>⚠️ 충돌:</b></td><td style="text-align: right;">{metrics['collision_count']}회</td></tr>
            <tr><td colspan="2" style="padding-top: 8px; border-top: 1px solid #ddd;"></td></tr>
            <tr><td><b>🛥️ 이동거리:</b></td><td style="text-align: right;">{metrics['actual_distance_km']:.2f}km</td></tr>
            <tr><td><b>📏 격자:</b></td><td style="text-align: right;">{metrics['search_distance']}칸</td></tr>
            <tr><td colspan="2" style="padding-top: 8px; border-top: 1px solid #ddd;"></td></tr>
            <tr><td><b>⏱️ 이동시간:</b></td><td style="text-align: right;">{metrics['travel_time_min']:.1f}분</td></tr>
            <tr><td><b>🗑️ 수거시간:</b></td><td style="text-align: right;">{metrics['collection_time_min']:.1f}분</td></tr>
            <tr><td><b>⏰ 총 작업:</b></td><td style="text-align: right; color: #f44336; font-weight: bold;">{metrics['total_operation_time_h']:.2f}시간</td></tr>
        </table>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(info_html))
    
    # 인터랙티브 범례 추가 (클릭으로 레이어 제어)
    legend_html = f'''
    <div id="legend" style="
        position: fixed; 
        bottom: 50px; 
        left: 50px; 
        background-color: white; 
        border: 2px solid #2196F3;
        border-radius: 8px;
        padding: 12px;
        font-size: 13px;
        font-family: Arial, sans-serif;
        z-index: 9999;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        min-width: 200px;">
        <div style="font-weight: bold; margin-bottom: 10px; color: #2196F3; border-bottom: 2px solid #2196F3; padding-bottom: 5px;">
            📍 범례 (클릭하여 ON/OFF)
        </div>
        <div style="cursor: pointer; padding: 5px; margin: 3px 0; border-radius: 4px; transition: background-color 0.2s;"
             onmouseover="this.style.backgroundColor='#E3F2FD'" 
             onmouseout="this.style.backgroundColor='white'"
             onclick="toggleLayer('🔥 핫스팟 (상위 10개)')">
            <span style="color: #FF6B35; font-size: 16px;">🔥</span> 핫스팟
        </div>
        <div style="cursor: pointer; padding: 5px; margin: 3px 0; border-radius: 4px; transition: background-color 0.2s;"
             onmouseover="this.style.backgroundColor='#E3F2FD'" 
             onmouseout="this.style.backgroundColor='white'"
             onclick="toggleLayer('🛥️ 수거 경로 ({metrics["actual_distance_km"]:.2f}km)')">
            <span style="color: #1976D2; font-size: 16px;">🛥️</span> 수거 경로
        </div>
        <div style="cursor: pointer; padding: 5px; margin: 3px 0; border-radius: 4px; transition: background-color 0.2s;"
             onmouseover="this.style.backgroundColor='#E3F2FD'" 
             onmouseout="this.style.backgroundColor='white'"
             onclick="toggleLayer('✅ 수거 완료 ({len(collected)})개')">
            <span style="color: #2E7D32; font-size: 16px;">✅</span> 수거 완료
        </div>
        <div style="cursor: pointer; padding: 5px; margin: 3px 0; border-radius: 4px; transition: background-color 0.2s;"
             onmouseover="this.style.backgroundColor='#E3F2FD'" 
             onmouseout="this.style.backgroundColor='white'"
             onclick="toggleLayer('❌ 미수거 ({len(uncollected)})개')">
            <span style="color: #757575; font-size: 16px;">❌</span> 미수거
        </div>
        <div style="cursor: pointer; padding: 5px; margin: 3px 0; border-radius: 4px; transition: background-color 0.2s;"
             onmouseover="this.style.backgroundColor='#E3F2FD'" 
             onmouseout="this.style.backgroundColor='white'"
             onclick="toggleLayer('⚠️ 장애물 ({len(obstacle_positions)})개')">
            <span style="color: #D32F2F; font-size: 16px;">⚠️</span> 장애물
        </div>
        <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 11px; color: #666;">
            💡 항목을 클릭하면 지도에서 표시/숨김
        </div>
    </div>
    
    <script>
    function toggleLayer(layerName) {{
        // Folium 레이어 컨트롤에서 해당 레이어 찾기
        var checkboxes = document.querySelectorAll('.leaflet-control-layers-overlays input');
        var labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
        
        for (var i = 0; i < labels.length; i++) {{
            var labelText = labels[i].textContent.trim();
            if (labelText === layerName) {{
                // 체크박스 토글
                checkboxes[i].click();
                break;
            }}
        }}
    }}
    </script>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # 레이어 컨트롤 추가 (펼친 상태, 우측 상단)
    folium.LayerControl(
        position='topright',
        collapsed=False,
        autoZIndex=True
    ).add_to(m)
    
    # 저장
    m.save(save_path)
    print(f"   ✅ 인터랙티브 지도 저장: {save_path}")
    
    return m
def visualize_path(path, trash_positions, obstacle_positions, hotspots, 
                   collected, save_path, title="Optimal Sweep Path"):
    """경로 시각화 (핫스팟 강조)"""
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # 격자 배경
    ax.set_xlim(-1, 50)
    ax.set_ylim(-1, 50)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    # 핫스팟 영역 표시
    for hx, hy in hotspots[:10]:  # 상위 10개만 표시
        circle = Circle((hx, hy), radius=6, facecolor='yellow', edgecolor='orange', 
                       alpha=0.2, linewidth=2, linestyle='--')
        ax.add_patch(circle)
        ax.plot(hx, hy, 'o', color='orange', markersize=12, 
               markeredgecolor='red', markeredgewidth=2, label='Hotspot' if hx == hotspots[0][0] else '')
    
    # 쓰레기 위치
    uncollected = [t for t in trash_positions if t not in collected]
    if uncollected:
        ux, uy = zip(*uncollected)
        ax.scatter(ux, uy, c='gray', s=30, alpha=0.4, marker='o', label='Uncollected Trash')
    
    if collected:
        cx, cy = zip(*collected)
        ax.scatter(cx, cy, c='green', s=50, alpha=0.7, marker='o', label='Collected Trash')
    
    # 장애물
    if obstacle_positions:
        ox, oy = zip(*obstacle_positions)
        ax.scatter(ox, oy, c='red', s=80, marker='X', alpha=0.6, label='Obstacles')
    
    # 경로
    if path:
        px, py = zip(*path)
        ax.plot(px, py, 'b-', linewidth=1.5, alpha=0.6, label='Sweep Path')
        ax.plot(path[0][0], path[0][1], 'go', markersize=15, 
               markeredgecolor='darkgreen', markeredgewidth=2, label='Start')
        ax.plot(path[-1][0], path[-1][1], 'rs', markersize=15,
               markeredgecolor='darkred', markeredgewidth=2, label='End')
    
    ax.set_xlabel('Grid X', fontsize=12)
    ax.set_ylabel('Grid Y', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()

# ================================================
# 메인 실행
# ================================================
def main():
    print("="*60)
    print("🌊 핫스팟 기반 최적 수거 경로 생성 시스템")
    print("="*60)
    
    # 1. 핫스팟 로드
    hotspot_json = os.path.join(HOTSPOT_DIR, 'hotspots.json')
    if not os.path.exists(hotspot_json):
        raise FileNotFoundError(f"핫스팟 파일을 찾을 수 없습니다: {hotspot_json}\nStep 3을 먼저 실행하세요.")
    
    hotspots_grid, hotspots_latlon, hotspot_data, transform_info = load_hotspots(hotspot_json)
    hotspot_radius = hotspot_data['settings']['min_distance_km']
    
    # 2. 환경 데이터 로드 (예시 - 실제 CSV 경로로 변경 필요)
    # env_data = pd.read_csv('2023.csv')  # 실제 환경 데이터
    # 테스트용 더미 데이터
    env_data = pd.DataFrame({
        '풍속(m/s)': np.random.uniform(2, 8, 100),
        '풍향(deg)': np.random.uniform(0, 360, 100),
        'GUST풍속(m/s)': np.random.uniform(3, 12, 100),
        '최대파고(m)': np.random.uniform(0.5, 3, 100),
        '유의파고(m)': np.random.uniform(0.3, 2, 100)
    })
    
    print(f"\n📊 환경 데이터: {len(env_data)}개 시나리오")
    
    # 3. 시뮬레이션 실행
    all_results = []
    test_count = min(50, len(env_data))  # 50개 시나리오 테스트
    
    for idx in range(test_count):
        env_row = env_data.iloc[idx]
        
        # 쓰레기 및 장애물 생성
        trash_positions = generate_hotspot_based_trash(50, env_row, hotspots_grid, 
                                                       hotspot_radius=int(hotspot_radius))
        obstacle_positions = generate_obstacles(50, env_row)
        
        start = (0, 0)
        t0 = time.time()
        
        # 경로 생성
        path, collected = hybrid_hotspot_algorithm(
            start, trash_positions, obstacle_positions,
            env=env_row, hotspots=hotspots_grid, 
            hotspot_radius=int(hotspot_radius),
            alpha=1.2, beta=0.15, lookahead=2
        )
        
        elapsed = time.time() - t0
        
        # 성능 평가
        metrics = evaluate_performance(path, trash_positions, obstacle_positions, collected)
        metrics['elapsed_time'] = elapsed
        all_results.append(metrics)
        
        # ✅ React UI용 dataset.json 생성 (+ public으로 자동 복사)
        dump_dataset_json(
            path, trash_positions, obstacle_positions, collected,
            transform_info, hotspots_latlon, metrics,
            copy_to_public=True  # public 폴더에 자동 복사
        )
        
        # 진행상황 출력
        if (idx + 1) % 10 == 0 or idx == 0:
            print(f"\n{'='*70}")
            print(f"[시나리오 {idx+1}/{test_count}] ({(idx+1)/test_count*100:.1f}% 완료)")
            print(f"{'='*70}")
            print(f"📊 수거 성능:")
            print(f"   - 수집률: {metrics['collection_rate']:.2%}")
            print(f"   - 수거량: {metrics['collected_count']}/{metrics['total_trash']}개")
            print(f"   - 충돌: {metrics['collision_count']}회")
            print(f"\n🛥️  이동 정보:")
            print(f"   - 격자 이동: {metrics['search_distance']}칸")
            print(f"   - 실제 거리: {metrics['actual_distance_km']:.2f}km ({metrics['actual_distance_m']:.0f}m)")
            print(f"\n⏱️  소요 시간:")
            print(f"   - 이동 시간: {metrics['travel_time_min']:.1f}분")
            print(f"   - 수거 시간: {metrics['collection_time_min']:.1f}분")
            print(f"   - 총 작업 시간: {metrics['total_operation_time_h']:.2f}시간 ({metrics['total_operation_time_min']:.1f}분)")
            print(f"   - 알고리즘 실행: {elapsed:.3f}초")
            print(f"{'='*70}")
        
        # 첫 번째 시나리오 시각화 (기존 격자 + 새로운 지도)
        if idx == 0:
            # 격자 시각화
            vis_path = os.path.join(RESULT_DIR, 'optimal_path_grid.png')
            visualize_path(path, trash_positions, obstacle_positions, 
                          hotspots_grid, collected, vis_path,
                          title=f"Optimal Sweep Path - Grid View (Collection: {metrics['collection_rate']:.1%})")
            print(f"   ✅ 격자 시각화 저장: {vis_path}")
            
            # 실제 지도 시각화
            map_path = os.path.join(RESULT_DIR, 'optimal_path_map.html')
            visualize_on_map(path, trash_positions, obstacle_positions,
                           hotspots_latlon, collected, transform_info, map_path, metrics,
                           title="Optimal Sweep Path - Map View")
            print(f"   🗺️ 브라우저에서 열기: {map_path}")
    
    # 4. 결과 저장
    results_df = pd.DataFrame(all_results)
    results_csv = os.path.join(RESULT_DIR, f'sweep_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    results_df.to_csv(results_csv, index=False, encoding='utf-8-sig')
    
    # 5. 통계 출력
    print("\n" + "="*70)
    print("📈 전체 성능 통계 요약 (50개 시나리오)")
    print("="*70)
    print(f"\n🎯 수거 성능:")
    print(f"   - 평균 수집률:     {results_df['collection_rate'].mean():.2%}")
    print(f"   - 평균 수거량:     {results_df['collected_count'].mean():.1f} / {results_df['total_trash'].mean():.1f}개")
    print(f"   - 평균 충돌 횟수:  {results_df['collision_count'].mean():.2f}회")
    
    print(f"\n🛥️  이동 통계:")
    print(f"   - 평균 격자 이동:  {results_df['search_distance'].mean():.1f}칸")
    print(f"   - 평균 실제 거리:  {results_df['actual_distance_km'].mean():.2f}km")
    print(f"   - 최대 이동 거리:  {results_df['actual_distance_km'].max():.2f}km")
    print(f"   - 최소 이동 거리:  {results_df['actual_distance_km'].min():.2f}km")
    
    print(f"\n⏱️  시간 통계:")
    print(f"   - 평균 이동 시간:  {results_df['travel_time_min'].mean():.1f}분")
    print(f"   - 평균 수거 시간:  {results_df['collection_time_min'].mean():.1f}분")
    print(f"   - 평균 총 작업:    {results_df['total_operation_time_h'].mean():.2f}시간 ({results_df['total_operation_time_min'].mean():.1f}분)")
    print(f"   - 최대 작업 시간:  {results_df['total_operation_time_h'].max():.2f}시간")
    print(f"   - 최소 작업 시간:  {results_df['total_operation_time_h'].min():.2f}시간")
    
    print(f"\n💻 알고리즘 성능:")
    print(f"   - 평균 실행 시간:  {results_df['elapsed_time'].mean():.3f}초")
    print(f"\n결과 파일 저장: {results_csv}")
    print("="*70)
    
    # 6. 요약 통계 저장
    summary = {
        "configuration": {
            "grid_cell_size_m": GRID_CELL_SIZE_M,
            "vessel_speed_ms": VESSEL_SPEED_MS,
            "vessel_speed_knots": VESSEL_SPEED_MS * 1.94384,  # m/s to knots
            "collection_time_per_trash_s": COLLECTION_TIME_S
        },
        "hotspot_count": len(hotspots_grid),
        "test_scenarios": test_count,
        "statistics": {
            "collection": {
                "avg_rate": float(results_df['collection_rate'].mean()),
                "avg_collected": float(results_df['collected_count'].mean()),
                "avg_total": float(results_df['total_trash'].mean())
            },
            "distance": {
                "avg_grid_distance": float(results_df['search_distance'].mean()),
                "avg_actual_distance_km": float(results_df['actual_distance_km'].mean()),
                "max_distance_km": float(results_df['actual_distance_km'].max()),
                "min_distance_km": float(results_df['actual_distance_km'].min())
            },
            "time": {
                "avg_travel_time_min": float(results_df['travel_time_min'].mean()),
                "avg_collection_time_min": float(results_df['collection_time_min'].mean()),
                "avg_total_operation_time_h": float(results_df['total_operation_time_h'].mean()),
                "max_operation_time_h": float(results_df['total_operation_time_h'].max()),
                "min_operation_time_h": float(results_df['total_operation_time_h'].min())
            },
            "performance": {
                "avg_collisions": float(results_df['collision_count'].mean()),
                "avg_algorithm_time_s": float(results_df['elapsed_time'].mean())
            }
        },
        "top_hotspots": hotspot_data['hotspots'][:5]
    }
    
    summary_path = os.path.join(RESULT_DIR, 'sweep_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 요약 통계 저장: {summary_path}\n")

if __name__ == '__main__':
    main()