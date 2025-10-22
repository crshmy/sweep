# -*- coding: utf-8 -*-
"""
Step 6 (Hybrid): 과거+예측 결합 히트맵 기반 trash field 구성 → Hybrid(Hotspot) 경로 생성
- 입력:
  - daily_results_hotspot_251013/history_summary.json (Step1 그리드 범위/해상도)
  - daily_results_forecast_251013/H_pred.npy          (Step2 예측 히트맵)
  - daily_results_final_251013/hotspots.json          (Step3/4 통합 핫스팟)
  - 대한해협.xlsx                                     (예측일 평균 풍향/풍속; 없으면 기본값)
- 출력:
  - daily_results_route_251013/route_hybrid_waypoints.csv
  - daily_results_route_251013/route_hybrid.geojson
  - daily_results_route_251013/route_hybrid.png
  - (옵션) route_hybrid_wgs84.geojson / route_hybrid_wgs84.csv
"""

import os, json, math, numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# ===================== 경로/설정 =====================
BASE_DIR = r"C:\ClaudeFolder\marine_cleanup_nav\hotspot"
ROUTE_DIR = os.path.join(BASE_DIR, "route_results")
os.makedirs(ROUTE_DIR, exist_ok=True)

HIST_DIR   = os.path.join(BASE_DIR, "daily_results_hotspot_251013")
FORE_DIR   = os.path.join(BASE_DIR, "daily_results_forecast_251013")
FINAL_DIR  = os.path.join(BASE_DIR, "daily_results_final_251013")
ROUTE_DIR  = os.path.join(BASE_DIR, "daily_results_route_251013")
os.makedirs(ROUTE_DIR, exist_ok=True)

XLSX_PATH  = os.path.join(BASE_DIR, "대한해협.xlsx")   # 없으면 풍향=0 처리

# === 하이브리드/그리드/샘플링 파라미터 ===
GRID_SIZE            = 50          # 경로계획 그리드 (0~49)
TOP_K_HOTSPOTS       = 15
MIN_VALUE_THRESH     = None        # 예: 0.2 이상만 사용
TRASH_POINTS_TOTAL   = 2000        # 전체 trash 샘플 수(히트맵 비례)
TRASH_MIN_CELL_WEIGHT= 0.0         # 셀 필터 임계 (0이면 전부)
HOTSPOT_BONUS_EACH   = (80, 140)   # 각 핫스팟 주변 추가 샘플 범위
HOTSPOT_RADIUS_GRID  = None        # None이면 자동 제안 사용
LOOKAHEAD            = 2
ALPHA_HS             = 1.0
BETA_HS_DIST         = 0.15
DIR_DOT_THRESHOLD    = 0.7
CAND_DIST_FILTER     = 30
TOP_K_CANDIDATES     = 12

START_MODE           = 'auto'      # 'auto' (최상위 핫스팟) / 'fixed'
START_GRID_XY        = (0, 0)      # START_MODE='fixed'일 때 시작 칸

# 선박 속도(ETA 용)
VESSEL_SPEED_KTS = 6.0; KNOT_TO_KMPH = 1.852
VESSEL_SPEED_KMPH= VESSEL_SPEED_KTS * KNOT_TO_KMPH

# (옵션) 위경도로 변환 저장할지
EXPORT_WGS84 = False

# ===================== 공통 유틸 =====================
def _clamp(v, vmin, vmax): return max(vmin, min(vmax, v))

def load_history_grid(summary_path):
    with open(summary_path, 'r', encoding='utf-8') as f:
        s = json.load(f)
    x_min, x_max = s['x_range']; y_min, y_max = s['y_range']
    bins = int(s['bins'])
    x_edges = np.linspace(x_min, x_max, bins)
    y_edges = np.linspace(y_min, y_max, bins)
    return x_edges, y_edges, bins

def load_forecast_heatmap(fore_dir):
    npy_path = os.path.join(fore_dir, "H_pred.npy")
    if not os.path.exists(npy_path):
        raise FileNotFoundError(f"예측 히트맵이 없습니다: {npy_path}")
    return np.load(npy_path)

