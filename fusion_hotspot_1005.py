import pandas as pd
import random
import numpy as np
import time
import heapq
import math
import os
import glob

# ================================================
# 작업 디렉토리 설정
# ================================================
os.chdir("C:/sweep_algorithm_test/")
os.makedirs("algo_test_results", exist_ok=True)

# ================================================
# CSV 데이터 로드
# ================================================
def load_data(file_path):
    return pd.read_csv(file_path)

data = load_data('2023.csv')

# ================================================
# 🔴 핫스팟 설정 (필수)
#   - 격자 좌표계(0~49) 기준으로 5~10개 지정
#   - 반경(radius) 안의 쓰레기를 해당 핫스팟 소속으로 간주
# ================================================
HOTSPOTS = [(8, 6), (12, 30), (20, 22), (33, 18), (40, 40)]  # 예시
HOTSPOT_RADIUS = 6

# ================================================
# 환경 기반 쓰레기 및 장애물 생성 함수
# ================================================
def generate_trash_obstacles_with_environment(grid_size, env_row):
    # === 환경 데이터 읽기 ===
    wind_speed = env_row['풍속(m/s)']
    wind_direction = env_row['풍향(deg)']
    gust_speed = env_row['GUST풍속(m/s)']
    max_wave_height = env_row['최대파고(m)']
    significant_wave_height = env_row['유의파고(m)']
    mean_wave_height = env_row['평균파고(m)']
    wave_period = env_row['파주기(sec)']
    wave_direction = env_row['파향(deg)']

    # === NaN 처리 (기본값 설정) ===
    if pd.isna(wind_speed): wind_speed = 0
    if pd.isna(wind_direction): wind_direction = 0
    if pd.isna(gust_speed): gust_speed = 0
    if pd.isna(max_wave_height): max_wave_height = 0
    if pd.isna(significant_wave_height): significant_wave_height = 0
    if pd.isna(mean_wave_height): mean_wave_height = 0
    if pd.isna(wave_period): wave_period = 0
    if pd.isna(wave_direction): wave_direction = 0

    # === 쓰레기와 장애물 개수 결정 ===
    base_trash = 50
    base_obstacles = 10

    trash_count = base_trash + int(wind_speed * 5) + int(significant_wave_height * 10)
    obstacle_count = base_obstacles + int(gust_speed * 2) + int(max_wave_height * 5)

    trash_count = min(trash_count, 300)
    obstacle_count = min(obstacle_count, 50)

    # === 쓰레기 배치 (바람 방향 고려) ===
    trash_positions = []
    for _ in range(trash_count):
        base_x = random.randint(0, grid_size-1)
        base_y = random.randint(0, grid_size-1)

        offset_distance = random.randint(0, 5)
        offset_x = int(np.cos(np.radians(wind_direction)) * offset_distance)
        offset_y = int(np.sin(np.radians(wind_direction)) * offset_distance)

        new_x = max(0, min(grid_size-1, base_x + offset_x))
        new_y = max(0, min(grid_size-1, base_y + offset_y))

        trash_positions.append((new_x, new_y))

    # === 장애물 배치 (파향 고려) ===
    obstacle_positions = []
    for _ in range(obstacle_count):
        base_x = random.randint(0, grid_size-1)
        base_y = random.randint(0, grid_size-1)

        offset_distance = random.randint(0, 3)
        offset_x = int(np.cos(np.radians(wave_direction)) * offset_distance)
        offset_y = int(np.sin(np.radians(wave_direction)) * offset_distance)

        new_x = max(0, min(grid_size-1, base_x + offset_x))
        new_y = max(0, min(grid_size-1, base_y + offset_y))

        obstacle_positions.append((new_x, new_y))

    return trash_positions, obstacle_positions

# ================================================
# Fusion
# ================================================
# ======================
# 유틸리티 함수
# ======================

def distance(a, b):
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)

def adjusted_distance(a, b, wind_direction):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    base_dist = math.sqrt(dx**2 + dy**2)

    angle_to_target = math.degrees(math.atan2(dy, dx)) % 360
    angle_diff = abs(wind_direction - angle_to_target)
    angle_diff = min(angle_diff, 360 - angle_diff)

    wind_penalty = 1 + (angle_diff / 180) * 0.5
    return base_dist * wind_penalty

