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
# 🔴 핫스팟 설정 (격자 0~49 기준)
# ================================================
HOTSPOTS = [(8, 6), (12, 30), (20, 22), (33, 18), (40, 40)]  # 예시
HOTSPOT_RADIUS = 6

# ================================================
# 환경 기반 쓰레기 및 장애물 생성 함수 (원본 유지)
# ================================================
def generate_trash_obstacles_with_environment(grid_size, env_row):
    wind_speed = env_row['풍속(m/s)']; wind_direction = env_row['풍향(deg)']
    gust_speed = env_row['GUST풍속(m/s)']; max_wave_height = env_row['최대파고(m)']
    significant_wave_height = env_row['유의파고(m)']; mean_wave_height = env_row['평균파고(m)']
    wave_period = env_row['파주기(sec)']; wave_direction = env_row['파향(deg)']

    if pd.isna(wind_speed): wind_speed = 0
    if pd.isna(wind_direction): wind_direction = 0
    if pd.isna(gust_speed): gust_speed = 0
    if pd.isna(max_wave_height): max_wave_height = 0
    if pd.isna(significant_wave_height): significant_wave_height = 0
    if pd.isna(mean_wave_height): mean_wave_height = 0
    if pd.isna(wave_period): wave_period = 0
    if pd.isna(wave_direction): wave_direction = 0

    base_trash, base_obstacles = 50, 10
    trash_count = min(base_trash + int(wind_speed*5) + int(significant_wave_height*10), 300)
    obstacle_count = min(base_obstacles + int(gust_speed*2) + int(max_wave_height*5), 50)

    trash_positions = []
    for _ in range(trash_count):
        bx = random.randint(0, 49); by = random.randint(0, 49)
        off = random.randint(0, 5)
        nx = max(0, min(49, bx + int(np.cos(np.radians(wind_direction))*off)))
        ny = max(0, min(49, by + int(np.sin(np.radians(wind_direction))*off)))
        trash_positions.append((nx, ny))

    obstacle_positions = []
    for _ in range(obstacle_count):
        bx = random.randint(0, 49); by = random.randint(0, 49)
        off = random.randint(0, 3)
        nx = max(0, min(49, bx + int(np.cos(np.radians(wave_direction))*off)))
        ny = max(0, min(49, by + int(np.sin(np.radians(wave_direction))*off)))
        obstacle_positions.append((nx, ny))

    return trash_positions, obstacle_positions