def load_hotspots(final_dir, top_k=TOP_K_HOTSPOTS, min_thr=MIN_VALUE_THRESH):
    fp = os.path.join(final_dir, "hotspots.json")
    if not os.path.exists(fp):
        raise FileNotFoundError(f"핫스팟 JSON이 없습니다: {fp}")
    hs = json.load(open(fp, 'r', encoding='utf-8'))['hotspots']
    if min_thr is not None:
        hs = [h for h in hs if float(h['value']) >= float(min_thr)]
    hs = sorted(hs, key=lambda h: h['value'], reverse=True)
    if top_k: hs = hs[:top_k]
    return hs  # [{'x','y','value'}, ...]

# === 엑셀에서 예측일 평균 풍향/풍속 ===
DIR2DEG = {
    '북':0,'북북동':22.5,'북동':45,'동북동':67.5,'동':90,'동남동':112.5,'남동':135,'남남동':157.5,
    '남':180,'남남서':202.5,'남서':225,'서남서':247.5,'서':270,'서북서':292.5,'북서':315,'북북서':337.5,
    '동풍':90,'서풍':270,'남풍':180,'북풍':0,
}
def to_deg(x):
    if pd.isna(x): return np.nan
    s = str(x).strip()
    if s in DIR2DEG: return DIR2DEG[s]
    if '/' in s:
        parts = [p.strip() for p in s.split('/')]
        vals = [DIR2DEG.get(p, np.nan) for p in parts]
        if all(not np.isnan(v) for v in vals): return float(np.mean(vals))
    try: return float(s)
    except: return np.nan

def get_daily_wind_direction_from_excel(xlsx_path):
    try:
        df = pd.read_excel(xlsx_path, sheet_name=0, header=None)
    except Exception:
        return 0.0, 0.0
    def find_row_after(start_i, keyword):
        for k in range(1, 8):
            if start_i + k >= len(df): break
            v = str(df.iloc[start_i+k,0]).strip()
            if keyword in v: return df.iloc[start_i+k].tolist()
        return None
    wdir_all, wspd_all = [], []
    i=0
    while i < len(df):
        if str(df.iloc[i,0]).strip() == '위도':
            row_wdir = find_row_after(i, '풍향'); row_wspd = find_row_after(i, '풍속')
            if row_wdir is None or row_wspd is None: i+=7; continue
            wdir_all += [to_deg(x) for x in row_wdir[1:9]]
            wspd_all += [pd.to_numeric(str(x).replace('m/s','').strip(), errors='coerce') for x in row_wspd[1:9]]
            i += 7
        else:
            i += 1
    wd = [x for x in wdir_all if not np.isnan(x)]
    ws = [x for x in wspd_all if not (pd.isna(x) or x is None)]
    if wd:
        rad = np.radians(wd); wind_dir = math.degrees(math.atan2(np.mean(np.sin(rad)), np.mean(np.cos(rad)))) % 360
    else:
        wind_dir = 0.0
    mean_wspd = float(np.mean(ws)) if ws else 0.0
    return wind_dir, mean_wspd

# === 좌표 변환: km <-> grid ===
def grid_to_km(ix, iy, x_edges, y_edges, grid_size=GRID_SIZE):
    x = np.interp(ix + 0.5, [0, grid_size], [x_edges[0], x_edges[-1]])
    y = np.interp(iy + 0.5, [0, grid_size], [y_edges[0], y_edges[-1]])
    return float(x), float(y)

# === 히트맵을 50x50 그리드로 재매핑 ===
def remap_heatmap_to_grid(H, out_size=GRID_SIZE):
    src_h, src_w = H.shape
    res = np.zeros((out_size, out_size), dtype=float)
    for gy in range(out_size):
        y0 = gy * src_h / out_size
        y1 = (gy+1) * src_h / out_size
        y0i, y1i = int(math.floor(y0)), int(math.ceil(y1))
        for gx in range(out_size):
            x0 = gx * src_w / out_size
            x1 = (gx+1) * src_w / out_size
            x0i, x1i = int(math.floor(x0)), int(math.ceil(x1))
            block = H[y0i:y1i, x0i:x1i]
            if block.size>0:
                res[gy, gx] = block.mean()
    return res

