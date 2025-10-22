# -*- coding: utf-8 -*-
import pandas as pd
import random
import numpy as np
import time
import heapq
import math
import os
import glob
import json
import signal
from contextlib import contextmanager

# ================================================
# 타임아웃 데코레이터
# ================================================
class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# ================================================
# 작업 디렉토리 / 결과 경로
# ================================================
BASE_DIR = r"C:\ClaudeFolder\marine_cleanup_nav\hotspot"
os.chdir(BASE_DIR)
SAVE_DIR = os.path.join(BASE_DIR, "algo_test_results")
os.makedirs(SAVE_DIR, exist_ok=True)

# Step3/4 산출물 경로
FINAL_DIR = os.path.join(BASE_DIR, "daily_results_final_251013")
HIST_DIR  = os.path.join(BASE_DIR, "daily_results_hotspot_251013")

GRID_SIZE = 50
TOP_K_HOTSPOTS = 15
MIN_REWARD_VAL  = None
USE_BIASED_TRASH = True

# ================================================
# 🔁 Hotspots Adapter: Step3/4 결과 → 격자(0~49) 매핑
# ================================================
def _clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))

def _to_grid(x, xmin, xmax, grid_size):
    if xmax == xmin:
        return 0
    g = round((x - xmin) / (xmax - xmin) * (grid_size - 1))
    return int(_clamp(g, 0, grid_size-1))

def load_hotspots_to_grid(final_dir=FINAL_DIR, hist_dir=HIST_DIR,
                          grid_size=GRID_SIZE, top_k=TOP_K_HOTSPOTS, min_reward=MIN_REWARD_VAL):
    with open(os.path.join(hist_dir, "history_summary.json"), "r", encoding="utf-8") as f:
        s = json.load(f)
    x_min, x_max = s["x_range"]; y_min, y_max = s["y_range"]

    with open(os.path.join(final_dir, "hotspots.json"), "r", encoding="utf-8") as f:
        hs = json.load(f)["hotspots"]

    if min_reward is not None:
        hs = [h for h in hs if float(h["value"]) >= float(min_reward)]
    hs = sorted(hs, key=lambda h: h["value"], reverse=True)
    if top_k is not None:
        hs = hs[:int(top_k)]

    seen = set()
    grid_points = []
    for h in hs:
        gx = _to_grid(h["x"], x_min, x_max, grid_size)
        gy = _to_grid(h["y"], y_min, y_max, grid_size)
        if (gx, gy) not in seen:
            seen.add((gx, gy))
            grid_points.append((gx, gy))
    return grid_points

def suggest_hotspot_radius(grid_size=GRID_SIZE, n_hotspots=10):
    base = max(4, int(0.12 * grid_size))
    if n_hotspots > 20: base = max(3, base-2)
    if n_hotspots > 35: base = max(2, base-2)
    return base

def generate_trash_obstacles_biased(grid_size, env_row, hotspots, base_func):
    trash, obstacles = base_func(grid_size, env_row)
    if not hotspots:
        return trash, obstacles
    extra = []
    for (hx, hy) in hotspots:
        m = random.randint(10, 20)
        for _ in range(m):
            dx = random.randint(-3, 3); dy = random.randint(-3, 3)
            x = _clamp(hx + dx, 0, grid_size-1)
            y = _clamp(hy + dy, 0, grid_size-1)
            extra.append((x, y))
    trash.extend(extra)
    return trash, obstacles

# ================================================
# 🔴 핫스팟 로드 (분석 산출물에서 자동)
# ================================================
try:
    HOTSPOTS = load_hotspots_to_grid()
    print(f"[INFO] Loaded HOTSPOTS ({len(HOTSPOTS)}): {HOTSPOTS}")
except Exception as e:
    print(f"[WARN] 핫스팟 자동 로드 실패: {e}")
    HOTSPOTS = [(8, 6), (12, 30), (20, 22), (33, 18), (40, 40)]
    print(f"[INFO] Fallback HOTSPOTS used: {HOTSPOTS}")

HOTSPOT_RADIUS = suggest_hotspot_radius(n_hotspots=len(HOTSPOTS))
print(f"[INFO] HOTSPOT_RADIUS (suggested): {HOTSPOT_RADIUS}")

# ================================================
# 📥 환경 데이터 로드 (10월 13일만)
# ================================================
def to_deg(val):
    if pd.isna(val): return np.nan
    s = str(val).strip()
    DIR2DEG = {
        '북': 0, '북북동': 22.5, '북동': 45, '동북동': 67.5,
        '동': 90, '동남동': 112.5, '남동': 135, '남남동': 157.5,
        '남': 180, '남남서': 202.5, '남서': 225, '서남서': 247.5,
        '서': 270, '서북서': 292.5, '북서': 315, '북북서': 337.5,
        '동풍': 90, '서풍': 270, '남풍': 180, '북풍': 0,
    }
    if s in DIR2DEG: return DIR2DEG[s]
    if '/' in s:
        parts = [p.strip() for p in s.split('/')]
        vals = [DIR2DEG.get(p, np.nan) for p in parts]
        if all([not np.isnan(v) for v in vals]): return float(np.mean(vals))
    try:
        return float(s)
    except:
        return np.nan