# ================================================
# 공용 유틸
# ================================================
def distance(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def adjusted_distance(a, b, wind_direction):
    dx, dy = b[0]-a[0], b[1]-a[1]
    base = math.sqrt(dx*dx + dy*dy)
    if base == 0: return 0.0
    ang = (math.degrees(math.atan2(dy, dx)) % 360)
    diff = abs(wind_direction - ang); diff = min(diff, 360 - diff)
    penalty = 1 + (diff/180.0)*0.5  # 역풍일수록 ↑ (최대 +50%)
    return base * penalty

def build_hotspot_groups(trash_positions, hotspots, radius=6):
    groups = {h: [] for h in hotspots}
    for t in trash_positions:
        h = min(hotspots, key=lambda x: distance(t, x))
        if distance(t, h) <= radius:
            groups[h].append(t)
    return groups

# ================================================
# Hybrid(Hotspot) — Fusion + Predictive + Score
# ================================================
def hybrid_algorithm(
    start,
    trash_positions,
    obstacle_positions,
    env=None,
    hotspots=None,
    hotspot_radius=6,
    alpha=1.0, beta=0.15,          # 핫스팟 선택 가중치
    lookahead=2,                    # Predictive 룩어헤드
    dir_dot_threshold=0.7,          # 방향 점수 코사인 임계(≈±45°)
    candidate_dist_filter=30,       # 후보 거리 필터
    top_k_candidates=12             # 후보 상한(K) — 연산량 제어
):
    grid_size = 50
    current = start
    path = [start]
    trash_set = set(trash_positions)
    obstacle_set = set(obstacle_positions)

    # 풍향(휴리스틱 반영)
    wind_dir = 0
    if env is not None:
        wd = env.get('풍향(deg)') if hasattr(env, 'get') else env['풍향(deg)']
        if not pd.isna(wd): wind_dir = wd

    # 8-이동 이웃
    directions8 = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]

    # --- A* (풍향 휴리스틱) + 양방향 캐시 ---
    astar_cache = {}
    def a_star_cached(s, g):
        if s == g: return [s]
        key = (s, g)
        if key in astar_cache: return astar_cache[key]
        rk = (g, s)
        if rk in astar_cache and astar_cache[rk] is not None:
            return list(reversed(astar_cache[rk]))

        open_set = []
        heapq.heappush(open_set, (adjusted_distance(s, g, wind_dir), 0, s, [s]))
        best_g = {s: 0}
        closed = set()

        while open_set:
            f, g_cost, u, u_path = heapq.heappop(open_set)
            if u == g:
                astar_cache[key] = u_path
                return u_path
            if u in closed: continue
            closed.add(u)

            for dx, dy in directions8:
                nx, ny = u[0]+dx, u[1]+dy
                if not (0 <= nx < grid_size and 0 <= ny < grid_size): continue
                v = (nx, ny)
                if v in obstacle_set: continue
                ng = g_cost + 1
                if ng < best_g.get(v, 1e18):
                    best_g[v] = ng
                    nf = ng + adjusted_distance(v, g, wind_dir)
                    heapq.heappush(open_set, (nf, ng, v, u_path+[v]))

        astar_cache[key] = None
        return None

    # --- 다익스트라(폴백) ---
    def dijkstra(s, g):
        if s == g: return [s]
        pq = [(0, s)]
        came = {}
        best = {s: 0}
        while pq:
            c, u = heapq.heappop(pq)
            if u == g:
                # reconstruct
                path2 = [u]
                while u in came:
                    u = came[u]; path2.append(u)
                return list(reversed(path2))
            for dx, dy in directions8:
                v = (u[0]+dx, u[1]+dy)
                if not (0 <= v[0] < grid_size and 0 <= v[1] < grid_size): continue
                if v in obstacle_set: continue
                nc = c + 1
                if nc < best.get(v, 1e18):
                    best[v] = nc
                    came[v] = u
                    heapq.heappush(pq, (nc, v))
        return None

    # --- 방향 점수로 후보 축소 ---
    def directional_candidates(points, center):
        # 각 방향에 대해: 앞쪽에 위치하면서 가까운 점 많으면 점수↑
        scores = []
        for dx, dy in directions8:
            dir_vec = np.array([dx, dy]); norm = np.linalg.norm(dir_vec)
            if norm == 0:
                scores.append(0.0); continue
            sc = 0.0
            for tx, ty in points:
                vec = np.array([tx-center[0], ty-center[1]])
                dist = np.linalg.norm(vec)
                if dist == 0: continue
                dot = float(np.dot(dir_vec, vec)/(norm*dist))
                if dot >= dir_dot_threshold:
                    sc += 1.0/(dist+1e-5)
            scores.append(sc)
        best_dir = directions8[int(np.argmax(scores))]

        # 그 방향 "앞쪽" + 거리 필터
        cand = []
        for t in points:
            vx, vy = t[0]-center[0], t[1]-center[1]
            if best_dir[0]*vx + best_dir[1]*vy > 0 and distance(center, t) <= candidate_dist_filter:
                cand.append(t)
        if not cand:
            # 필터가 너무 엄격하면 완화
            cand = sorted(points, key=lambda p: distance(center, p))[:top_k_candidates]
        else:
            cand = sorted(cand, key=lambda p: distance(center, p))[:top_k_candidates]
        return cand

    # --- 목표 비용 평가: A*경로길이 + 룩어헤드 근사 ---
    def evaluate_target_cost(cur, target, remaining):
        route = a_star_cached(cur, target)
        if route is None:
            route = dijkstra(cur, target)
            if route is None:
                return float('inf'), None
        cost = len(route)

        # 룩어헤드: 이후 lookahead-1개를 adjusted_distance 기준 NN로 근사
        sim_pos = target
        rem = list(remaining - {target})
        for _ in range(max(0, lookahead-1)):
            if not rem: break
            nxt = min(rem, key=lambda p: adjusted_distance(sim_pos, p, wind_dir))
            cost += adjusted_distance(sim_pos, nxt, wind_dir)
            sim_pos = nxt
            rem.remove(nxt)
        return cost, route

    # --- 경로 따라가며 로컬 우회 ---
    def follow_route(route, cur, collected):
        nonlocal path
        for step in route[1:]:
            if step in obstacle_set:
                # 1-스텝 로컬 우회
                adj = [(cur[0]+dx, cur[1]+dy) for dx, dy in directions8]
                adj = [a for a in adj if 0 <= a[0] < grid_size and 0 <= a[1] < grid_size and a not in obstacle_set]
                if not adj: return cur
                step = adj[0]
            path.append(step)
            cur = step
            if cur in trash_set: collected.add(cur)
        return cur

    # ============ 메인 루프 ============
    collected = set()

    if hotspots:
        groups = build_hotspot_groups(list(trash_set), hotspots, radius=hotspot_radius)

        while True:
            # 1) 핫스팟 선택(α·개수 − β·거리)
            cands = []
            for h, pts in groups.items():
                remain = [p for p in pts if p not in collected]
                if remain:
                    score = alpha*len(remain) - beta*distance(current, h)
                    cands.append((h, remain, score))
            if not cands: break
            target_h, remain_pts, _ = max(cands, key=lambda x: x[2])

            # 2) 핫스팟 내부: 방향 점수로 후보 축소 → (A*+룩어헤드) 총비용 최소 선택
            remain_set = set(remain_pts)
            while remain_set:
                candidates = directional_candidates(list(remain_set), current)
                best = (float('inf'), None, None)  # (cost, target, route)
                for t in candidates:
                    cost, route = evaluate_target_cost(current, t, remain_set)
                    if cost < best[0]:
                        best = (cost, t, route)
                if best[2] is None:
                    # 모두 막혔다면 핫스팟 내 종료
                    break
                # 3) 경로 따라 이동(로컬 우회 포함)
                current = follow_route(best[2], current, collected)
                if best[1] in remain_set: remain_set.remove(best[1])

        # 핫스팟 반경 밖 잔여물은 동일 방식으로 마무리
        leftovers = list(trash_set - collected)
        while leftovers:
            candidates = directional_candidates(leftovers, current)
            best = (float('inf'), None, None)
            rem_set = set(leftovers)
            for t in candidates:
                cost, route = evaluate_target_cost(current, t, rem_set)
                if cost < best[0]:
                    best = (cost, t, route)
            if best[2] is None: break
            current = follow_route(best[2], current, collected)
            if best[1] in leftovers: leftovers.remove(best[1])

        return path[1:]  # 시작칸 제외하고 반환

    # (폴백) 핫스팟 미설정 시: 후보 축소 + (A*+룩어헤드)로 수거
    remain = set(trash_set)
    while remain:
        candidates = directional_candidates(list(remain), current)
        best = (float('inf'), None, None)
        for t in candidates:
            cost, route = evaluate_target_cost(current, t, remain)
            if cost < best[0]:
                best = (cost, t, route)
        if best[2] is None: break
        current = follow_route(best[2], current, collected)
        remain.discard(best[1])

    return path[1:]

