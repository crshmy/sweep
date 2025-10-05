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
# 🔴 핫스팟 설정 (격자 0~49 기준, 5~10개 권장)
#    - 미설정(None 또는 빈 리스트)이면 기존 Score 로직으로 동작
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
# Score (핫스팟 우선)
#  - 핫스팟 간: 남은개수 우선 + 거리 페널티(score=alpha*cnt - beta*dist)
#  - 핫스팟 내: 기존 '방향 점수' 방식으로 다음 타깃 선정(A*로 경로)
# ================================================
def score_algorithm(start, trash_positions, obstacle_positions, env=None,
                    hotspots=None, hotspot_radius=6, dir_dot_threshold=0.7):
    grid_size = 50
    directions = [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]
    current_pos = start
    path = []
    trash_positions_set = set(trash_positions)
    obstacle_set = set(obstacle_positions)

    # 휴리스틱/경로 함수들
    def heuristic(a, b):
        # 8방향 이동에 맨해튼은 비최적일 수 있으나 빠르고 일관성 있게 유도
        return abs(b[0] - a[0]) + abs(b[1] - a[1])

    def reconstruct_path(came_from, current):
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        return total_path[::-1]

    def a_star(start_, goal_, obstacles):
        open_set = []
        heapq.heappush(open_set, (heuristic(start_, goal_), 0, start_))
        came_from = {}
        g_score = {start_: 0}
        closed_set = set()

        while open_set:
            _, cost, current = heapq.heappop(open_set)
            if current == goal_:
                return reconstruct_path(came_from, current)
            if current in closed_set:
                continue
            closed_set.add(current)

            for dx, dy in directions:
                nx, ny = current[0] + dx, current[1] + dy
                neighbor = (nx, ny)
                if 0 <= nx < grid_size and 0 <= ny < grid_size and neighbor not in obstacles:
                    tentative_g = cost + 1
                    if neighbor not in g_score or tentative_g < g_score[neighbor]:
                        g_score[neighbor] = tentative_g
                        f_score = tentative_g + heuristic(neighbor, goal_)
                        heapq.heappush(open_set, (f_score, tentative_g, neighbor))
                        came_from[neighbor] = current
        return None

    # 🔁 핫스팟 우선 모드
    if hotspots:
        groups = build_hotspot_groups(list(trash_positions_set), hotspots, radius=hotspot_radius)
        collected = set()
        alpha, beta = 1.0, 0.15  # 핫스팟 선택: 남은개수↑, 거리↓ 균형

        # 핫스팟이 모두 비면 종료
        while True:
            # 후보 핫스팟 수집
            candidates = []
            for h, pts in groups.items():
                remaining = [p for p in pts if p not in collected]
                if remaining:
                    score = alpha * len(remaining) - beta * distance(current_pos, h)
                    candidates.append((h, remaining, score))
            if not candidates:
                break

            # 점수 최대 핫스팟 선택
            target_h, remaining_pts, _ = max(candidates, key=lambda x: x[2])

            # === 핫스팟 내 루프: 기존 Score의 "방향 점수"를 그대로 적용하되
            #     후보 풀을 "해당 핫스팟의 남은 쓰레기"로 제한 ===
            remaining_set = set(remaining_pts)

            while remaining_set:
                # 1) 8방향마다 "그 방향 앞쪽에 얼마나/얼마나 가까이 많이 있나" 점수 계산
                scores = []
                for dx, dy in directions:
                    score_dir = 0.0
                    dir_vec = np.array([dx, dy])
                    dir_norm = np.linalg.norm(dir_vec)
                    if dir_norm == 0:
                        scores.append(0.0)
                        continue
                    for tx, ty in remaining_set:
                        vec = np.array([tx - current_pos[0], ty - current_pos[1]])
                        dist = np.linalg.norm(vec)
                        if dist == 0:
                            continue
                        dot = np.dot(dir_vec, vec) / (dir_norm * dist)
                        if dot >= dir_dot_threshold:
                            score_dir += 1.0 / (dist + 1e-5)
                    scores.append(score_dir)

                best_dir = directions[int(np.argmax(scores))]

                # 2) 해당 방향 "앞쪽"에 있는 쓰레기들만 후보
                candidates_local = []
                for tx, ty in remaining_set:
                    vx, vy = tx - current_pos[0], ty - current_pos[1]
                    dot_lin = best_dir[0]*vx + best_dir[1]*vy
                    if dot_lin > 0:
                        candidates_local.append((tx, ty))

                # 비면 가장 가까운 것으로 폴백
                if not candidates_local:
                    candidates_local = list(remaining_set)

                # 3) 후보 중 "현재와의 거리"로 가장 가까운 점 선택
                next_trash = min(candidates_local, key=lambda p: heuristic(current_pos, p))

                # 4) A*로 경로 찾기(실패 시 해당 점은 스킵, 다른 점 시도)
                route = a_star(current_pos, next_trash, obstacle_set)
                if route:
                    path.extend(route[1:])
                    current_pos = next_trash
                    remaining_set.remove(next_trash)
                    collected.add(next_trash)
                else:
                    # 막히면 해당 후보 제거 후 계속
                    remaining_set.remove(next_trash)

        # 핫스팟 반경 밖 잔여물(있다면) → 기존 Score 로직으로 마무리
        trash_positions_set = set(trash_positions_set) - set(collected)

    # 🔁 (폴백) 기존 Score 로직
    while trash_positions_set:
        # 1) 방향 점수
        scores = []
        for dx, dy in directions:
            score = 0.0
            dir_vec = np.array([dx, dy])
            dir_norm = np.linalg.norm(dir_vec)
            if dir_norm == 0:
                scores.append(0.0)
                continue
            for tx, ty in trash_positions_set:
                vec = np.array([tx - current_pos[0], ty - current_pos[1]])
                dist = np.linalg.norm(vec)
                if dist == 0:
                    continue
                dot = np.dot(dir_vec, vec) / (dir_norm * dist)
                if dot >= dir_dot_threshold:
                    score += 1.0 / (dist + 1e-5)
            scores.append(score)

        best_dir = directions[int(np.argmax(scores))]

        # 2) 그 방향 앞쪽 후보
        candidates = []
        for tx, ty in trash_positions_set:
            vx, vy = tx - current_pos[0], ty - current_pos[1]
            dot = best_dir[0]*vx + best_dir[1]*vy
            if dot > 0:
                candidates.append((tx, ty))
        if not candidates:
            candidates = list(trash_positions_set)

        # 3) 가장 가까운 후보
        next_trash = min(candidates, key=lambda p: heuristic(current_pos, p))

        # 4) 경로 이동(A*)
        route = a_star(current_pos, next_trash, obstacle_set)
        if route:
            path.extend(route[1:])
            current_pos = next_trash
        else:
            # 경로가 막히면 그래도 목표로 위치 갱신(강행) 후 다음으로 진행
            current_pos = next_trash

        trash_positions_set.remove(next_trash)

    return path

# ================================================
# 알고리즘 성능 평가 함수
# ================================================
def evaluate_algorithm(algorithm, start, trash_positions, obstacle_positions, env=None):
    start_time = time.time()
    results = algorithm(start, trash_positions.copy(), obstacle_positions, env)
    end_time = time.time()

    collection_rate = len(set(results) & set(trash_positions)) / len(trash_positions) if trash_positions else 0
    collision_count = len([pos for pos in results if pos in obstacle_positions])
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

algorithm_names = ["💙Score(Hotspot)"]

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

    # evaluate_algorithm 시그니처 유지를 위해 람다로 핫스팟 파라미터 주입
    Score_results = evaluate_algorithm(
        lambda s, t, o, env=None: score_algorithm(
            s, t, o, env=env, hotspots=HOTSPOTS, hotspot_radius=HOTSPOT_RADIUS
        ),
        start, trash_positions, obstacle_positions, env=row
    )

    results = {
        "💙Score(Hotspot)": Score_results,
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
    print(f"✅ TEST RESULT FILE SAVED: Score_results_{save_count}.csv")
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