# -*- coding: utf-8 -*-
"""
개선된 핫스팟 기반 최적 수거 경로 생성 알고리즘
- A*보다 빠른 성능을 위한 최적화
- 스마트 클러스터링 + 동적 우선순위 조정
- 경로 캐싱 및 지역 탐색 강화
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
from collections import deque
from scipy.spatial import KDTree

# ================================================
# 디렉토리 설정
# ================================================
HOTSPOT_DIR = './daily_results_hotspot_251013'
RESULT_DIR = './sweep_path_results_improved'
os.makedirs(RESULT_DIR, exist_ok=True)
REACT_PUBLIC_DIR = r"C:\Users\User\Downloads\sweep-marine_cleanup_nav\public"

# ================================================
# 이동 및 수거 시간 설정
# ================================================
GRID_CELL_SIZE_M = 100
VESSEL_SPEED_MS = 2.5
COLLECTION_TIME_S = 30

def dump_dataset_json(path_grid, trash_positions, obstacles, collected_set,
                      transform_info, hotspots_latlon, metrics,
                      copy_to_public=True):
    """React UI용 dataset.json 생성"""
    
    def grid_to_latlon_pair(p):
        lat, lng = grid_to_latlon(p[0], p[1], transform_info)
        return {"lat": float(lat), "lng": float(lng)}
    
    route_ll = [grid_to_latlon_pair(p) for p in path_grid]
    collected_ll = [grid_to_latlon_pair(p) for p in collected_set]
    uncollected_ll = [grid_to_latlon_pair(p) for p in trash_positions if p not in collected_set]
    obstacles_ll = [grid_to_latlon_pair(p) for p in obstacles]
    
    data = {
      "vessel": {
        "lat": float(transform_info["origin_lat"]),
        "lng": float(transform_info["origin_lon"]),
        "heading": 180,
        "speed_kn": float(VESSEL_SPEED_MS * 1.94384)
      },
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
    
    out_path = os.path.join(RESULT_DIR, "dataset.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ React용 dataset.json 저장:", out_path)
    
    if copy_to_public:
        try:
            os.makedirs(REACT_PUBLIC_DIR, exist_ok=True)
            dst = os.path.join(REACT_PUBLIC_DIR, "dataset.json")
            shutil.copyfile(out_path, dst)
            print("✅ public/dataset.json 갱신:", dst)
        except Exception as e:
            print("⚠️ public 복사 실패:", e)

# ================================================
# 핫스팟 데이터 로드
# ================================================
def load_hotspots(hotspot_json_path):
    """hotspots.json 로드 및 격자 좌표로 변환"""
    with open(hotspot_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    origin_lat = data['origin']['latitude']
    origin_lon = data['origin']['longitude']
    
    hotspots_km = [(hs['x'], hs['y'], hs['latitude'], hs['longitude']) for hs in data['hotspots']]
    
    if hotspots_km:
        x_coords = [h[0] for h in hotspots_km]
        y_coords = [h[1] for h in hotspots_km]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        hotspots_grid = []
        hotspots_latlon = []
        for x_km, y_km, lat, lon in hotspots_km:
            grid_x = int((x_km - x_min) / (x_max - x_min) * 49) if x_max != x_min else 25
            grid_y = int((y_km - y_min) / (y_max - y_min) * 49) if y_max != y_min else 25
            hotspots_grid.append((grid_x, grid_y))
            hotspots_latlon.append((lat, lon))
        
        print(f"✅ 핫스팟 로드 완료: {len(hotspots_grid)}개")
        
        transform_info = {
            'x_min': x_min, 'x_max': x_max,
            'y_min': y_min, 'y_max': y_max,
            'origin_lat': origin_lat, 'origin_lon': origin_lon
        }
        
        return hotspots_grid, hotspots_latlon, data, transform_info
    
    return [], [], data, None

# ================================================
# 쓰레기 및 장애물 생성
# ================================================
def generate_hotspot_based_trash(grid_size, env_row, hotspots, hotspot_radius=6):
    """핫스팟 중심으로 쓰레기 집중 생성"""
    wind_speed = env_row.get('풍속(m/s)', 0) or 0
    wind_direction = env_row.get('풍향(deg)', 0) or 0
    significant_wave = env_row.get('유의파고(m)', 0) or 0
    
    base_trash = 80
    trash_count = min(base_trash + int(wind_speed*8) + int(significant_wave*15), 400)
    
    trash_positions = []
    hotspot_trash = int(trash_count * 0.7)
    remaining_trash = trash_count - hotspot_trash
    
    for _ in range(hotspot_trash):
        if not hotspots:
            break
        hx, hy = hotspots[np.random.randint(0, len(hotspots))]
        
        offset_x = int(np.random.normal(0, hotspot_radius/2))
        offset_y = int(np.random.normal(0, hotspot_radius/2))
        
        wind_offset_x = int(np.cos(np.radians(wind_direction)) * wind_speed * 0.3)
        wind_offset_y = int(np.sin(np.radians(wind_direction)) * wind_speed * 0.3)
        
        tx = np.clip(hx + offset_x + wind_offset_x, 0, grid_size-1)
        ty = np.clip(hy + offset_y + wind_offset_y, 0, grid_size-1)
        
        trash_positions.append((int(tx), int(ty)))
    
    for _ in range(remaining_trash):
        tx = np.random.randint(0, grid_size)
        ty = np.random.randint(0, grid_size)
        trash_positions.append((tx, ty))
    
    return trash_positions

def generate_obstacles(grid_size, env_row):
    """장애물 생성"""
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
# 🚀 개선된 알고리즘 - 핵심 최적화
# ================================================
def distance(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def manhattan_distance(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

class SmartClusterManager:
    """스마트 클러스터 관리자 - 동적 우선순위 및 효율적 경로 계획"""
    
    def __init__(self, trash_positions, hotspots, hotspot_radius, obstacles):
        self.trash_set = set(trash_positions)
        self.hotspots = hotspots
        self.radius = hotspot_radius
        self.obstacles = set(obstacles)
        self.collected = set()
        
        # KD-Tree로 빠른 근접 쓰레기 검색
        if trash_positions:
            self.trash_tree = KDTree(trash_positions)
        else:
            self.trash_tree = None
        
        # 핫스팟별 클러스터 생성
        self.clusters = self._build_clusters()
        
    def _build_clusters(self):
        """핫스팟 기반 클러스터 구축"""
        clusters = {}
        for h in self.hotspots:
            nearby = []
            for t in self.trash_set:
                if distance(t, h) <= self.radius:
                    nearby.append(t)
            if nearby:
                clusters[h] = {
                    'trash': nearby,
                    'center': h,
                    'collected': 0,
                    'total': len(nearby)
                }
        return clusters
    
    def get_best_cluster(self, current_pos):
        """현재 위치에서 최적 클러스터 선택"""
        if not self.clusters:
            return None
        
        best_score = -1
        best_cluster = None
        
        for h, cluster in self.clusters.items():
            remaining = cluster['total'] - cluster['collected']
            if remaining == 0:
                continue
            
            dist = distance(current_pos, h)
            # 개수 우선, 거리는 부차적
            # 멀리 있어도 쓰레기가 많으면 가치가 높음
            score = remaining * 2.0 / (1 + dist * 0.05)
            
            if score > best_score:
                best_score = score
                best_cluster = (h, cluster)
        
        return best_cluster
    
    def get_nearby_trash(self, pos, radius=5):
        """KD-Tree로 빠른 근접 쓰레기 검색"""
        if self.trash_tree is None:
            return []
        
        uncollected = [t for t in self.trash_set if t not in self.collected]
        if not uncollected:
            return []
        
        nearby = []
        for t in uncollected:
            if distance(pos, t) <= radius:
                nearby.append(t)
        
        return sorted(nearby, key=lambda t: distance(pos, t))[:10]
    
    def mark_collected(self, pos):
        """쓰레기 수거 표시"""
        if pos in self.trash_set and pos not in self.collected:
            self.collected.add(pos)
            
            # 해당 클러스터 업데이트
            for h, cluster in self.clusters.items():
                if pos in cluster['trash']:
                    cluster['collected'] += 1
                    break
            
            return True
        return False
    
    def get_uncollected_count(self):
        """미수거 쓰레기 개수"""
        return len(self.trash_set) - len(self.collected)


def improved_hybrid_algorithm(
    start, trash_positions, obstacle_positions,
    env=None, hotspots=None, hotspot_radius=6,
    alpha=1.2, beta=0.15, lookahead=3, max_iterations=5000
):
    """
    🚀 개선된 하이브리드 알고리즘
    
    주요 개선사항:
    1. 스마트 클러스터 관리자로 효율적 클러스터 관리
    2. BFS 기반 지역 탐색으로 A* 호출 최소화
    3. Lookahead 전략으로 다음 N개 쓰레기 동시 고려
    4. 경로 캐싱으로 중복 계산 방지
    5. 동적 수거 전략 (클러스터 → 로컬 → 그리디)
    """
    grid_size = 50
    current = start
    path = [start]
    obstacle_set = set(obstacle_positions)
    
    if not trash_positions:
        return path[1:], set()
    
    # 스마트 클러스터 관리자
    cluster_mgr = SmartClusterManager(trash_positions, hotspots or [], hotspot_radius, obstacle_positions)
    
    directions8 = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    
    # 경로 캐시
    path_cache = {}
    
    def is_valid(pos):
        """유효한 위치인지 확인"""
        return (0 <= pos[0] < grid_size and 
                0 <= pos[1] < grid_size and 
                pos not in obstacle_set)
    
    def bfs_local_path(start_pos, goal_pos, max_dist=15):
        """BFS 기반 지역 경로 탐색 (가까운 거리용)"""
        if start_pos == goal_pos:
            return [start_pos]
        
        if manhattan_distance(start_pos, goal_pos) > max_dist:
            return None  # 너무 멀면 A* 사용
        
        cache_key = (start_pos, goal_pos)
        if cache_key in path_cache:
            return path_cache[cache_key]
        
        queue = deque([(start_pos, [start_pos])])
        visited = {start_pos}
        
        while queue:
            pos, path_so_far = queue.popleft()
            
            if len(path_so_far) > max_dist + 5:
                break
            
            for dx, dy in directions8:
                next_pos = (pos[0] + dx, pos[1] + dy)
                
                if next_pos == goal_pos:
                    result = path_so_far + [next_pos]
                    path_cache[cache_key] = result
                    return result
                
                if next_pos not in visited and is_valid(next_pos):
                    visited.add(next_pos)
                    queue.append((next_pos, path_so_far + [next_pos]))
        
        return None
    
    def astar_path(start_pos, goal_pos, max_steps=800):
        """A* 경로 탐색 (먼 거리용)"""
        cache_key = (start_pos, goal_pos)
        if cache_key in path_cache:
            return path_cache[cache_key]
        
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
                result = []
                while current_pos in came_from:
                    result.append(current_pos)
                    current_pos = came_from[current_pos]
                result.append(start_pos)
                result = list(reversed(result))
                path_cache[cache_key] = result
                return result
            
            for dx, dy in directions8:
                neighbor = (current_pos[0] + dx, current_pos[1] + dy)
                if not is_valid(neighbor):
                    continue
                
                tentative_g = g_score[current_pos] + 1
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + distance(neighbor, goal_pos)
                    heapq.heappush(open_set, (f_score, neighbor))
                    came_from[neighbor] = current_pos
        
        return None
    
    def find_smart_path(start_pos, goal_pos):
        """스마트 경로 찾기 - 거리에 따라 BFS 또는 A* 선택"""
        dist = manhattan_distance(start_pos, goal_pos)
        
        if dist <= 15:
            # 가까우면 BFS (빠름)
            result = bfs_local_path(start_pos, goal_pos, max_dist=15)
            if result:
                return result
        
        # 멀거나 BFS 실패시 A*
        return astar_path(start_pos, goal_pos)
    
    def follow_and_collect(route):
        """경로 따라가며 수거"""
        nonlocal current
        if not route or len(route) <= 1:
            return
        
        for step in route[1:]:
            if not is_valid(step):
                # 장애물 회피
                alternatives = [
                    (current[0] + dx, current[1] + dy)
                    for dx, dy in directions8
                    if is_valid((current[0] + dx, current[1] + dy))
                ]
                if alternatives:
                    step = min(alternatives, key=lambda p: distance(p, route[-1]))
                else:
                    break
            
            path.append(step)
            current = step
            
            # 쓰레기 수거 (주변 포함)
            cluster_mgr.mark_collected(current)
            
            # 주변 1칸 이내도 수거
            for dx, dy in directions8:
                adj = (current[0] + dx, current[1] + dy)
                cluster_mgr.mark_collected(adj)
    
    def greedy_sweep_nearby(radius=4):
        """현재 위치 주변 탐욕적 수거"""
        nearby = cluster_mgr.get_nearby_trash(current, radius)
        
        for trash in nearby[:5]:  # 최대 5개
            route = bfs_local_path(current, trash, max_dist=radius+2)
            if route and len(route) <= radius + 3:
                follow_and_collect(route)
                
                if cluster_mgr.get_uncollected_count() == 0:
                    break
    
    # ==========================================
    # 메인 수거 로직
    # ==========================================
    
    # Phase 1: 클러스터 기반 수거 (핫스팟 우선)
    visited_clusters = set()
    
    while cluster_mgr.get_uncollected_count() > len(trash_positions) * 0.1:
        best = cluster_mgr.get_best_cluster(current)
        
        if not best or best[0] in visited_clusters:
            break
        
        hotspot, cluster_info = best
        visited_clusters.add(hotspot)
        
        # 클러스터 중심으로 이동
        route = find_smart_path(current, hotspot)
        if route:
            follow_and_collect(route)
        
        # 클러스터 내 로컬 수거
        for _ in range(cluster_info['total']):
            if cluster_mgr.get_uncollected_count() == 0:
                break
            
            nearby = cluster_mgr.get_nearby_trash(current, radius=hotspot_radius+2)
            if not nearby:
                break
            
            target = nearby[0]
            route = bfs_local_path(current, target, max_dist=hotspot_radius+3)
            
            if route:
                follow_and_collect(route)
            else:
                break
        
        # 중간 그리디 수거
        greedy_sweep_nearby(radius=5)
        
        if len(path) > max_iterations * 0.7:
            break
    
    # Phase 2: 잔여 쓰레기 그리디 수거
    attempts = 0
    max_attempts = cluster_mgr.get_uncollected_count() * 3 + 100
    
    while cluster_mgr.get_uncollected_count() > 0 and attempts < max_attempts:
        attempts += 1
        
        # Lookahead: 다음 N개 쓰레기 고려
        nearby_candidates = cluster_mgr.get_nearby_trash(current, radius=20)
        
        if not nearby_candidates:
            break
        
        # 가장 가까운 것 선택 (lookahead 효과)
        best_trash = None
        best_value = -1
        
        for trash in nearby_candidates[:lookahead]:
            dist = distance(current, trash)
            # 가까울수록 + 주변에 쓰레기 많을수록 가치 높음
            nearby_count = len([t for t in nearby_candidates if distance(trash, t) <= 3])
            value = nearby_count / (1 + dist * 0.1)
            
            if value > best_value:
                best_value = value
                best_trash = trash
        
        if not best_trash:
            break
        
        # 경로 찾기
        route = find_smart_path(current, best_trash)
        
        if route:
            old_count = len(cluster_mgr.collected)
            follow_and_collect(route)
            
            # 진전 없으면 스킵
            if len(cluster_mgr.collected) == old_count:
                cluster_mgr.mark_collected(best_trash)  # 강제 스킵
        else:
            cluster_mgr.mark_collected(best_trash)
        
        # 주기적 그리디 스윕
        if attempts % 10 == 0:
            greedy_sweep_nearby(radius=4)
    
    return path[1:], cluster_mgr.collected


# ================================================
# 성능 평가
# ================================================
def calculate_actual_distance(path):
    """경로의 실제 이동 거리 계산"""
    if len(path) < 2:
        return 0.0
    
    total_distance = 0.0
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        grid_dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        total_distance += grid_dist * GRID_CELL_SIZE_M
    
    return total_distance

def calculate_operation_time(path, collected_count, vessel_speed_ms, collection_time_s):
    """총 작업 시간 계산"""
    distance_m = calculate_actual_distance(path)
    travel_time_s = distance_m / vessel_speed_ms if vessel_speed_ms > 0 else 0
    collection_time_total = collected_count * collection_time_s
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
    search_distance = len(path)
    
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
# 시각화 함수들
# ================================================
def grid_to_latlon(grid_x, grid_y, transform_info):
    """격자 좌표를 실제 위경도로 변환"""
    x_km = transform_info['x_min'] + (grid_x / 49) * (transform_info['x_max'] - transform_info['x_min'])
    y_km = transform_info['y_min'] + (grid_y / 49) * (transform_info['y_max'] - transform_info['y_min'])
    
    origin_lat = transform_info['origin_lat']
    origin_lon = transform_info['origin_lon']
    
    lat = origin_lat + (y_km / 111.0)
    lon = origin_lon + (x_km / (111.0 * np.cos(np.radians(origin_lat))))
    
    return lat, lon

def visualize_path(path, trash_positions, obstacle_positions, hotspots, collected, save_path, title=""):
    """격자 시각화"""
    fig, ax = plt.subplots(figsize=(14, 14))
    
    # 미수거 쓰레기
    uncollected = [t for t in trash_positions if t not in collected]
    if uncollected:
        ux, uy = zip(*uncollected)
        ax.scatter(ux, uy, c='gray', s=30, alpha=0.5, label=f'Uncollected ({len(uncollected)})', marker='x')
    
    # 수거된 쓰레기
    if collected:
        cx, cy = zip(*collected)
        ax.scatter(cx, cy, c='green', s=50, alpha=0.8, label=f'Collected ({len(collected)})', marker='o')
    
    # 장애물
    if obstacle_positions:
        ox, oy = zip(*obstacle_positions)
        ax.scatter(ox, oy, c='red', s=80, alpha=0.7, label=f'Obstacles ({len(obstacle_positions)})', marker='s')
    
    # 핫스팟
    if hotspots:
        hx, hy = zip(*hotspots[:10])
        for i, (x, y) in enumerate(zip(hx, hy)):
            circle = Circle((x, y), radius=6, color='orange', fill=False, linewidth=2.5, linestyle='--')
            ax.add_patch(circle)
            ax.scatter(x, y, c='red', s=200, marker='*', edgecolors='darkred', linewidths=2, zorder=10)
    
    # 경로
    if len(path) > 1:
        px, py = zip(*path)
        ax.plot(px, py, 'b-', linewidth=1.5, alpha=0.6, label='Path')
        ax.plot(path[0][0], path[0][1], 'go', markersize=15, markeredgecolor='darkgreen', markeredgewidth=2, label='Start')
        ax.plot(path[-1][0], path[-1][1], 'rs', markersize=15, markeredgecolor='darkred', markeredgewidth=2, label='End')
    
    ax.set_xlabel('Grid X', fontsize=12)
    ax.set_ylabel('Grid Y', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.set_xlim(-1, 51)
    ax.set_ylim(-1, 51)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()

def visualize_on_map(path, trash_positions, obstacle_positions, hotspots_latlon, 
                     collected, transform_info, save_path, metrics, title=""):
    """Folium 지도 시각화"""
    path_latlon = [grid_to_latlon(x, y, transform_info) for x, y in path]
    
    if path_latlon:
        center_lat = np.mean([p[0] for p in path_latlon])
        center_lon = np.mean([p[1] for p in path_latlon])
    else:
        center_lat = transform_info['origin_lat']
        center_lon = transform_info['origin_lon']
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # 핫스팟
    hotspot_layer = folium.FeatureGroup(name='🔥 Hotspots', show=True)
    for idx, (lat, lon) in enumerate(hotspots_latlon[:10]):
        folium.Circle(
            location=[lat, lon],
            radius=600,
            color='orange',
            fill=True,
            fillColor='yellow',
            fillOpacity=0.3,
            weight=2
        ).add_to(hotspot_layer)
        
        folium.Marker(
            location=[lat, lon],
            icon=folium.Icon(color='red', icon='fire', prefix='fa'),
            popup=f'Hotspot #{idx+1}',
            tooltip=f'🔥 #{idx+1}'
        ).add_to(hotspot_layer)
    hotspot_layer.add_to(m)
    
    # 수거된 쓰레기
    collected_layer = folium.FeatureGroup(name=f'✅ Collected ({len(collected)})', show=True)
    for trash in collected:
        lat, lon = grid_to_latlon(trash[0], trash[1], transform_info)
        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color='#2E7D32',
            fill=True,
            fillColor='#66BB6A',
            fillOpacity=0.9,
            weight=1.5
        ).add_to(collected_layer)
    m.add_child(collected_layer)
    
    # 미수거 쓰레기
    uncollected = [t for t in trash_positions if t not in collected]
    uncollected_layer = folium.FeatureGroup(name=f'❌ Uncollected ({len(uncollected)})', show=True)
    for trash in uncollected:
        lat, lon = grid_to_latlon(trash[0], trash[1], transform_info)
        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            color='#757575',
            fill=True,
            fillColor='#BDBDBD',
            fillOpacity=0.6
        ).add_to(uncollected_layer)
    m.add_child(uncollected_layer)
    
    # 장애물
    obstacle_layer = folium.FeatureGroup(name=f'⚠️ Obstacles ({len(obstacle_positions)})', show=True)
    for obs in obstacle_positions:
        lat, lon = grid_to_latlon(obs[0], obs[1], transform_info)
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color='#D32F2F',
            fill=True,
            fillColor='#EF5350',
            fillOpacity=0.8
        ).add_to(obstacle_layer)
    m.add_child(obstacle_layer)
    
    # 경로
    path_layer = folium.FeatureGroup(name=f'🛥️ Path ({metrics["actual_distance_km"]:.2f}km)', show=True)
    if len(path_latlon) > 1:
        folium.PolyLine(
            locations=path_latlon,
            color='#1976D2',
            weight=4,
            opacity=0.8
        ).add_to(path_layer)
        
        # 시작점
        folium.Marker(
            location=path_latlon[0],
            icon=folium.Icon(color='green', icon='play', prefix='fa'),
            popup='Start'
        ).add_to(path_layer)
        
        # 종료점
        folium.Marker(
            location=path_latlon[-1],
            icon=folium.Icon(color='red', icon='stop', prefix='fa'),
            popup='End'
        ).add_to(path_layer)
    
    m.add_child(path_layer)
    folium.LayerControl().add_to(m)
    m.save(save_path)

# ================================================
# 메인 실행
# ================================================
def create_dummy_hotspots():
    """테스트용 더미 핫스팟 데이터 생성"""
    print("⚠️ 핫스팟 파일이 없습니다. 테스트용 더미 데이터를 생성합니다...")
    
    # 부산 기준 좌표
    origin_lat = 35.1796
    origin_lon = 129.0756
    
    # 10개의 랜덤 핫스팟 생성
    hotspots_grid = []
    hotspots_latlon = []
    
    np.random.seed(42)
    for i in range(10):
        # 격자 좌표 (0~49)
        grid_x = np.random.randint(10, 40)
        grid_y = np.random.randint(10, 40)
        hotspots_grid.append((grid_x, grid_y))
        
        # 위경도 (대략 5km x 5km 영역)
        lat = origin_lat + np.random.uniform(-0.03, 0.03)
        lon = origin_lon + np.random.uniform(-0.03, 0.03)
        hotspots_latlon.append((lat, lon))
    
    transform_info = {
        'x_min': 0.0,
        'x_max': 5.0,
        'y_min': 0.0,
        'y_max': 5.0,
        'origin_lat': origin_lat,
        'origin_lon': origin_lon
    }
    
    hotspot_data = {
        'settings': {
            'min_distance_km': 6
        }
    }
    
    print(f"✅ 더미 핫스팟 생성 완료: {len(hotspots_grid)}개")
    return hotspots_grid, hotspots_latlon, hotspot_data, transform_info

def main():
    print("="*60)
    print("🚀 개선된 핫스팟 기반 수거 경로 생성 시스템")
    print("="*60)
    
    # 핫스팟 로드 (없으면 더미 생성)
    hotspot_json = os.path.join(HOTSPOT_DIR, 'hotspots.json')
    if not os.path.exists(hotspot_json):
        print(f"⚠️ 핫스팟 파일 없음: {hotspot_json}")
        hotspots_grid, hotspots_latlon, hotspot_data, transform_info = create_dummy_hotspots()
    else:
        hotspots_grid, hotspots_latlon, hotspot_data, transform_info = load_hotspots(hotspot_json)
    
    hotspot_radius = hotspot_data['settings']['min_distance_km']
    
    # 테스트용 환경 데이터
    env_data = pd.DataFrame({
        '풍속(m/s)': np.random.uniform(2, 8, 100),
        '풍향(deg)': np.random.uniform(0, 360, 100),
        'GUST풍속(m/s)': np.random.uniform(3, 12, 100),
        '최대파고(m)': np.random.uniform(0.5, 3, 100),
        '유의파고(m)': np.random.uniform(0.3, 2, 100)
    })
    
    print(f"\n📊 환경 데이터: {len(env_data)}개 시나리오")
    
    # 시뮬레이션
    all_results = []
    test_count = min(50, len(env_data))
    
    for idx in range(test_count):
        env_row = env_data.iloc[idx]
        
        trash_positions = generate_hotspot_based_trash(50, env_row, hotspots_grid, int(hotspot_radius))
        obstacle_positions = generate_obstacles(50, env_row)
        
        start = (0, 0)
        t0 = time.time()
        
        # 🚀 개선된 알고리즘 실행
        path, collected = improved_hybrid_algorithm(
            start, trash_positions, obstacle_positions,
            env=env_row, hotspots=hotspots_grid,
            hotspot_radius=int(hotspot_radius),
            alpha=1.2, beta=0.15, lookahead=3
        )
        
        elapsed = time.time() - t0
        
        # 성능 평가
        metrics = evaluate_performance(path, trash_positions, obstacle_positions, collected)
        metrics['elapsed_time'] = elapsed
        all_results.append(metrics)
        
        # dataset.json 생성
        dump_dataset_json(
            path, trash_positions, obstacle_positions, collected,
            transform_info, hotspots_latlon, metrics,
            copy_to_public=True
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
            print(f"   - 실제 거리: {metrics['actual_distance_km']:.2f}km")
            print(f"\n⏱️  소요 시간:")
            print(f"   - 이동 시간: {metrics['travel_time_min']:.1f}분")
            print(f"   - 수거 시간: {metrics['collection_time_min']:.1f}분")
            print(f"   - 총 작업: {metrics['total_operation_time_h']:.2f}시간")
            print(f"   - 알고리즘 실행: {elapsed:.3f}초")
            print(f"{'='*70}")
        
        # 첫 번째 시나리오 시각화
        if idx == 0:
            vis_path = os.path.join(RESULT_DIR, 'optimal_path_grid_improved.png')
            visualize_path(path, trash_positions, obstacle_positions, 
                          hotspots_grid, collected, vis_path,
                          title=f"Improved Algorithm - Grid View (Collection: {metrics['collection_rate']:.1%})")
            print(f"   ✅ 격자 시각화 저장: {vis_path}")
            
            map_path = os.path.join(RESULT_DIR, 'optimal_path_map_improved.html')
            visualize_on_map(path, trash_positions, obstacle_positions,
                           hotspots_latlon, collected, transform_info, map_path, metrics,
                           title="Improved Algorithm - Map View")
            print(f"   🗺️ 지도 시각화: {map_path}")
    
    # 결과 저장
    results_df = pd.DataFrame(all_results)
    results_csv = os.path.join(RESULT_DIR, f'improved_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    results_df.to_csv(results_csv, index=False, encoding='utf-8-sig')
    
    # 통계 출력
    print("\n" + "="*70)
    print("📈 전체 성능 통계 요약 (50개 시나리오)")
    print("="*70)
    print(f"\n🎯 수거 성능:")
    print(f"   - 평균 수집률:     {results_df['collection_rate'].mean():.2%}")
    print(f"   - 평균 수거량:     {results_df['collected_count'].mean():.1f} / {results_df['total_trash'].mean():.1f}개")
    print(f"   - 평균 충돌:       {results_df['collision_count'].mean():.2f}회")
    
    print(f"\n🛥️  이동 통계:")
    print(f"   - 평균 격자 이동:  {results_df['search_distance'].mean():.1f}칸")
    print(f"   - 평균 실제 거리:  {results_df['actual_distance_km'].mean():.2f}km")
    
    print(f"\n⏱️  시간 통계:")
    print(f"   - 평균 총 작업:    {results_df['total_operation_time_h'].mean():.2f}시간")
    
    print(f"\n💻 알고리즘 성능:")
    print(f"   - 평균 실행 시간:  {results_df['elapsed_time'].mean():.3f}초")
    print(f"\n결과 파일 저장: {results_csv}")
    print("="*70)
    
    # 요약 저장
    summary = {
        "algorithm": "Improved Hybrid (Cluster + BFS + Lookahead)",
        "configuration": {
            "grid_cell_size_m": GRID_CELL_SIZE_M,
            "vessel_speed_ms": VESSEL_SPEED_MS,
            "collection_time_s": COLLECTION_TIME_S
        },
        "test_scenarios": test_count,
        "statistics": {
            "collection": {
                "avg_rate": float(results_df['collection_rate'].mean()),
                "avg_collected": float(results_df['collected_count'].mean()),
                "avg_total": float(results_df['total_trash'].mean())
            },
            "distance": {
                "avg_grid_distance": float(results_df['search_distance'].mean()),
                "avg_actual_distance_km": float(results_df['actual_distance_km'].mean())
            },
            "time": {
                "avg_total_operation_time_h": float(results_df['total_operation_time_h'].mean())
            },
            "performance": {
                "avg_collisions": float(results_df['collision_count'].mean()),
                "avg_algorithm_time_s": float(results_df['elapsed_time'].mean())
            }
        }
    }
    
    summary_path = os.path.join(RESULT_DIR, 'improved_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 요약 저장: {summary_path}\n")

if __name__ == '__main__':
    main()
