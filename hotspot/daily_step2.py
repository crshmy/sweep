# -*- coding: utf-8 -*-
"""
Step 2 (Excel 개선+진단): 2025-10-13 예측 체류 히트맵 생성 + 블록별 이동거리/궤적 저장
- Step 1의 공통 격자(history_summary.json)에 정합
- 엑셀(대한해협.xlsx) 블록을 '라벨 매칭'으로 robust 파싱
- 개선:
  1) 체류가중치 안정화(속도 eps 상향 + 가중 상한)
  2) 구간 히트맵: 선분을 N_SUB등분 샘플링해 누적
  3) 시각화 auto_crop 옵션
  4) ★ 블록별 이동거리 계산/CSV 저장 + 궤적 라인플롯 저장(블록별/전체)
출력:
  ./daily_results_forecast_251013/H_pred.npy, H_pred.png
  ./daily_results_forecast_251013/intervals/*.png  (3시간 간격 8개)
  ./daily_results_forecast_251013/forecast_summary.json
  ./daily_results_forecast_251013/block_stats.csv
  ./daily_results_forecast_251013/tracks/track_block_###.png
  ./daily_results_forecast_251013/tracks/track_all_blocks.png
"""

import os, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# ----------------- 경로 -----------------
XLSX_PATH  = r"./data/대한해협.xlsx"
HIST_DIR   = './daily_results_hotspot_251013'      # Step 1 출력 폴더
RESULT_DIR = './daily_results_forecast_251013'
INTERVAL_DIR = os.path.join(RESULT_DIR, 'intervals')
TRACK_DIR    = os.path.join(RESULT_DIR, 'tracks')
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(INTERVAL_DIR, exist_ok=True)
os.makedirs(TRACK_DIR, exist_ok=True)

# ----------------- 날짜/파라미터 -----------------
target_year, month, day = 2025, 10, 13

selected_trash = 'Light Small Trash'
trash_types = {
    'Light Small Trash': {'alpha': 0.05, 'beta': 0.02},
    'Light Medium Trash': {'alpha': 0.04, 'beta': 0.03},
    'Heavy Small Trash': {'alpha': 0.03, 'beta': 0.04},
    'Heavy Medium Trash': {'alpha': 0.02, 'beta': 0.05},
    'Heavy Large Trash': {'alpha': 0.01, 'beta': 0.06},
}
alpha = trash_types[selected_trash]['alpha']
beta  = trash_types[selected_trash]['beta']

# === 체류가중치 안정화 파라미터 ===
MAX_SPEED_EPS = 0.1
WEIGHT_CLIP   = 50.0

# === 구간 선분 샘플링 ===
N_SUB = 12

# ----------------- 방향어→각도 매핑 -----------------
DIR2DEG = {
    '북': 0, '북북동': 22.5, '북동': 45, '동북동': 67.5,
    '동': 90, '동남동': 112.5, '남동': 135, '남남동': 157.5,
    '남': 180, '남남서': 202.5, '남서': 225, '서남서': 247.5,
    '서': 270, '서북서': 292.5, '북서': 315, '북북서': 337.5,
    '북동풍': 45, '남동풍': 135, '남서풍': 225, '북서풍': 315,
    '동풍': 90, '서풍': 270, '남풍': 180, '북풍': 0,
}

def to_deg(val):
    if pd.isna(val): return np.nan
    s = str(val).strip()
    if s in DIR2DEG: return DIR2DEG[s]
    if '/' in s:  # 혼합 표기 평균
        parts = [p.strip() for p in s.split('/')]
        vals = [DIR2DEG.get(p, np.nan) for p in parts]
        if all([not np.isnan(v) for v in vals]): return float(np.mean(vals))
    try:
        return float(s)  # 숫자면 그대로
    except:
        return np.nan