def load_env_data_oct13(base_dir):
    """10월 13일 데이터만 로드"""
    data_dir = os.path.join(base_dir, "data")
    
    # 2022, 2023, 2024년 10월 데이터 로드
    frames = []
    for year in [2022, 2023, 2024]:
        fname = f"{year}년 10월 대한해협 해양관측부이.csv"
        fpath = os.path.join(data_dir, fname)
        
        if not os.path.exists(fpath):
            print(f"[WARN] 파일 없음: {fpath}")
            continue
            
        try:
            df = pd.read_csv(fpath, encoding='cp949', sep='\t', skiprows=3)
        except Exception as e:
            print(f"[WARN] CSV 읽기 실패: {fpath} / {e}")
            continue

        # 컬럼 표준화
        colmap = {}
        if '유의파고(MOSE.HF)(m)' in df.columns:
            colmap['유의파고(MOSE.HF)(m)'] = '유의파고(m)'
        if 'GUST풍속(m/s)' not in df.columns:
            df['GUST풍속(m/s)'] = 0.0
        if '최대파고(m)' not in df.columns:
            df['최대파고(m)'] = 0.0
        if '평균파고(m)' not in df.columns:
            df['평균파고(m)'] = df['유의파고(m)'] if '유의파고(m)' in df.columns else 0.0
        if '파주기(sec)' not in df.columns:
            df['파주기(sec)'] = 0.0

        df = df.rename(columns=colmap)

        # 필요한 컬럼 강제 구성
        need_cols = ['관측시간', '풍속(m/s)', '풍향(deg)', '유의파고(m)', '파향(deg)',
                     'GUST풍속(m/s)', '최대파고(m)', '평균파고(m)', '파주기(sec)']
        for c in need_cols:
            if c not in df.columns:
                df[c] = 0.0

        # 타입/단위 보정
        df['관측시간'] = pd.to_datetime(df['관측시간'], errors='coerce')
        for c in ['풍속(m/s)', '유의파고(m)', 'GUST풍속(m/s)', '최대파고(m)', '평균파고(m)', '파주기(sec)']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df['풍향(deg)'] = df['풍향(deg)'].apply(to_deg)
        df['파향(deg)'] = df['파향(deg)'].apply(to_deg)

        # NA → 0
        df = df.fillna(0)
        
        # 10월 13일만 필터링
        df = df[df['관측시간'].dt.month == 10]
        df = df[df['관측시간'].dt.day == 13]
        
        frames.append(df[need_cols])
        print(f"[INFO] Loaded: {fpath}  (10월 13일 데이터: {len(df)}개)")
    
    if not frames:
        raise FileNotFoundError("10월 13일 데이터를 찾지 못했습니다.")
    
    out = pd.concat(frames, ignore_index=True).sort_values('관측시간').reset_index(drop=True)
    print(f"[INFO] 10월 13일 환경 데이터 통합 완료: rows={len(out)}")
    return out

# 실제 로드
data = load_env_data_oct13(BASE_DIR)

# ================================================
# 환경 기반 쓰레기/장애물 생성 (원본 로직 유지)
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
        bx = random.randint(0, GRID_SIZE-1); by = random.randint(0, GRID_SIZE-1)
        off = random.randint(0, 5)
        nx = max(0, min(GRID_SIZE-1, bx + int(np.cos(np.radians(wind_direction))*off)))
        ny = max(0, min(GRID_SIZE-1, by + int(np.sin(np.radians(wind_direction))*off)))
        trash_positions.append((nx, ny))

    obstacle_positions = []
    for _ in range(obstacle_count):
        bx = random.randint(0, GRID_SIZE-1); by = random.randint(0, GRID_SIZE-1)
        off = random.randint(0, 3)
        nx = max(0, min(GRID_SIZE-1, bx + int(np.cos(np.radians(wave_direction))*off)))
        ny = max(0, min(GRID_SIZE-1, by + int(np.sin(np.radians(wave_direction))*off)))
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
    penalty = 1 + (diff/180.0)*0.5
    return base * penalty

def build_hotspot_groups(trash_positions, hotspots, radius=6):
    groups = {h: [] for h in hotspots}
    for t in trash_positions:
        h = min(hotspots, key=lambda x: distance(t, x))
        if distance(t, h) <= radius:
            groups[h].append(t)
    return groups