# === 히트맵 → trash positions 생성 (핫스팟 인자 무시: 언패킹 에러 방지) ===
def sample_trash_from_heatmap_and_hotspots(Hg,
                                           hotspots_any=None,           # 🔹 더 이상 사용하지 않음(바이어스는 add_hotspot_bias에서 처리)
                                           total_points=TRASH_POINTS_TOTAL,
                                           min_cell_weight=TRASH_MIN_CELL_WEIGHT,
                                           hotspot_bonus_each=HOTSPOT_BONUS_EACH,
                                           grid_size=GRID_SIZE):
    """
    예측 히트맵(Hg, 이미 GRID_SIZE×GRID_SIZE로 리샘플된 값)에 비례해서
    trash 포인트를 샘플링합니다.
    핫스팟 주변 보너스는 별도의 add_hotspot_bias()에서 grid 좌표로 주입합니다.
    """
    rng = np.random.default_rng(42)
    H = Hg.copy().astype(float)
    H[np.isnan(H)] = 0.0
    if min_cell_weight is not None:
        H[H < float(min_cell_weight)] = 0.0

    if H.sum() <= 0:
        base = [(int(rng.integers(0, grid_size)),
                 int(rng.integers(0, grid_size))) for _ in range(total_points)]
    else:
        prob = (H / H.sum()).ravel()
        idxs = rng.choice(H.size, size=total_points, replace=True, p=prob)
        ys, xs = np.unravel_index(idxs, H.shape)  # (row, col)
        base = list(zip(xs.tolist(), ys.tolist()))

    # 장애물은 현재 사용하지 않으므로 빈 리스트 반환
    return base, []

def add_hotspot_bias(trash_positions, hotspot_grid_pts, each_range=HOTSPOT_BONUS_EACH,
                     grid_size=GRID_SIZE):
    rng = np.random.default_rng(123)
    extra = []
    for (hx, hy) in hotspot_grid_pts:
        m = rng.integers(each_range[0], each_range[1]+1)
        for _ in range(int(m)):
            dx = int(rng.integers(-3, 4))
            dy = int(rng.integers(-3, 4))
            x = _clamp(hx+dx, 0, grid_size-1)
            y = _clamp(hy+dy, 0, grid_size-1)
            extra.append((x, y))
    trash_positions.extend(extra)
    return trash_positions

# === Hybrid(Hotspot) 알고리즘 ===
import heapq
def distance(a,b): return math.hypot(a[0]-b[0], a[1]-b[1])