# ----------------- 공통 격자 로드 -----------------
def load_history_grid():
    summ_fp = os.path.join(HIST_DIR, 'history_summary.json')
    if not os.path.exists(summ_fp):
        raise FileNotFoundError(f'Step 1 요약 파일이 필요합니다: {summ_fp}')
    with open(summ_fp, 'r', encoding='utf-8') as f:
        s = json.load(f)
    x_min, x_max = s['x_range']
    y_min, y_max = s['y_range']
    bins = int(s['bins'])
    x_edges = np.linspace(x_min, x_max, bins)
    y_edges = np.linspace(y_min, y_max, bins)
    return x_edges, y_edges, bins

# ----------------- 라벨 정규화/검색 -----------------
def _norm_label(x):
    if pd.isna(x): return ''
    s = str(x).strip().replace(' ', '')
    s = (s.replace(':','').replace('：','')
           .replace('(m/s)','').replace('(m)','')
           .replace('MOSE.HF','').replace('유의파고(MOSE.HF)','유의파고'))
    return s

def _find_next_row(df, start_idx, want_label):
    want = _norm_label(want_label)
    for r in range(start_idx, len(df)):
        if _norm_label(df.iloc[r, 0]) == want:
            return r
    return -1

# ----------------- Excel 파서 (라벨 매칭) -----------------
def parse_blocks_from_excel(path):
    df = pd.read_excel(path, sheet_name=0, header=None)
    blocks = []
    i, n = 0, len(df)

    while i < n:
        if _norm_label(df.iloc[i, 0]) != '위도':
            i += 1
            continue

        lat = pd.to_numeric(df.iloc[i, 1], errors='coerce')
        j_lon = i+1 if _norm_label(df.iloc[i+1,0]) == '경도' else _find_next_row(df, i+1, '경도')
        if j_lon == -1:
            i += 1; continue
        lon = pd.to_numeric(df.iloc[j_lon, 1], errors='coerce')

        base = j_lon + 1
        r_time = _find_next_row(df, base, '시간')
        r_wdir = _find_next_row(df, base, '풍향')
        r_wspd = _find_next_row(df, base, '풍속')
        r_pdir = _find_next_row(df, base, '파향')
        r_whgt = _find_next_row(df, base, '유의파고')
        if min(r_time, r_wdir, r_wspd, r_pdir, r_whgt) == -1:
            nxt = _find_next_row(df, i+1, '위도')
            i = nxt if nxt != -1 else n
            continue

        times = pd.to_numeric(df.iloc[r_time, 1:9], errors='coerce').tolist()
        wdir  = [to_deg(v) for v in df.iloc[r_wdir, 1:9].tolist()]
        wspd  = pd.to_numeric(df.iloc[r_wspd, 1:9], errors='coerce').fillna(0).tolist()
        pdir  = [to_deg(v) for v in df.iloc[r_pdir, 1:9].tolist()]
        whgt  = pd.to_numeric(df.iloc[r_whgt, 1:9], errors='coerce').fillna(0).tolist()

        def fix_len(a, fill=0.0, allow_nan=False):
            a = list(a)
            if len(a) < 8: a += ([np.nan] if allow_nan else [fill])*(8-len(a))
            return a[:8]

        times = [int(x) if not pd.isna(x) else 0 for x in fix_len(times, 0)]
        wdir  = [float(x) if not pd.isna(x) else np.nan for x in fix_len(wdir, allow_nan=True)]
        wspd  = [float(x) for x in fix_len(wspd, 0.0)]
        pdir  = [float(x) if not pd.isna(x) else np.nan for x in fix_len(pdir, allow_nan=True)]
        whgt  = [float(x) for x in fix_len(whgt, 0.0)]

        blocks.append({
            "lat": float(lat) if not pd.isna(lat) else None,
            "lon": float(lon) if not pd.isna(lon) else None,
            "times": times,
            "wind_dir_deg": wdir,
            "wind_speed": wspd,
            "wave_dir_deg": pdir,
            "wave_height": whgt
        })

        nxt = _find_next_row(df, r_whgt+1, '위도')
        i = nxt if nxt != -1 else n

    return blocks