# ================================================
# Hybrid(Hotspot) — 개선된 알고리즘 (무한루프 방지)
# ================================================
def hybrid_algorithm(
    start,
    trash_positions,
    obstacle_positions,
    env=None,
    hotspots=None,
    hotspot_radius=6,
    alpha=1.0, beta=0.15,
    lookahead=2,
    dir_dot_threshold=0.7,
    candidate_dist_filter=30,
    top_k_candidates=12,
    max_iterations=5000  # 🔴 무한루프 방지
):
    grid_size = GRID_SIZE
    current = start
    path = [start]
    trash_set = set(trash_positions)
    obstacle_set = set(obstacle_positions)
    
    iteration_count = 0  # 🔴 반복 카운터

    wind_dir = 0
    if env is not None:
        wd = env.get('풍향(deg)') if hasattr(env, 'get') else env['풍향(deg)']
        if not pd.isna(wd): wind_dir = wd

    directions8 = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]

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
        search_count = 0  # 🔴 A* 내부 반복 제한
        while open_set and search_count < 1000:
            search_count += 1
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

    def dijkstra(s, g):
        if s == g: return [s]
        pq = [(0, s)]
        came = {}
        best = {s: 0}
        search_count = 0  # 🔴 Dijkstra 내부 반복 제한
        while pq and search_count < 1000:
            search_count += 1
            c, u = heapq.heappop(pq)
            if u == g:
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

    def directional_candidates(points, center):
        if not points:  # 🔴 빈 리스트 체크
            return []
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
        cand = []
        for t in points:
            vx, vy = t[0]-center[0], t[1]-center[1]
            if best_dir[0]*vx + best_dir[1]*vy > 0 and distance(center, t) <= candidate_dist_filter:
                cand.append(t)
        if not cand:
            cand = sorted(points, key=lambda p: distance(center, p))[:top_k_candidates]
        else:
            cand = sorted(cand, key=lambda p: distance(center, p))[:top_k_candidates]
        return cand

    def evaluate_target_cost(cur, target, remaining):
        route = a_star_cached(cur, target)
        if route is None:
            route = dijkstra(cur, target)
            if route is None:
                return float('inf'), None
        cost = len(route)
        sim_pos = target
        rem = list(remaining - {target})
        for _ in range(max(0, lookahead-1)):
            if not rem: break
            nxt = min(rem, key=lambda p: adjusted_distance(sim_pos, p, wind_dir))
            cost += adjusted_distance(sim_pos, nxt, wind_dir)
            sim_pos = nxt
            rem.remove(nxt)
        return cost, route

    def follow_route(route, cur, collected):
        nonlocal path
        for step in route[1:]:
            if step in obstacle_set:
                adj = [(cur[0]+dx, cur[1]+dy) for dx, dy in directions8]
                adj = [a for a in adj if 0 <= a[0] < grid_size and 0 <= a[1] < grid_size and a not in obstacle_set]
                if not adj: return cur
                step = adj[0]
            path.append(step)
            cur = step
            if cur in trash_set: collected.add(cur)
        return cur

    collected = set()

    if hotspots:
        groups = build_hotspot_groups(list(trash_set), hotspots, radius=hotspot_radius)
        hotspot_iteration = 0  # 🔴 핫스팟 루프 카운터
        while hotspot_iteration < 100:  # 🔴 최대 100번만
            hotspot_iteration += 1
            iteration_count += 1
            if iteration_count > max_iterations:
                print(f"[WARN] 최대 반복 횟수 도달 (핫스팟 단계)")
                break
                
            cands = []
            for h, pts in groups.items():
                remain = [p for p in pts if p not in collected]
                if remain:
                    score = alpha*len(remain) - beta*distance(current, h)
                    cands.append((h, remain, score))
            if not cands: break
            target_h, remain_pts, _ = max(cands, key=lambda x: x[2])

            remain_set = set(remain_pts)
            inner_iteration = 0  # 🔴 내부 루프 카운터
            while remain_set and inner_iteration < 200:  # 🔴 최대 200번만
                inner_iteration += 1
                iteration_count += 1
                if iteration_count > max_iterations:
                    print(f"[WARN] 최대 반복 횟수 도달 (핫스팟 내부)")
                    break
                    
                candidates = directional_candidates(list(remain_set), current)
                if not candidates:  # 🔴 후보가 없으면 중단
                    break
                    
                best = (float('inf'), None, None)
                for t in candidates:
                    cost, route = evaluate_target_cost(current, t, remain_set)
                    if cost < best[0]:
                        best = (cost, t, route)
                if best[2] is None:
                    break
                current = follow_route(best[2], current, collected)
                if best[1] in remain_set: remain_set.remove(best[1])

        leftovers = list(trash_set - collected)
        leftover_iteration = 0  # 🔴 잔여 쓰레기 루프 카운터
        while leftovers and leftover_iteration < 300:  # 🔴 최대 300번만
            leftover_iteration += 1
            iteration_count += 1
            if iteration_count > max_iterations:
                print(f"[WARN] 최대 반복 횟수 도달 (잔여 쓰레기)")
                break
                
            candidates = directional_candidates(leftovers, current)
            if not candidates:  # 🔴 후보가 없으면 중단
                break
                
            best = (float('inf'), None, None)
            rem_set = set(leftovers)
            for t in candidates:
                cost, route = evaluate_target_cost(current, t, rem_set)
                if cost < best[0]:
                    best = (cost, t, route)
            if best[2] is None: break
            current = follow_route(best[2], current, collected)
            if best[1] in leftovers: leftovers.remove(best[1])

        return path[1:]

    # 핫스팟 없을 때
    remain = set(trash_set)
    no_hotspot_iteration = 0
    while remain and no_hotspot_iteration < 500:
        no_hotspot_iteration += 1
        iteration_count += 1
        if iteration_count > max_iterations:
            print(f"[WARN] 최대 반복 횟수 도달 (핫스팟 없음)")
            break
            
        candidates = directional_candidates(list(remain), current)
        if not candidates:
            break
            
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
# 성능 평가/저장
# ================================================
def evaluate_algorithm(algorithm, start, trash_positions, obstacle_positions, env=None, timeout=10):
    """타임아웃 포함 평가"""
    try:
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
                "elapsed_time": elapsed_time,
                "timeout": False}
    except Exception as e:
        print(f"[ERROR] 알고리즘 실행 실패: {e}")
        return {"collection_rate": 0.0,
                "collision_count": 0,
                "search_distance": 0,
                "elapsed_time": timeout,
                "timeout": True}

def print_results(results, index, total, env_row):
    progress = (index + 1) / total * 100
    print("=" * 60)
    print(f"🧪 Test #{index+1}/{total} ({progress:.1f}% 완료)")
    print(f"📅 관측시간: {env_row['관측시간']}")
    print(f"🌬️  풍속: {env_row['풍속(m/s)']:.1f} m/s, 풍향: {env_row['풍향(deg)']:.1f}°")
    print(f"🌊 파고: {env_row['유의파고(m)']:.2f} m, 파향: {env_row['파향(deg)']:.1f}°")
    print("-" * 60)
    for name, m in results.items():
        status = "⚠️ TIMEOUT" if m.get("timeout", False) else "✅"
        print(f"{name}: {status}")
        print(f"  ✓ 수집률: {m['collection_rate']:.4f} ({m['collection_rate']*100:.2f}%)")
        print(f"  ✗ 충돌 횟수: {m['collision_count']}")
        print(f"  📏 탐색 거리: {m['search_distance']}")
        print(f"  ⏱️  실행 시간: {m['elapsed_time']:.4f} sec")
    print("=" * 60)
    print()