def adjusted_distance(a, b, wind_direction):
    dx, dy = b[0]-a[0], b[1]-a[1]; base = math.hypot(dx, dy)
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
    grid_size=GRID_SIZE
):
    current = start
    path = [start]
    trash_set = set(trash_positions)
    obstacle_set = set(obstacle_positions)
    wind_dir = 0
    if env is not None:
        wd = env.get('풍향(deg)', 0.0)
        if not pd.isna(wd): wind_dir = float(wd)

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
        best_g = {s:0}; closed=set()
        while open_set:
            f, g_cost, u, u_path = heapq.heappop(open_set)
            if u == g:
                astar_cache[key] = u_path; return u_path
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
        pq = [(0, s)]; came={}; best={s:0}
        while pq:
            c,u = heapq.heappop(pq)
            if u == g:
                path2=[u]
                while u in came:
                    u = came[u]; path2.append(u)
                return list(reversed(path2))
            for dx, dy in directions8:
                v = (u[0]+dx, u[1]+dy)
                if not (0 <= v[0] < grid_size and 0 <= v[1] < grid_size): continue
                if v in obstacle_set: continue
                nc = c + 1
                if nc < best.get(v, 1e18):
                    best[v] = nc; came[v]=u; heapq.heappush(pq,(nc,v))
        return None

    def directional_candidates(points, center):
        scores=[]
        for dx, dy in directions8:
            dir_vec=np.array([dx,dy]); norm=np.linalg.norm(dir_vec)
            if norm==0: scores.append(0.0); continue
            sc=0.0
            for tx,ty in points:
                vec=np.array([tx-center[0], ty-center[1]])
                dist=np.linalg.norm(vec)
                if dist==0: continue
                dot=float(np.dot(dir_vec, vec)/(norm*dist))
                if dot >= DIR_DOT_THRESHOLD:
                    sc += 1.0/(dist+1e-5)
            scores.append(sc)
        best_dir = directions8[int(np.argmax(scores))]
        cand=[]
        for t in points:
            vx,vy = t[0]-center[0], t[1]-center[1]
            if best_dir[0]*vx + best_dir[1]*vy > 0 and distance(center,t) <= CAND_DIST_FILTER:
                cand.append(t)
        if not cand:
            cand=sorted(points, key=lambda p: distance(center,p))[:TOP_K_CANDIDATES]
        else:
            cand=sorted(cand, key=lambda p: distance(center,p))[:TOP_K_CANDIDATES]
        return cand

    def evaluate_target_cost(cur, target, remaining):
        route = a_star_cached(cur, target); 
        if route is None:
            route = dijkstra(cur, target)
            if route is None: return float('inf'), None
        cost = len(route)
        sim_pos = target
        rem = list(remaining - {target})
        for _ in range(max(0, LOOKAHEAD-1)):
            if not rem: break
            nxt = min(rem, key=lambda p: adjusted_distance(sim_pos, p, wind_dir))
            cost += adjusted_distance(sim_pos, nxt, wind_dir)
            sim_pos = nxt; rem.remove(nxt)
        return cost, route

    def follow_route(route, cur, collected, path):
        for step in route[1:]:
            path.append(step); cur=step
            if cur in trash_set: collected.add(cur)
        return cur

    collected=set()

    if hotspots:
        groups = build_hotspot_groups(list(trash_set), hotspots, radius=hotspot_radius)
        while True:
            cands=[]
            for h, pts in groups.items():
                remain=[p for p in pts if p not in collected]
                if remain:
                    score = ALPHA_HS*len(remain) - BETA_HS_DIST*distance(current, h)
                    cands.append((h, remain, score))
            if not cands: break
            target_h, remain_pts, _ = max(cands, key=lambda x:x[2])

            remain_set=set(remain_pts)
            while remain_set:
                candidates = directional_candidates(list(remain_set), current)
                best=(float('inf'), None, None)
                for t in candidates:
                    cost, route = evaluate_target_cost(current, t, remain_set)
                    if cost < best[0]: best=(cost,t,route)
                if best[2] is None: break
                current = follow_route(best[2], current, collected, path)
                if best[1] in remain_set: remain_set.remove(best[1])

        leftovers = list(trash_set - collected)
        while leftovers:
            candidates = directional_candidates(leftovers, current)
            best=(float('inf'), None, None); rem_set=set(leftovers)
            for t in candidates:
                cost, route = evaluate_target_cost(current, t, rem_set)
                if cost < best[0]: best=(cost,t,route)
            if best[2] is None: break
            current = follow_route(best[2], current, collected, path)
            if best[1] in leftovers: leftovers.remove(best[1])

        return path[1:]

    # 폴백(핫스팟 미설정)
    remain=set(trash_set)
    while remain:
        candidates = directional_candidates(list(remain), current)
        best=(float('inf'), None, None)
        for t in candidates:
            cost, route = evaluate_target_cost(current, t, remain)
            if cost < best[0]: best=(cost,t,route)
        if best[2] is None: break
        current = follow_route(best[2], current, collected, path)
        remain.discard(best[1])
    return path[1:]

# === 시각화/저장 ===
def plot_route_on_heatmap(H, x_edges, y_edges, route_grid, start_grid, out_png, title):
    plt.figure(figsize=(8,7))
    pos = H[H>0]
    if len(pos)>0:
        vmin = np.percentile(pos, 5); vmax = np.percentile(pos, 95)
        if vmax <= vmin: vmax = vmin * 10
    else:
        vmin, vmax = 1e-3, 1
    plt.imshow(
        H.T, origin='lower', cmap='plasma',
        extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
        aspect='auto', norm=LogNorm(vmin=vmin, vmax=vmax)
    )
    # grid → km
    xs = []; ys=[]
    sx, sy = start_grid
    x0,y0 = grid_to_km(sx, sy, x_edges, y_edges)
    xs.append(x0); ys.append(y0)
    for (gx, gy) in route_grid:
        x,y = grid_to_km(gx, gy, x_edges, y_edges)
        xs.append(x); ys.append(y)
    plt.plot(xs, ys, '-o', markersize=3, linewidth=1.5, label='Hybrid Route')
    plt.scatter([xs[0]],[ys[0]], c='white', s=50, edgecolors='black', label='Start')
    plt.title(title); plt.xlabel('X (km)'); plt.ylabel('Y (km)')
    plt.legend(loc='upper left'); plt.tight_layout()
    plt.savefig(out_png, dpi=180); plt.close()