# ----------------- 모델 변환/히스토그램 -----------------
def to_xy(block):
    wind_speed = np.array(block["wind_speed"], dtype=float)
    wind_dir   = np.array(block["wind_dir_deg"], dtype=float)
    wave_h     = np.array(block["wave_height"], dtype=float)
    wave_dir   = np.array(block["wave_dir_deg"], dtype=float)

    X = alpha * wind_speed * np.cos(np.radians(wind_dir + 180.0)) + \
        beta  * wave_h     * np.cos(np.radians(wave_dir))
    Y = alpha * wind_speed * np.sin(np.radians(wind_dir + 180.0)) + \
        beta  * wave_h     * np.sin(np.radians(wave_dir))

    X = np.nan_to_num(X, nan=0.0); Y = np.nan_to_num(Y, nan=0.0)
    x = np.cumsum(X); y = np.cumsum(Y)
    return x, y

def residence_histogram(x, y, x_edges, y_edges):
    dx = np.diff(x, prepend=x[0]); dy = np.diff(y, prepend=y[0])
    speed = np.sqrt(dx*dx + dy*dy)
    w = 1.0 / np.maximum(speed, MAX_SPEED_EPS)
    w = np.clip(w, 0, WEIGHT_CLIP)
    H, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges], weights=w)
    return H

# ----------------- 가시화 -----------------
def save_heatmap_png(H, x_edges, y_edges, title, outpng, auto_crop=False):
    xmin, xmax = x_edges[0], x_edges[-1]
    ymin, ymax = y_edges[0], y_edges[-1]

    if auto_crop and np.any(H > 0):
        nz = np.argwhere(H > 0)
        i0, j0 = nz.min(axis=0); i1, j1 = nz.max(axis=0)
        i0 = max(i0-1, 0); j0 = max(j0-1, 0)
        i1 = min(i1+2, len(x_edges)-1); j1 = min(j1+2, len(y_edges)-1)
        xmin, xmax = x_edges[i0], x_edges[i1]
        ymin, ymax = y_edges[j0], y_edges[j1]

    plt.figure(figsize=(7,6))
    pos = H[H>0]
    if len(pos)>0:
        vmin = np.percentile(pos, 5); vmax = np.percentile(pos, 95)
        if vmax <= vmin: vmax = vmin * 10
    else:
        vmin, vmax = 1e-3, 1
    plt.imshow(
        H.T, origin='lower', cmap='plasma',
        extent=[xmin, xmax, ymin, ymax],
        aspect='auto', norm=LogNorm(vmin=vmin, vmax=vmax)
    )
    plt.colorbar(label='Residence time (weighted)')
    plt.title(title); plt.xlabel('X (km)'); plt.ylabel('Y (km)')
    plt.tight_layout(); plt.savefig(outpng); plt.close()

def save_track_plot(xs, ys, title, outpng):
    plt.figure(figsize=(6,6))
    plt.plot(xs, ys, '-o', linewidth=2)
    plt.axis('equal')
    plt.grid(True, alpha=0.3)
    plt.title(title)
    plt.xlabel('X (km)'); plt.ylabel('Y (km)')
    plt.tight_layout(); plt.savefig(outpng); plt.close()