algorithm_names = ["🧪Hybrid(Hotspot)"]

def save_results(all_results, save_folder=SAVE_DIR):
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
                "Timeout": result[algo].get("timeout", False)
            })
    df = pd.DataFrame(rows)
    output_file = os.path.join(save_folder, "algorithm_test_results_oct13.csv")
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ 결과 저장 완료: {output_file}")
    return df

# ================================================
# 메인 실행
# ================================================
print("\n" + "=" * 60)
print("🚀 10월 13일 데이터 분석 시작")
print(f"📊 총 {len(data)}개 테스트 예정")
print(f"⏱️  예상 소요 시간: 약 {len(data) * 0.4 / 60:.1f}분")
print("=" * 60)

all_results = []
total = len(data)
start_time = time.time()

for index, row in data.iterrows():
    env_row = row

    if USE_BIASED_TRASH:
        trash_positions, obstacle_positions = generate_trash_obstacles_biased(
    GRID_SIZE, env_row, HOTSPOTS, generate_trash_obstacles_with_environment
    )
    else:
        trash_positions, obstacle_positions = generate_trash_obstacles_with_environment(GRID_SIZE, env_row)

    start = (0, 0)

    hybrid_results = evaluate_algorithm(
    lambda s, t, o, env=None: hybrid_algorithm(
        s, t, o, env=env,
        hotspots=HOTSPOTS, hotspot_radius=HOTSPOT_RADIUS,
        alpha=1.0, beta=0.15,
        lookahead=2,
        dir_dot_threshold=0.7,
        candidate_dist_filter=30,
        top_k_candidates=12,
        max_iterations=5000  # 🔴 무한루프 방지
    ),
    start, trash_positions, obstacle_positions, env=env_row, timeout=10
    )

    results = {"🧪Hybrid(Hotspot)": hybrid_results}
    all_results.append(results)

    # 매 테스트마다 로그 출력
    print_results(results, index, total, env_row)

    # 10개마다 중간 진행 상황
    if (index + 1) % 10 == 0:
        elapsed = time.time() - start_time
        avg_time = elapsed / (index + 1)
        remaining = (total - index - 1) * avg_time
        print(f"⏳ 중간 진행: {index+1}/{total} 완료")
        print(f"   평균 소요 시간: {avg_time:.2f}초/테스트")
        print(f"   남은 시간: 약 {remaining/60:.1f}분\n")

    # 결과 저장
    total_time = time.time() - start_time
    print(f"\n⏱️  총 실행 시간: {total_time:.2f}초 ({total_time/60:.2f}분)")
    result_df = save_results(all_results)

    # 평균 결과
    print("\n" + "=" * 60)
    print("📊 10월 13일 전체 평균 결과")
    print("=" * 60)
    for algo in algorithm_names:
        a = result_df[result_df["Algorithm"] == algo]
        timeout_count = a["Timeout"].sum()
        print(f"\n{algo}")
        print(f"  총 테스트: {len(a)}개")
        print(f"  타임아웃: {timeout_count}개")
        print(f"  평균 수집률: {a['CollectionRate'].mean():.4f} ({a['CollectionRate'].mean()*100:.2f}%)")
        print(f"  평균 충돌 횟수: {a['CollisionCount'].mean():.2f}")
        print(f"  평균 탐색 거리: {a['SearchDistance'].mean():.2f}")
        print(f"  평균 실행 시간: {a['ElapsedTime'].mean():.4f} sec")
    print("=" * 60)
    print()
# 
# 
# 
# 알고리즘 52806개 돌리는 코드
# # -*- coding: utf-8 -*-
# import pandas as pd
# import random
# import numpy as np
# import time
# import heapq
# import math
# import os
# import glob
# import json

# # ================================================
# # 작업 디렉토리 / 결과 경로
# # ================================================
# BASE_DIR = r"C:\Users\User\OneDrive\바탕 화면\sweep\2025부산빅데이터\trash_test"
# os.chdir(BASE_DIR)
# SAVE_DIR = os.path.join(BASE_DIR, "algo_test_results")
# os.makedirs(SAVE_DIR, exist_ok=True)

# # Step3/4 산출물 경로
# FINAL_DIR = os.path.join(BASE_DIR, "daily_results_final_251013")
# HIST_DIR  = os.path.join(BASE_DIR, "daily_results_hotspot_251013")

# GRID_SIZE = 50
# TOP_K_HOTSPOTS = 15
# MIN_REWARD_VAL  = None
# USE_BIASED_TRASH = True

# # ================================================
# # 🔁 Hotspots Adapter: Step3/4 결과 → 격자(0~49) 매핑
# # ================================================
# def _clamp(v, vmin, vmax):
#     return max(vmin, min(vmax, v))

# def _to_grid(x, xmin, xmax, grid_size):
#     if xmax == xmin:
#         return 0
#     g = round((x - xmin) / (xmax - xmin) * (grid_size - 1))
#     return int(_clamp(g, 0, grid_size-1))

# def load_hotspots_to_grid(final_dir=FINAL_DIR, hist_dir=HIST_DIR,
#                           grid_size=GRID_SIZE, top_k=TOP_K_HOTSPOTS, min_reward=MIN_REWARD_VAL):
#     with open(os.path.join(hist_dir, "history_summary.json"), "r", encoding="utf-8") as f:
#         s = json.load(f)
#     x_min, x_max = s["x_range"]; y_min, y_max = s["y_range"]