def export_route_csv_geojson(route_grid, start_grid, x_edges, y_edges, out_csv, out_geojson, speed_kmph=None):
    # CSV
    rows=[]; t_cum_h=0.0; cum_km=0.0; last_xy_km = grid_to_km(*start_grid, x_edges, y_edges)
    for i,(gx,gy) in enumerate(route_grid, start=1):
        xy_km = grid_to_km(gx, gy, x_edges, y_edges)
        seg = math.hypot(xy_km[0]-last_xy_km[0], xy_km[1]-last_xy_km[1])
        cum_km += seg
        eta=None
        if speed_kmph and speed_kmph>0:
            t_cum_h += seg / speed_kmph; eta=t_cum_h
        rows.append({"order":i, "grid_x":gx, "grid_y":gy, "x_km":xy_km[0], "y_km":xy_km[1],
                     "segment_dist_km":seg, "cum_dist_km":cum_km, "eta_hour_from_start":eta})
        last_xy_km = xy_km
    pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8-sig")

    # GeoJSON
    coords=[grid_to_km(*start_grid, x_edges, y_edges)]
    for (gx,gy) in route_grid:
        coords.append(grid_to_km(gx, gy, x_edges, y_edges))
    gj = {
        "type":"FeatureCollection",
        "features":[
            {"type":"Feature","geometry":{"type":"LineString","coordinates":[[float(x),float(y)] for (x,y) in coords]},
             "properties":{"name":"Hybrid Trash Route (planar km coords)"}},
            {"type":"Feature","geometry":{"type":"MultiPoint","coordinates":[[float(x),float(y)] for (x,y) in coords[1:]]},
             "properties":{"name":"Visited grid centers"}}
        ]
    }
    with open(out_geojson, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False, indent=2)

# (옵션) 위경도 변환
def export_wgs84_from_km_geojson(in_geojson, out_geojson, out_csv, lat0=35.0, lon0=129.3, xlsx_path=XLSX_PATH):
    def parse_blocks_latlon_from_excel(path):
        try: df = pd.read_excel(path, sheet_name=0, header=None)
        except Exception: return []
        pts=[]; i=0
        while i<len(df):
            if str(df.iloc[i,0]).strip()=='위도':
                lat = pd.to_numeric(df.iloc[i,1], errors='coerce')
                lon = pd.to_numeric(df.iloc[i+1,1], errors='coerce') if i+1<len(df) else np.nan
                if not pd.isna(lat) and not pd.isna(lon): pts.append((float(lat), float(lon)))
                i+=7
            else: i+=1
        return pts
    if os.path.exists(xlsx_path):
        pts = parse_blocks_latlon_from_excel(xlsx_path)
        if pts:
            lat0 = float(np.mean([p[0] for p in pts])); lon0=float(np.mean([p[1] for p in pts]))
    lon_per_km = 1.0/(111.0*math.cos(math.radians(lat0))); lat_per_km=1.0/111.0

    gj=json.load(open(in_geojson,'r',encoding='utf-8'))
    line=[f for f in gj["features"] if f["geometry"]["type"]=="LineString"][0]
    coords_km=line["geometry"]["coordinates"]
    lats=[lat0 + (y_km*lat_per_km) for (x_km,y_km) in coords_km]
    lons=[lon0 + (x_km*lon_per_km) for (x_km,y_km) in coords_km]
    gj_wgs={
        "type":"FeatureCollection",
        "features":[
            {"type":"Feature","geometry":{"type":"LineString","coordinates":[[lons[i],lats[i]] for i in range(len(lats))]},
             "properties":{"name":"Hybrid Trash Route (WGS84)",
                           "origin_ref":{"lat0":lat0,"lon0":lon0,"note":"equirectangular approx"}}}
        ]
    }
    with open(out_geojson,"w",encoding="utf-8") as f: json.dump(gj_wgs,f,ensure_ascii=False,indent=2)
    rows=[{"order":i+1,"lat":lats[i],"lon":lons[i]} for i in range(len(lats))]
    pd.DataFrame(rows).to_csv(out_csv,index=False,encoding="utf-8-sig")

