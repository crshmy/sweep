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
# 🔴 핫스팟 설정 (필수: 격자 0~49 기준, 5~10개 권장)
# ================================================
HOTSPOTS = [(8, 6), (12, 30), (20, 22), (33, 18), (40, 40)]  # 예시
HOTSPOT_RADIUS = 6  # 이 반경 안의 쓰레기를 해당 핫스팟 소속으로 간주

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
# 🔴 핫스팟 유틸
# ================================================
def distance(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

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
    return groups

# ================================================
# Predictive (핫스팟 우선 + A* 캐싱 + 룩어헤드)
# ================================================
def predictive_algorithm(start, trash_positions, obstacle_positions, env=None,
                         lookahead=2, hotspots=None, hotspot_radius=6):
    import numpy as np
    from heapq import heappush, heappop

    grid_size = 50
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    trash_positions = trash_positions.copy()
    obstacle_set = set(obstacle_positions)
    path = [start]
    current_position = start

    # A* 결과 캐싱 (양방향)
    astar_cache = {}

    # ✅ 유클리드 거리 휴리스틱
    def heuristic(a, b):
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

    # ✅ A* (양방향 캐시)
    def a_star(s, g):
        if (s, g) in astar_cache:
            return astar_cache[(s, g)]
        if (g, s) in astar_cache:
            return astar_cache[(g, s)][::-1]

        open_set = []
        heappush(open_set, (heuristic(s, g), 0, s, [s]))
        visited = {}

        while open_set:
            est_total, cost_so_far, cur, cur_path = heappop(open_set)
            if cur == g:
                astar_cache[(s, g)] = cur_path
                return cur_path
            if cur in visited and visited[cur] <= cost_so_far:
                continue
            visited[cur] = cost_so_far

            for dx, dy in directions:
                nb = (cur[0]+dx, cur[1]+dy)
                if (0 <= nb[0] < grid_size and 0 <= nb[1] < grid_size and nb not in obstacle_set):
                    new_cost = cost_so_far + 1
                    heappush(open_set, (new_cost + heuristic(nb, g), new_cost, nb, cur_path+[nb]))

        astar_cache[(s, g)] = None
        return None

    # === (A) 핫스팟 우선 모드 ===
    if hotspots:
        groups = build_hotspot_groups(trash_positions, hotspots, radius=hotspot_radius)
        collected = set()

        # 핫스팟 선택 스코어: 남은개수 우선(alpha), 거리 페널티(beta)
        alpha, beta = 1.0, 0.15
        max_iterations = 2000
        iteration = 0

        while iteration < max_iterations and len(collected) < len(trash_positions):
            iteration += 1

            # 아직 남은 쓰레기가 있는 핫스팟 후보
            candidates = []
            for h, pts in groups.items():
                remaining = [p for p in pts if p not in collected]
                if remaining:
                    score = alpha * len(remaining) - beta * distance(current_position, h)
                    candidates.append((h, remaining, score))

            if not candidates:
                break

            # 점수 최대인 핫스팟 선택
            target_h, remaining_pts, _ = max(candidates, key=lambda x: x[2])

            # 🔁 핫스팟 내부: Predictive 방식(룩어헤드)으로 동적 선택
            remaining_set = set(remaining_pts)

            while remaining_set:
                # 필터: 너무 먼 점 제외(탐색 폭 제한)
                filtered = [t for t in remaining_set if heuristic(current_position, t) <= 30]
                if not filtered:
                    # 필터에 걸리는 게 없으면 남은 것 중 아무거나(가장 가까운) 사용
                    filtered = [min(remaining_set, key=lambda t: heuristic(current_position, t))]

                best_target = None
                min_cost = float('inf')
                best_route = None

                for target in filtered:
                    route = a_star(current_position, target)
                    if not route:
                        continue
                    total_cost = len(route)
                    sim_pos = target
                    visited_locals = {target}

                    # 룩어헤드: 남은 점들에 대한 근사 비용 더하기(휴리스틱 기반)
                    for _ in range(lookahead - 1):
                        rest = [t for t in remaining_set if t not in visited_locals]
                        if not rest:
                            break
                        nxt = min(rest, key=lambda t: heuristic(sim_pos, t))
                        total_cost += heuristic(sim_pos, nxt)
                        sim_pos = nxt
                        visited_locals.add(nxt)

                    if total_cost < min_cost:
                        min_cost = total_cost
                        best_target = target
                        best_route = route

                if not best_route:
                    # 모두 막혔다면 이 핫스팟 내 수거 종료
                    break

                # 경로 따라 이동
                path.extend(best_route[1:])
                current_position = best_target
                if best_target in remaining_set:
                    remaining_set.remove(best_target)
                collected.add(best_target)

        # 핫스팟 반경 밖 잔여 쓰레기(있다면): 원래 Predictive 로직으로 마무리
        leftovers = [t for t in trash_positions if t not in collected]
        while leftovers:
            best_target = None
            min_cost = float('inf')
            best_path = None

            filtered_trash = [t for t in leftovers if heuristic(current_position, t) <= 30]
            if not filtered_trash:
                filtered_trash = [min(leftovers, key=lambda t: heuristic(current_position, t))]

            for target in filtered_trash:
                route = a_star(current_position, target)
                if not route:
                    continue

                total_cost = len(route)
                simulated_pos = target
                visited = {target}

                for _ in range(lookahead - 1):
                    remaining = [t for t in leftovers if t not in visited]
                    if not remaining:
                        break
                    next_target = min(remaining, key=lambda t: heuristic(simulated_pos, t))
                    total_cost += heuristic(simulated_pos, next_target)
                    simulated_pos = next_target
                    visited.add(next_target)

                if total_cost < min_cost:
                    min_cost = total_cost
                    best_target = target
                    best_path = route

            if not best_path:
                break

            path.extend(best_path[1:])
            current_position = best_target
            leftovers.remove(best_target)

        return path

    # === (B) 핫스팟 미설정: 기존 Predictive 그대로 ===
    while trash_positions:
        best_target = None
        min_cost = float('inf')
        best_path = None

        filtered_trash = [t for t in trash_positions if heuristic(current_position, t) <= 30]
        if not filtered_trash:
            filtered_trash = trash_positions  # 제한을 풀어 마지막까지 시도

        for target in filtered_trash:
            route = a_star(current_position, target)
            if not route:
                continue

            total_cost = len(route)
            simulated_pos = target
            visited = {target}

            for _ in range(lookahead - 1):
                remaining = [t for t in trash_positions if t not in visited]
                if not remaining:
                    break
                next_target = min(remaining, key=lambda t: heuristic(simulated_pos, t))
                total_cost += heuristic(simulated_pos, next_target)
                simulated_pos = next_target
                visited.add(next_target)

            if total_cost < min_cost:
                min_cost = total_cost
                best_target = target
                best_path = route

        if not best_path:
            break

        path.extend(best_path[1:])
        current_position = best_target
        trash_positions.remove(best_target)

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

algorithm_names = ["💚Predictive(Hotspot)"]

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
    df.to_csv(f"{save_folder}/algorithm_test_results_{save_count}.csv", index=False, encoding='utf-8-sig')

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

    # 🔴 evaluate_algorithm 시그니처 유지: 람다로 핫스팟 주입
    predictive_results = evaluate_algorithm(
        lambda s, t, o, env=None: predictive_algorithm(
            s, t, o, env=env, lookahead=2, hotspots=HOTSPOTS, hotspot_radius=HOTSPOT_RADIUS
        ),
        start, trash_positions, obstacle_positions, env=row
    )

    results = {
        "💚Predictive(Hotspot)": predictive_results,
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
    print(f"\n=== {algo} Algorithm ===")
    print(f"  수집률 평균: {algo_df['CollectionRate'].mean():.4f}")
    print(f"  충돌 횟수 평균: {algo_df['CollisionCount'].mean():.4f}")
    print(f"  탐색 거리 평균: {algo_df['SearchDistance'].mean():.4f}")
    print(f"  실행 시간 평균: {algo_df['ElapsedTime'].mean():.4f} seconds")

print()