#     with open(os.path.join(final_dir, "hotspots.json"), "r", encoding="utf-8") as f:
#         hs = json.load(f)["hotspots"]

#     if min_reward is not None:
#         hs = [h for h in hs if float(h["value"]) >= float(min_reward)]
#     hs = sorted(hs, key=lambda h: h["value"], reverse=True)
#     if top_k is not None:
#         hs = hs[:int(top_k)]

#     seen = set()
#     grid_points = []
#     for h in hs:
#         gx = _to_grid(h["x"], x_min, x_max, grid_size)
#         gy = _to_grid(h["y"], y_min, y_max, grid_size)
#         if (gx, gy) not in seen:
#             seen.add((gx, gy))
#             grid_points.append((gx, gy))
#     return grid_points

# def suggest_hotspot_radius(grid_size=GRID_SIZE, n_hotspots=10):
#     base = max(4, int(0.12 * grid_size))
#     if n_hotspots > 20: base = max(3, base-2)
#     if n_hotspots > 35: base = max(2, base-2)
#     return base

# def generate_trash_obstacles_biased(grid_size, env_row, hotspots, base_func):
#     trash, obstacles = base_func(grid_size, env_row)
#     if not hotspots:
#         return trash, obstacles
#     extra = []
#     for (hx, hy) in hotspots:
#         m = random.randint(10, 20)
#         for _ in range(m):
#             dx = random.randint(-3, 3); dy = random.randint(-3, 3)
#             x = _clamp(hx + dx, 0, grid_size-1)
#             y = _clamp(hy + dy, 0, grid_size-1)
#             extra.append((x, y))
#     trash.extend(extra)
#     return trash, obstacles

# # ================================================
# # 🔴 핫스팟 로드 (분석 산출물에서 자동)
# # ================================================
# try:
#     HOTSPOTS = load_hotspots_to_grid()
#     print(f"[INFO] Loaded HOTSPOTS ({len(HOTSPOTS)}): {HOTSPOTS}")
# except Exception as e:
#     print(f"[WARN] 핫스팟 자동 로드 실패: {e}")
#     HOTSPOTS = [(8, 6), (12, 30), (20, 22), (33, 18), (40, 40)]
#     print(f"[INFO] Fallback HOTSPOTS used: {HOTSPOTS}")

# HOTSPOT_RADIUS = suggest_hotspot_radius(n_hotspots=len(HOTSPOTS))
# print(f"[INFO] HOTSPOT_RADIUS (suggested): {HOTSPOT_RADIUS}")

# # ================================================
# # 📥 환경 데이터 로드 (2022~2024 월별 TSV, cp949 + fallback)
# # ================================================
# def to_deg(val):
#     if pd.isna(val): return np.nan
#     s = str(val).strip()
#     DIR2DEG = {
#         '북': 0, '북북동': 22.5, '북동': 45, '동북동': 67.5,
#         '동': 90, '동남동': 112.5, '남동': 135, '남남동': 157.5,
#         '남': 180, '남남서': 202.5, '남서': 225, '서남서': 247.5,
#         '서': 270, '서북서': 292.5, '북서': 315, '북북서': 337.5,
#         '동풍': 90, '서풍': 270, '남풍': 180, '북풍': 0,
#     }
#     if s in DIR2DEG: return DIR2DEG[s]
#     if '/' in s:
#         parts = [p.strip() for p in s.split('/')]
#         vals = [DIR2DEG.get(p, np.nan) for p in parts]
#         if all([not np.isnan(v) for v in vals]): return float(np.mean(vals))
#     try:
#         return float(s)
#     except:
#         return np.nan

# def read_month_csv(fpath):
#     # cp949 → utf-16 → utf-8-sig 순으로 시도
#     for enc in ['cp949', 'utf-16', 'utf-8-sig']:
#         try:
#             return pd.read_csv(fpath, encoding=enc, sep='\t', skiprows=3)
#         except Exception:
#             continue
#     print(f"[WARN] CSV 읽기 실패(모든 인코딩 시도): {fpath}")
#     return None

# def load_env_data_from_monthly_files(base_dir, years=(2022, 2023, 2024)):
#     data_dir = os.path.join(base_dir, "data")
#     frames = []
#     for y in years:
#         for m in range(1, 13):
#             fname = f"{y}년 {m:02d}월 대한해협 해양관측부이.csv"
#             fpath = os.path.join(data_dir, fname)
#             if not os.path.exists(fpath):
#                 continue
#             df = read_month_csv(fpath)
#             if df is None:
#                 continue

#             # 컬럼 표준화/보강
#             colmap = {}
#             if '유의파고(MOSE.HF)(m)' in df.columns:
#                 colmap['유의파고(MOSE.HF)(m)'] = '유의파고(m)'
#             if 'GUST풍속(m/s)' not in df.columns:
#                 df['GUST풍속(m/s)'] = 0.0
#             if '최대파고(m)' not in df.columns:
#                 df['최대파고(m)'] = 0.0
#             if '평균파고(m)' not in df.columns:
#                 df['평균파고(m)'] = df['유의파고(m)'] if '유의파고(m)' in df.columns else 0.0
#             if '파주기(sec)' not in df.columns:
#                 df['파주기(sec)'] = 0.0

#             df = df.rename(columns=colmap)

#             need_cols = ['관측시간', '풍속(m/s)', '풍향(deg)', '유의파고(m)', '파향(deg)',
#                          'GUST풍속(m/s)', '최대파고(m)', '평균파고(m)', '파주기(sec)']
#             for c in need_cols:
#                 if c not in df.columns:
#                     df[c] = 0.0