# ===================== 메인 =====================
def main():
    print("Step 6 (Hybrid) ▶ 경로 생성 시작")

    # 1) 공통 그리드/엣지
    x_edges, y_edges, bins = load_history_grid(os.path.join(HIST_DIR, "history_summary.json"))

    # 2) 예측 히트맵 로드 → 50x50으로 재매핑
    H_pred_full = load_forecast_heatmap(FORE_DIR)        # (bins-1, bins-1)
    H_pred_grid = remap_heatmap_to_grid(H_pred_full, out_size=GRID_SIZE)

    # 3) 핫스팟 로드 (km 좌표)
    hotspots = load_hotspots(FINAL_DIR, TOP_K_HOTSPOTS, MIN_VALUE_THRESH)
    # km → grid 로 변환
    hs_grid=[]
    for h in hotspots:
        gx = int(np.interp(h['x'], [x_edges[0], x_edges[-1]], [0, GRID_SIZE]))
        gy = int(np.interp(h['y'], [y_edges[0], y_edges[-1]], [0, GRID_SIZE]))
        gx=_clamp(gx,0,GRID_SIZE-1); gy=_clamp(gy,0,GRID_SIZE-1)
        hs_grid.append((gx, gy))

    # 4) 풍향/풍속 (예측 엑셀) → hybrid 비용에 반영
    if os.path.exists(XLSX_PATH):
        wind_dir_deg, mean_wspd = get_daily_wind_direction_from_excel(XLSX_PATH)
    else:
        wind_dir_deg, mean_wspd = 0.0, 0.0
    print(f"  - wind_dir(deg)={wind_dir_deg:.1f}, mean_wspd={mean_wspd:.2f} m/s")

    # 5) trash field 만들기: 예측 히트맵 비례 샘플 + 핫스팟 주변 추가
    trash_positions, obstacles = sample_trash_from_heatmap_and_hotspots(H_pred_grid, hotspots_any=None)
    trash_positions = add_hotspot_bias(trash_positions, hs_grid, HOTSPOT_BONUS_EACH, GRID_SIZE)

    # 6) 시작점 설정
    if START_MODE == 'fixed':
        start_grid = tuple(START_GRID_XY)
    else:  # 가장 강한 핫스팟 근처에서 출발
        start_grid = hs_grid[0] if hs_grid else (0,0)

    # 7) Hybrid(Hotspot) 경로 생성
    env = {'풍향(deg)': wind_dir_deg}
    hotspot_radius = HOTSPOT_RADIUS_GRID or max(4, int(0.12 * GRID_SIZE))
    route_grid = hybrid_algorithm(
        start=start_grid,
        trash_positions=trash_positions,
        obstacle_positions=obstacles,
        env=env,
        hotspots=hs_grid if hs_grid else None,
        hotspot_radius=hotspot_radius,
        alpha=ALPHA_HS, beta=BETA_HS_DIST,
        lookahead=LOOKAHEAD,
        dir_dot_threshold=DIR_DOT_THRESHOLD,
        candidate_dist_filter=CAND_DIST_FILTER,
        top_k_candidates=TOP_K_CANDIDATES,
        grid_size=GRID_SIZE
    )

    # 8) 저장/시각화 (km 좌표로 변환 후)
    csv_path = os.path.join(ROUTE_DIR, "route_hybrid_waypoints.csv")
    geo_path = os.path.join(ROUTE_DIR, "route_hybrid.geojson")
    png_path = os.path.join(ROUTE_DIR, "route_hybrid.png")

    export_route_csv_geojson(route_grid, start_grid, x_edges, y_edges, csv_path, geo_path, speed_kmph=VESSEL_SPEED_KMPH)
    plot_route_on_heatmap(H_pred_full, x_edges, y_edges, route_grid, start_grid, png_path,
                          title="2025-10-13 Hybrid Route on Forecast Heatmap")

    print("Step 6 (Hybrid) ✅ 완료")
    print(f"  - Waypoints: {csv_path}")
    print(f"  - GeoJSON  : {geo_path}")
    print(f"  - Plot     : {png_path}")

    # 9) (옵션) 위경도 결과 추가 저장
    if EXPORT_WGS84:
        wgs_gj = os.path.join(ROUTE_DIR, "route_hybrid_wgs84.geojson")
        wgs_cs = os.path.join(ROUTE_DIR, "route_hybrid_wgs84.csv")
        export_wgs84_from_km_geojson(geo_path, wgs_gj, wgs_cs)
        print(f"  - WGS84 GeoJSON: {wgs_gj}")
        print(f"  - WGS84 CSV   : {wgs_cs}")

if __name__ == "__main__":
    main()