# ----------------- 메인 -----------------
def main():
    print('Step 2 (Excel, 진단 포함) ▶ 예측 히트맵 생성 시작')

    # 1) 공통 격자 로드
    x_edges, y_edges, bins = load_history_grid()

    # 2) Excel 파싱 → 블록 리스트
    blocks = parse_blocks_from_excel(XLSX_PATH)
    if not blocks:
        print('  !! 엑셀에서 블록을 찾지 못했습니다.')
        return
    print(f'  - 블록(지점) 수: {len(blocks)} (각 8개 시각)')

    # 3) 하루(H_pred) 누적 + 구간맵(8개) + 진단(블록별 이동거리/궤적)
    H_pred = np.zeros((bins-1, bins-1), dtype=float)
    interval_maps = [np.zeros_like(H_pred) for _ in range(8)]  # [0-3]..[21-24]
    stats_rows = []
    all_tracks = []  # 전체 트랙 오버레이용

    labels = [(0,3),(3,6),(6,9),(9,12),(12,15),(15,18),(18,21),(21,24)]

    for idx, b in enumerate(blocks, start=1):
        x, y = to_xy(b)
        H_pred += residence_histogram(x, y, x_edges, y_edges)

        # 구간(0-3..18-21): 선분 등분 샘플링
        for k in range(7):
            x0, y0 = x[k], y[k]
            dx, dy = x[k+1]-x[k], y[k+1]-y[k]
            t = np.linspace(0, 1, N_SUB+1)
            xs = x0 + t*dx
            ys = y0 + t*dy
            interval_maps[k] += residence_histogram(xs, ys, x_edges, y_edges)
        # 21-24 구간은 정지 가정

        # ---- 진단: 이동누적거리 + 궤적 저장 ----
        dx = np.diff(x); dy = np.diff(y)
        dist = float(np.sqrt(dx*dx + dy*dy).sum())
        print(f'  · block #{idx:03d}  이동누적거리: {dist:.4f} (모델 좌표 단위)')
        stats_rows.append({
            "block_id": idx,
            "lat": b.get("lat"), "lon": b.get("lon"),
            "dist_units": dist,
            "mean_wind_speed": float(np.nanmean(b["wind_speed"])),
            "mean_wave_height": float(np.nanmean(b["wave_height"]))
        })
        # 블록별 궤적 플롯
        save_track_plot(x, y,
                        f'Block #{idx:03d} Track (2025-10-13)',
                        os.path.join(TRACK_DIR, f'track_block_{idx:03d}.png'))
        all_tracks.append((x, y))

    # 전체 궤적 오버레이
    plt.figure(figsize=(7,7))
    for (x, y) in all_tracks:
        plt.plot(x, y, '-o', linewidth=1.5, alpha=0.7)
    plt.axis('equal'); plt.grid(True, alpha=0.3)
    plt.title('All Blocks Tracks (2025-10-13)')
    plt.xlabel('X (km)'); plt.ylabel('Y (km)')
    plt.tight_layout(); plt.savefig(os.path.join(TRACK_DIR, 'track_all_blocks.png')); plt.close()

    # 4) 저장/가시화 (auto_crop=True로 보기 좋게)
    np.save(os.path.join(RESULT_DIR, 'H_pred.npy'), H_pred)
    save_heatmap_png(
        H_pred, x_edges, y_edges,
        f'Forecast Hotspot Heatmap (2025-10-13, {selected_trash})',
        os.path.join(RESULT_DIR, 'H_pred.png'),
        auto_crop=True
    )
    # 구간 PNG
    for idx, Hseg in enumerate(interval_maps):
        h0, h1 = labels[idx]
        outpng = os.path.join(INTERVAL_DIR, f'H_pred_{h0:02d}_{h1:02d}.png')
        save_heatmap_png(Hseg, x_edges, y_edges,
                         f'Forecast Heatmap {h0:02d}-{h1:02d}',
                         outpng, auto_crop=True)

    # 5) 요약/통계 저장
    summary = {
        "alpha": alpha, "beta": beta, "bins": int(bins),
        "grid":{"x_min":float(x_edges[0]),"x_max":float(x_edges[-1]),
                "y_min":float(y_edges[0]),"y_max":float(y_edges[-1])},
        "blocks": len(blocks),
        "intervals": [{"start":a,"end":b,"nonzero":int((m>0).sum())}
                      for (a,b),m in zip(labels, interval_maps)],
        "params":{"MAX_SPEED_EPS": MAX_SPEED_EPS, "WEIGHT_CLIP": WEIGHT_CLIP, "N_SUB": N_SUB}
    }
    with open(os.path.join(RESULT_DIR, 'forecast_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 블록별 통계 CSV
    pd.DataFrame(stats_rows).to_csv(os.path.join(RESULT_DIR, 'block_stats.csv'), index=False, encoding='utf-8-sig')

    print('Step 2 (Excel, 진단 포함) ✅ 완료')
    print(f'  - {RESULT_DIR}/H_pred.npy, H_pred.png, forecast_summary.json, block_stats.csv')
    print(f'  - {INTERVAL_DIR}/*.png, {TRACK_DIR}/track_block_###.png, track_all_blocks.png')

if __name__ == '__main__':
    main()