#             df['관측시간'] = pd.to_datetime(df['관측시간'], errors='coerce')
#             for c in ['풍속(m/s)', '유의파고(m)', 'GUST풍속(m/s)', '최대파고(m)', '평균파고(m)', '파주기(sec)']:
#                 df[c] = pd.to_numeric(df[c], errors='coerce')
#             df['풍향(deg)'] = df['풍향(deg)'].apply(to_deg)
#             df['파향(deg)'] = df['파향(deg)'].apply(to_deg)

#             df = df.fillna(0)
#             frames.append(df[need_cols])
#             print(f"[INFO] Loaded: {fpath}  rows={len(df)}")
#     if not frames:
#         raise FileNotFoundError("data 폴더에 월별 파일을 찾지 못했습니다.")
#     out = pd.concat(frames, ignore_index=True).sort_values('관측시간').reset_index(drop=True)
#     print(f"[INFO] 환경 데이터 통합 완료: rows={len(out)}  from years={years}")
#     return out

# # 실제 로드
# data = load_env_data_from_monthly_files(BASE_DIR)

# # ⚡️테스트/진행상태 확인을 빠르게 하고 싶으면 아래 필터 중 택1 (주석 해제)
# # data = data[data['관측시간'].dt.strftime('%m-%d') == '10-13'].reset_index(drop=True)  # 10/13만
# # data = data.iloc[:100].reset_index(drop=True)  # 상위 100행만

# # ================================================
# # 환경 기반 쓰레기/장애물 생성 (원본 로직 유지)
# # ================================================
# def generate_trash_obstacles_with_environment(grid_size, env_row):
#     wind_speed = env_row['풍속(m/s)']; wind_direction = env_row['풍향(deg)']
#     gust_speed = env_row['GUST풍속(m/s)']; max_wave_height = env_row['최대파고(m)']
#     significant_wave_height = env_row['유의파고(m)']; mean_wave_height = env_row['평균파고(m)']
#     wave_period = env_row['파주기(sec)']; wave_direction = env_row['파향(deg)']

#     if pd.isna(wind_speed): wind_speed = 0
#     if pd.isna(wind_direction): wind_direction = 0
#     if pd.isna(gust_speed): gust_speed = 0
#     if pd.isna(max_wave_height): max_wave_height = 0
#     if pd.isna(significant_wave_height): significant_wave_height = 0
#     if pd.isna(mean_wave_height): mean_wave_height = 0
#     if pd.isna(wave_period): wave_period = 0
#     if pd.isna(wave_direction): wave_direction = 0

#     base_trash, base_obstacles = 50, 10
#     trash_count = min(base_trash + int(wind_speed*5) + int(significant_wave_height*10), 300)
#     obstacle_count = min(base_obstacles + int(gust_speed*2) + int(max_wave_height*5), 50)

#     trash_positions = []
#     for _ in range(trash_count):
#         bx = random.randint(0, GRID_SIZE-1); by = random.randint(0, GRID_SIZE-1)
#         off = random.randint(0, 5)
#         nx = max(0, min(GRID_SIZE-1, bx + int(np.cos(np.radians(wind_direction))*off)))
#         ny = max(0, min(GRID_SIZE-1, by + int(np.sin(np.radians(wind_direction))*off)))
#         trash_positions.append((nx, ny))

#     obstacle_positions = []
#     for _ in range(obstacle_count):
#         bx = random.randint(0, GRID_SIZE-1); by = random.randint(0, GRID_SIZE-1)
#         off = random.randint(0, 3)
#         nx = max(0, min(GRID_SIZE-1, bx + int(np.cos(np.radians(wave_direction))*off)))
#         ny = max(0, min(GRID_SIZE-1, by + int(np.sin(np.radians(wave_direction))*off)))
#         obstacle_positions.append((nx, ny))

#     return trash_positions, obstacle_positions

# # ================================================
# # 공용 유틸
# # ================================================
# def distance(a, b):
#     return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

# def adjusted_distance(a, b, wind_direction):
#     dx, dy = b[0]-a[0], b[1]-a[1]
#     base = math.sqrt(dx*dx + dy*dy)
#     if base == 0: return 0.0
#     ang = (math.degrees(math.atan2(dy, dx)) % 360)
#     diff = abs(wind_direction - ang); diff = min(diff, 360 - diff)
#     penalty = 1 + (diff/180.0)*0.5
#     return base * penalty

# def build_hotspot_groups(trash_positions, hotspots, radius=6):
#     groups = {h: [] for h in hotspots}
#     for t in trash_positions:
#         h = min(hotspots, key=lambda x: distance(t, x))
#         if distance(t, h) <= radius:
#             groups[h].append(t)
#     return groups

# # ================================================
# # Hybrid(Hotspot) — 기존 알고리즘 본체
# # ================================================
# def hybrid_algorithm(
#     start,
#     trash_positions,
#     obstacle_positions,
#     env=None,
#     hotspots=None,
#     hotspot_radius=6,
#     alpha=1.0, beta=0.15,
#     lookahead=2,
#     dir_dot_threshold=0.7,
#     candidate_dist_filter=30,
#     top_k_candidates=12
# ):
#     grid_size = GRID_SIZE
#     current = start
#     path = [start]
#     trash_set = set(trash_positions)
#     obstacle_set = set(obstacle_positions)

#     wind_dir = 0
#     if env is not None:
#         wd = env.get('풍향(deg)') if hasattr(env, 'get') else env['풍향(deg)']
#         if not pd.isna(wd): wind_dir = wd

#     directions8 = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]