def neighbors(pos, grid_size):
    x, y = pos
    return [(x + dx, y + dy) for dx, dy in
            [(-1,0), (1,0), (0,-1), (0,1)]
            if 0 <= x+dx < grid_size and 0 <= y+dy < grid_size]

def is_collision(pos, obstacles):
    return pos in obstacles

def reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    return path[::-1]

# ======================
# 알고리즘 함수들
# ======================

def a_star_search(start, goal, obstacle_positions, grid_size, wind_direction=0):
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    closed_set = set()

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(came_from, current)

        if current in closed_set:
            continue
        closed_set.add(current)

        for neighbor in neighbors(current, grid_size):
            if is_collision(neighbor, obstacle_positions):
                continue

            tentative_g = g_score[current] + 1
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + adjusted_distance(neighbor, goal, wind_direction)
                heapq.heappush(open_set, (f_score, neighbor))

    return None

def dijkstra_search(start, goal, obstacle_positions, grid_size):
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    cost = {start: 0}
    visited = set()

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(came_from, current)

        if current in visited:
            continue
        visited.add(current)

        for neighbor in neighbors(current, grid_size):
            if is_collision(neighbor, obstacle_positions):
                continue

            new_cost = cost[current] + 1
            if neighbor not in cost or new_cost < cost[neighbor]:
                cost[neighbor] = new_cost
                came_from[neighbor] = current
                heapq.heappush(open_set, (new_cost, neighbor))

    return None

# ======================
# 클러스터링 (기존 대비 호환용; 핫스팟 미사용 시 사용)
# ======================

def cluster_trash(trash_positions, max_cluster_dist=8):
    clusters = []
    trash_set = set(trash_positions)

    while trash_set:
        base = trash_set.pop()
        cluster = [base]
        nbs = [t for t in list(trash_set) if distance(base, t) <= max_cluster_dist]
        for t in nbs:
            cluster.append(t)
            trash_set.remove(t)
        clusters.append(cluster)

    return clusters

# ======================
# 🔴 핫스팟 유틸
# ======================

def build_hotspot_groups(trash_positions, hotspots, radius=6):
    """
    각 핫스팟 반경 'radius' 안의 쓰레기를 그룹화.
    여러 반경이 겹치면 가장 가까운 핫스팟으로 귀속.
    """
    groups = {h: [] for h in hotspots}
    for t in trash_positions:
        nearest = min(hotspots, key=lambda h: distance(t, h))
        if distance(t, nearest) <= radius:
            groups[nearest].append(t)
    # 빈 그룹은 남겨도 되지만, 이후 로직에서 자동으로 걸러짐
    return groups

# ======================
# Fusion Algorithm (핫스팟 우선 + 동적 최근접)
# ======================