# ================================================
# 알고리즘 성능 평가/출력/저장 (원본 포맷 유지)
# ================================================
def evaluate_algorithm(algorithm, start, trash_positions, obstacle_positions, env=None):
    t0 = time.time()
    results = algorithm(start, trash_positions.copy(), obstacle_positions, env)
    t1 = time.time()
    collection_rate = len(set(results) & set(trash_positions))/len(trash_positions) if trash_positions else 0
    collision_count = len([p for p in results if p in set(obstacle_positions)])
    search_distance = len(results)
    elapsed_time = t1 - t0
    return {"collection_rate": collection_rate,
            "collision_count": collision_count,
            "search_distance": search_distance,
            "elapsed_time": elapsed_time}

def print_results(results):
    for name, m in results.items():
        print(f"{name} Algorithm:")
        print(f"  수집률: {m['collection_rate']:.4f}")
        print(f"  충돌 횟수: {m['collision_count']}")
        print(f"  탐색 거리: {m['search_distance']}")
        print(f"  실행 시간: {m['elapsed_time']:.4f} seconds")
        print()

save_folder = "algo_test_results"
os.makedirs(save_folder, exist_ok=True)
algorithm_names = ["🧪Hybrid(Hotspot)"]

def save_partial_results(all_results, save_count):
    rows = []
    for i, result in enumerate(all_results):
        for algo in algorithm_names:
            rows.append({
                "Index": i,
                "Algorithm": algo,
                "CollectionRate": result[algo]["collection_rate"],
                "CollisionCount": result[algo]["collision_count"],
                "SearchDistance": result[algo]["search_distance"],
                "ElapsedTime": result[algo]["elapsed_time"],
            })
    pd.DataFrame(rows).to_csv(f"{save_folder}/algorithm_test_results_{save_count}.csv",
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

    hybrid_results = evaluate_algorithm(
        lambda s, t, o, env=None: hybrid_algorithm(
            s, t, o, env=env,
            hotspots=HOTSPOTS, hotspot_radius=HOTSPOT_RADIUS,
            alpha=1.0, beta=0.15,
            lookahead=2,
            dir_dot_threshold=0.7,
            candidate_dist_filter=30,
            top_k_candidates=12
        ),
        start, trash_positions, obstacle_positions, env=row
    )

    results = {"🧪Hybrid(Hotspot)": hybrid_results}
    all_results.append(results)

    print("\n================================================")
    print(f"Data Index {index+1}/{total}: ({(index+1)/total*100:.2f}%)\n")
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
    print("================================================\n")

# 평균 결과
print("\n================================================")
print("✅ TEST RESULT AVERAGE")
file_list = glob.glob(f"{save_folder}/algorithm_test_results_*.csv")
full_df = pd.concat([pd.read_csv(f) for f in file_list], ignore_index=True)
for algo in algorithm_names:
    a = full_df[full_df["Algorithm"] == algo]
    print(f"\n=== {algo} ===")
    print(f"  수집률 평균: {a['CollectionRate'].mean():.4f}")
    print(f"  충돌 횟수 평균: {a['CollisionCount'].mean():.4f}")
    print(f"  탐색 거리 평균: {a['SearchDistance'].mean():.4f}")
    print(f"  실행 시간 평균: {a['ElapsedTime'].mean():.4f} seconds")
print()