#     astar_cache = {}
#     def a_star_cached(s, g):
#         if s == g: return [s]
#         key = (s, g)
#         if key in astar_cache: return astar_cache[key]
#         rk = (g, s)
#         if rk in astar_cache and astar_cache[rk] is not None:
#             return list(reversed(astar_cache[rk]))
#         open_set = []
#         heapq.heappush(open_set, (adjusted_distance(s, g, wind_dir), 0, s, [s]))
#         best_g = {s: 0}
#         closed = set()
#         while open_set:
#             f, g_cost, u, u_path = heapq.heappop(open_set)
#             if u == g:
#                 astar_cache[key] = u_path
#                 return u_path
#             if u in closed: continue
#             closed.add(u)
#             for dx, dy in directions8:
#                 nx, ny = u[0]+dx, u[1]+dy
#                 if not (0 <= nx < grid_size and 0 <= ny < grid_size): continue
#                 v = (nx, ny)
#                 if v in obstacle_set: continue
#                 ng = g_cost + 1
#                 if ng < best_g.get(v, 1e18):
#                     best_g[v] = ng
#                     nf = ng + adjusted_distance(v, g, wind_dir)
#                     heapq.heappush(open_set, (nf, ng, v, u_path+[v]))
#         astar_cache[key] = None
#         return None

#     def dijkstra(s, g):
#         if s == g: return [s]
#         pq = [(0, s)]
#         came = {}
#         best = {s: 0}
#         while pq:
#             c, u = heapq.heappop(pq)
#             if u == g:
#                 path2 = [u]
#                 while u in came:
#                     u = came[u]; path2.append(u)
#                 return list(reversed(path2))
#             for dx, dy in directions8:
#                 v = (u[0]+dx, u[1]+dy)
#                 if not (0 <= v[0] < grid_size and 0 <= v[1] < grid_size): continue
#                 if v in obstacle_set: continue
#                 nc = c + 1
#                 if nc < best.get(v, 1e-18):
#                     best[v] = nc
#                     came[v] = u
#                     heapq.heappush(pq, (nc, v))
#         return None

#     def directional_candidates(points, center):
#         scores = []
#         for dx, dy in directions8:
#             dir_vec = np.array([dx, dy]); norm = np.linalg.norm(dir_vec)
#             if norm == 0:
#                 scores.append(0.0); continue
#             sc = 0.0
#             for tx, ty in points:
#                 vec = np.array([tx-center[0], ty-center[1]])
#                 dist = np.linalg.norm(vec)
#                 if dist == 0: continue
#                 dot = float(np.dot(dir_vec, vec)/(norm*dist))
#                 if dot >= dir_dot_threshold:
#                     sc += 1.0/(dist+1e-5)
#             scores.append(sc)
#         best_dir = directions8[int(np.argmax(scores))]
#         cand = []
#         for t in points:
#             vx, vy = t[0]-center[0], t[1]-center[1]
#             if best_dir[0]*vx + best_dir[1]*vy > 0 and distance(center, t) <= candidate_dist_filter:
#                 cand.append(t)
#         if not cand:
#             cand = sorted(points, key=lambda p: distance(center, p))[:top_k_candidates]
#         else:
#             cand = sorted(cand, key=lambda p: distance(center, p))[:top_k_candidates]
#         return cand

#     def evaluate_target_cost(cur, target, remaining):
#         route = a_star_cached(cur, target)
#         if route is None:
#             route = dijkstra(cur, target)
#             if route is None:
#                 return float('inf'), None
#         cost = len(route)
#         sim_pos = target
#         rem = list(remaining - {target})
#         for _ in range(max(0, lookahead-1)):
#             if not rem: break
#             nxt = min(rem, key=lambda p: adjusted_distance(sim_pos, p, wind_dir))
#             cost += adjusted_distance(sim_pos, nxt, wind_dir)
#             sim_pos = nxt
#             rem.remove(nxt)
#         return cost, route

#     def follow_route(route, cur, collected):
#         nonlocal path
#         for step in route[1:]:
#             if step in obstacle_set:
#                 adj = [(cur[0]+dx, cur[1]+dy) for dx, dy in directions8]
#                 adj = [a for a in adj if 0 <= a[0] < grid_size and 0 <= a[1] < grid_size and a not in obstacle_set]
#                 if not adj: return cur
#                 step = adj[0]
#             path.append(step)
#             cur = step
#             if cur in trash_set: collected.add(cur)
#         return cur

#     collected = set()

#     if hotspots:
#         groups = build_hotspot_groups(list(trash_set), hotspots, radius=hotspot_radius)
#         while True:
#             cands = []
#             for h, pts in groups.items():
#                 remain = [p for p in pts if p not in collected]
#                 if remain:
#                     score = alpha*len(remain) - beta*distance(current, h)
#                     cands.append((h, remain, score))
#             if not cands: break
#             target_h, remain_pts, _ = max(cands, key=lambda x: x[2])

#             remain_set = set(remain_pts)
#             while remain_set:
#                 candidates = directional_candidates(list(remain_set), current)
#                 best = (float('inf'), None, None)
#                 for t in candidates:
#                     cost, route = evaluate_target_cost(current, t, remain_set)
#                     if cost < best[0]:
#                         best = (cost, t, route)
#                 if best[2] is None:
#                     break
#                 current = follow_route(best[2], current, collected)
#                 if best[1] in remain_set: remain_set.remove(best[1])

#         leftovers = list(trash_set - collected)
#         while leftovers:
#             candidates = directional_candidates(leftovers, current)
#             best = (float('inf'), None, None)
#             rem_set = set(leftovers)
#             for t in candidates:
#                 cost, route = evaluate_target_cost(current, t, rem_set)
#                 if cost < best[0]:
#                     best = (cost, t, route)
#             if best[2] is None: break
#             current = follow_route(best[2], current, collected)
#             if best[1] in leftovers: leftovers.remove(best[1])