def fusion_algorithm(start, trash_positions, obstacle_positions, env=None,
                     hotspots=None, hotspot_radius=6):
    grid_size = 50
    path = []
    current_pos = start

    # set로 바꿔 조회 비용 ↓
    trash_set = set(trash_positions)
    obstacle_set = set(obstacle_positions)

    # 풍향(있으면 A* 휴리스틱에 반영)
    wind_direction = 0
    if env is not None:
        wd = env.get('풍향(deg)') if hasattr(env, 'get') else env['풍향(deg)']
        if not pd.isna(wd):
            wind_direction = wd

    # === (A) 핫스팟 우선 모드 ===
    if hotspots:
        groups = build_hotspot_groups(list(trash_set), hotspots, radius=hotspot_radius)
        visited_hotspots = set()

        # 핫스팟 선택: 남은 개수 ↑, 거리 ↓ (가중합)
        alpha, beta = 1.0, 0.15
        max_iterations = 2000
        iteration = 0

        collected = set()

        while iteration < max_iterations and len(collected) < len(trash_set):
            iteration += 1

            # 후보 핫스팟: 아직 남은 쓰레기가 있는 곳
            candidate_hotspots = []
            for h, pts in groups.items():
                remaining_pts = [p for p in pts if p not in collected]
                if remaining_pts:
                    score = alpha * len(remaining_pts) - beta * distance(current_pos, h)
                    candidate_hotspots.append((h, remaining_pts, score))

            if not candidate_hotspots:
                break

            # 점수 최대인 핫스팟 선택
            target_h, remaining_pts, _ = max(candidate_hotspots, key=lambda x: x[2])
            visited_hotspots.add(target_h)

            # 🔁 동적 최근접(바람 휴리스틱 반영)으로 한 개씩 선택·수거
            remaining = set(remaining_pts)
            while remaining:
                # 다음 타깃: adjusted_distance 최소
                target = min(remaining, key=lambda t: adjusted_distance(current_pos, t, wind_direction))

                # 경로: A* → 폴백 다익스트라
                route = a_star_search(current_pos, target, obstacle_set, grid_size, wind_direction)
                if route is None:
                    route = dijkstra_search(current_pos, target, obstacle_set, grid_size)
                if route is None:
                    # 막히면 해당 타깃 포기 후 다음 타깃
                    remaining.remove(target)
                    continue

                # 경로 따라 이동(충돌 시 1-스텝 로컬 우회)
                for step in route[1:]:
                    if is_collision(step, obstacle_set):
                        alt_steps = [n for n in neighbors(current_pos, grid_size) if not is_collision(n, obstacle_set)]
                        if alt_steps:
                            step = alt_steps[0]
                        else:
                            break
                    path.append(step)
                    current_pos = step
                    # 수거 처리
                    if current_pos in trash_set:
                        collected.add(current_pos)
                        if current_pos in remaining:
                            remaining.remove(current_pos)

                # 목표점에 도달 못했으면 그래도 제거 시도(안전장치)
                if target in remaining and current_pos == target:
                    remaining.remove(target)

        # 핫스팟 반경 외 잔여 쓰레기가 있다면(선택) 기존 클러스터 모드로 마저 수거
        leftovers = [t for t in trash_set if t not in collected]
        if leftovers:
            clusters = cluster_trash(leftovers)
            visited_clusters = set()
            iteration = 0
            while iteration < 1000 and len(collected) < len(trash_set):
                iteration += 1
                candidate_clusters = [c for c in clusters
                                      if tuple(c[0]) not in visited_clusters and
                                      min(distance(current_pos, t) for t in c) < 15]
                if not candidate_clusters:
                    break
                target_cluster = min(candidate_clusters, key=lambda c: distance(current_pos, c[0]))
                visited_clusters.add(tuple(target_cluster[0]))

                for target in sorted(target_cluster, key=lambda t: distance(current_pos, t)):
                    if target in collected:
                        continue
                    route = a_star_search(current_pos, target, obstacle_set, grid_size, wind_direction)
                    if route is None:
                        route = dijkstra_search(current_pos, target, obstacle_set, grid_size)
                    if route is None:
                        continue

                    for step in route[1:]:
                        if is_collision(step, obstacle_set):
                            alt_steps = [n for n in neighbors(current_pos, grid_size) if not is_collision(n, obstacle_set)]
                            if alt_steps:
                                step = alt_steps[0]
                            else:
                                break
                        path.append(step)
                        current_pos = step
                        if current_pos in trash_set:
                            collected.add(current_pos)

        return path

    # === (B) 핫스팟 미설정 시: 기존 클러스터 우선 모드 ===
    collected = set()
    clusters = cluster_trash(list(trash_set))
    visited_clusters = set()

    max_iterations = 1000
    iteration = 0
    while iteration < max_iterations and len(collected) < len(trash_set):
        iteration += 1

        candidate_clusters = [c for c in clusters if tuple(c[0]) not in visited_clusters and
                              min(distance(current_pos, t) for t in c) < 15]

        if not candidate_clusters:
            break

        target_cluster = min(candidate_clusters, key=lambda c: distance(current_pos, c[0]))
        visited_clusters.add(tuple(target_cluster[0]))

        for target in sorted(target_cluster, key=lambda t: distance(current_pos, t)):
            if target in collected:
                continue

            route = a_star_search(current_pos, target, obstacle_set, grid_size, wind_direction)
            if route is None:
                route = dijkstra_search(current_pos, target, obstacle_set, grid_size)
            if route is None:
                continue

            for step in route[1:]:
                if is_collision(step, obstacle_set):
                    alt_steps = [n for n in neighbors(current_pos, grid_size) if not is_collision(n, obstacle_set)]
                    if alt_steps:
                        step = alt_steps[0]
                    else:
                        break
                path.append(step)
                current_pos = step
                if current_pos in trash_set:
                    collected.add(current_pos)

    return path

# ================================================
# 알고리즘 성능 평가 함수
# ================================================
def evaluate_algorithm(algorithm, start, trash_positions, obstacle_positions, env=None):
    start_time = time.time()
    results = algorithm(start, trash_positions.copy(), obstacle_positions, env)
    end_time = time.time()

    collection_rate = len(set(results) & set(trash_positions)) / len(trash_positions) if trash_positions else 0
    collision_count = len([pos for pos in results if pos in set(obstacle_positions)])
    search_distance = len(results)
    elapsed_time = end_time - start_time

    return {
        "collection_rate": collection_rate,
        "collision_count": collision_count,
        "search_distance": search_distance,
        "elapsed_time": elapsed_time
    }

# ================================================
# 결과 출력 함수
# ================================================
def print_results(results):
    for name, metrics in results.items():
        print(f"{name} Algorithm:")
        print(f"  수집률: {metrics['collection_rate']:.4f}")
        print(f"  충돌 횟수: {metrics['collision_count']}")
        print(f"  탐색 거리: {metrics['search_distance']}")
        print(f"  실행 시간: {metrics['elapsed_time']:.4f} seconds")
        print()

# ================================================
# 결과 저장 함수
# ================================================
save_folder = "algo_test_results"
os.makedirs(save_folder, exist_ok=True)

algorithm_names = ["❤️Fusion(Hotspot)"]

def save_partial_results(all_results, save_count):
    rows = []
    for i, result in enumerate(all_results):
        for algo in algorithm_names:
            row = {
                "Index": i,
                "Algorithm": algo,
                "CollectionRate": result[algo]["collection_rate"],
                "CollisionCount": result[algo]["collision_count"],
                "SearchDistance": result[algo]["search_distance"],
                "ElapsedTime": result[algo]["elapsed_time"]
            }
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(f"{save_folder}/algorithm_test_results_{save_count}.csv",
              index=False, encoding='utf-8-sig')

# ================================================
# 메인 실행
# ================================================
all_results = []
batch_size = 500
save_count = 1
total = len(data)

for index, row in data.iterrows():
    trash_positions, obstacle_positions = generate_trash_obstacles_with_environment(50, row)
    start = (0, 0)

    # 🔴 evaluate_algorithm 시그니처를 유지하기 위해 람다로 hotspots 주입
    fusion_results = evaluate_algorithm(
        lambda s, t, o, env=None: fusion_algorithm(
            s, t, o, env=env, hotspots=HOTSPOTS, hotspot_radius=HOTSPOT_RADIUS
        ),
        start, trash_positions, obstacle_positions, env=row
    )

    results = {
        "❤️Fusion(Hotspot)": fusion_results,
    }

    all_results.append(results)

    print()
    print("================================================")
    print(f"Data Index {index+1}/{total}: ({(index+1)/total*100:.2f}%)")
    print()
    print_results(results)

    if (index + 1) % batch_size == 0 or (index + 1) == total:
        save_partial_results(all_results, save_count)
        print(f"Results saved: batch {save_count}")
        save_count += 1
        all_results = []

if all_results:
    save_partial_results(all_results, save_count)
    print("\n================================================")
    print(f"✅ TEST RESULT FILE SAVED: algorithm_test_results_{save_count}.csv")
    print("================================================")
    print()

# ================================================
# 평균 결과 계산
# ================================================
print("\n================================================")
print("✅ TEST RESULT AVERAGE")
file_list = glob.glob(f"{save_folder}/algorithm_test_results_*.csv")

dfs = []
for file in file_list:
    dfs.append(pd.read_csv(file))

full_df = pd.concat(dfs, ignore_index=True)

for algo in algorithm_names:
    algo_df = full_df[full_df["Algorithm"] == algo]
    print(f"\n=== {algo} ===")
    print(f"  수집률 평균: {algo_df['CollectionRate'].mean():.4f}")
    print(f"  충돌 횟수 평균: {algo_df['CollisionCount'].mean():.4f}")
    print(f"  탐색 거리 평균: {algo_df['SearchDistance'].mean():.4f}")
    print(f"  실행 시간 평균: {algo_df['ElapsedTime'].mean():.4f} seconds")

print()