#         return path[1:]

#     remain = set(trash_set)
#     while remain:
#         candidates = directional_candidates(list(remain), current)
#         best = (float('inf'), None, None)
#         for t in candidates:
#             cost, route = evaluate_target_cost(current, t, remain)
#             if cost < best[0]:
#                 best = (cost, t, route)
#         if best[2] is None: break
#         current = follow_route(best[2], current, collected)
#         remain.discard(best[1])

#     return path[1:]

# # ================================================
# # 성능 평가/저장
# # ================================================
# def evaluate_algorithm(algorithm, start, trash_positions, obstacle_positions, env=None):
#     t0 = time.time()
#     results = algorithm(start, trash_positions.copy(), obstacle_positions, env)
#     t1 = time.time()
#     collection_rate = len(set(results) & set(trash_positions))/len(trash_positions) if trash_positions else 0
#     collision_count = len([p for p in results if p in set(obstacle_positions)])
#     search_distance = len(results)
#     elapsed_time = t1 - t0
#     return {"collection_rate": collection_rate,
#             "collision_count": collision_count,
#             "search_distance": search_distance,
#             "elapsed_time": elapsed_time}

# def print_results(results):
#     for name, m in results.items():
#         print(f"{name} Algorithm:")
#         print(f"  수집률: {m['collection_rate']:.4f}")
#         print(f"  충돌 횟수: {m['collision_count']}")
#         print(f"  탐색 거리: {m['search_distance']}")
#         print(f"  실행 시간: {m['elapsed_time']:.4f} seconds")
#         print()

# algorithm_names = ["🧪Hybrid(Hotspot)"]

# def save_partial_results(all_results, save_count, save_folder=SAVE_DIR):
#     rows = []
#     for i, result in enumerate(all_results):
#         for algo in algorithm_names:
#             rows.append({
#                 "Index": i,
#                 "Algorithm": algo,
#                 "CollectionRate": result[algo]["collection_rate"],
#                 "CollisionCount": result[algo]["collision_count"],
#                 "SearchDistance": result[algo]["search_distance"],
#                 "ElapsedTime": result[algo]["elapsed_time"],
#             })
#     pd.DataFrame(rows).to_csv(os.path.join(save_folder, f"algorithm_test_results_{save_count}.csv"),
#                               index=False, encoding='utf-8-sig')

# # ================================================
# # 메인 실행 (로그를 5행마다, 첫 행부터 즉시 출력)
# # ================================================
# all_results = []
# batch_size = 100          # 중간 저장 간격(좀 더 자주)
# save_count = 1
# total = len(data)

# print(f"[START] rows={total}", flush=True)

# for index, row in data.iterrows():
#     if index == 0:
#         print(f"[RUNNING] Processing row {index+1}/{total}", flush=True)
#     elif (index + 1) % 5 == 0:
#         print(f"[RUNNING] Processing row {index+1}/{total}", flush=True)

#     env_row = row

#     if USE_BIASED_TRASH:
#         trash_positions, obstacle_positions = generate_trash_obstacles_biased(
#             GRID_SIZE, env_row, HOTSPOTS, generate_trash_obstacles_with_environment
#         )
#     else:
#         trash_positions, obstacle_positions = generate_trash_obstacles_with_environment(GRID_SIZE, env_row)

#     start = (0, 0)

#     hybrid_results = evaluate_algorithm(
#         lambda s, t, o, env=None: hybrid_algorithm(
#             s, t, o, env=env,
#             hotspots=HOTSPOTS, hotspot_radius=HOTSPOT_RADIUS,
#             alpha=1.0, beta=0.15,
#             lookahead=2,
#             dir_dot_threshold=0.7,
#             candidate_dist_filter=30,
#             top_k_candidates=12
#         ),
#         start, trash_positions, obstacle_positions, env=env_row
#     )

#     results = {"🧪Hybrid(Hotspot)": hybrid_results}
#     all_results.append(results)

#     # 진행 요약을 5행마다 표시
#     if (index + 1) % 5 == 0 or (index + 1) == total:
#         print("\n------------------------------------------------", flush=True)
#         print(f"Data Index {index+1}/{total}: ({(index+1)/total*100:.2f}%)", flush=True)
#         print_results(results)

#     # 중간 저장 간격
#     if (index + 1) % batch_size == 0 or (index + 1) == total:
#         save_partial_results(all_results, save_count)
#         print(f"[INFO] Results saved: batch {save_count}", flush=True)
#         save_count += 1
#         all_results = []

# if all_results:
#     save_partial_results(all_results, save_count)
#     print("\n================================================", flush=True)
#     print(f"✅ TEST RESULT FILE SAVED: algorithm_test_results_{save_count}.csv", flush=True)
#     print("================================================\n", flush=True)

# # 평균 결과
# print("\n================================================", flush=True)
# print("✅ TEST RESULT AVERAGE", flush=True)
# file_list = glob.glob(os.path.join(SAVE_DIR, "algorithm_test_results_*.csv"))
# full_df = pd.concat([pd.read_csv(f) for f in file_list], ignore_index=True)
# for algo in algorithm_names:
#     a = full_df[full_df["Algorithm"] == algo]
#     print(f"\n=== {algo} ===", flush=True)
#     print(f"  수집률 평균: {a['CollectionRate'].mean():.4f}", flush=True)
#     print(f"  충돌 횟수 평균: {a['CollisionCount'].mean():.4f}", flush=True)
#     print(f"  탐색 거리 평균: {a['SearchDistance'].mean():.4f}", flush=True)
#     print(f"  실행 시간 평균: {a['ElapsedTime'].mean():.4f} seconds", flush=True)
# print()