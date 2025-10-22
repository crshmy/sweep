# -*- coding: utf-8 -*-
"""
Step 1: 2022/2023/2024-10-13 과거 체류시간 히트맵 표준화 생성
- 동일 격자/동일 파라미터로 연도별 히트맵 생성 후 평균(H_hist)
- 출력: H_hist.npy, H_hist.png, 연도별 PNG, history_summary.json
"""

import os, json, math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# ----------------- 설정 -----------------
DATA_DIR   = './data'
RESULT_DIR = './daily_results_hotspot_251013'
os.makedirs(RESULT_DIR, exist_ok=True)

years_hist = [2022, 2023, 2024]
month, day = 10, 13
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

BINS = 140              # 격자 해상도(필요 시 100~200 사이 조정)
MAX_SPEED_EPS = 1e-3    # 0 나눗셈 방지

# ----------------- 유틸 -----------------
def load_month_csv(year:int, month:int):
    fn = f'{year}년 {month:02d}월 대한해협 해양관측부이.csv'
    fp = os.path.join(DATA_DIR, fn)
    df = pd.read_csv(fp, encoding='cp949', sep='\t', skiprows=3)
    if '관측시간' not in df.columns:
        raise ValueError(f'관측시간 컬럼 없음: {fp}')
    df['관측시간'] = pd.to_datetime(df['관측시간'])
    req = ['풍속(m/s)','풍향(deg)','유의파고(MOSE.HF)(m)','파향(deg)']
    for c in req:
        if c not in df.columns:
            raise ValueError(f'필수 컬럼 없음: {c} in {fp}')
    return df

def subset_day(df:pd.DataFrame, month:int, day:int):
    d = df[(df['관측시간'].dt.month==month) & (df['관측시간'].dt.day==day)].copy()
    return d.sort_values('관측시간')

def compute_xy(df:pd.DataFrame, alpha:float, beta:float):
    # 풍속/방향/파고/파향 숫자화
    wind_speed = pd.to_numeric(df['풍속(m/s)'], errors='coerce').fillna(0)
    wind_dir   = pd.to_numeric(df['풍향(deg)'], errors='coerce').fillna(0)
    wave_h     = pd.to_numeric(df['유의파고(MOSE.HF)(m)'], errors='coerce').fillna(0)
    wave_dir   = pd.to_numeric(df['파향(deg)'], errors='coerce').fillna(0)

    # 바람은 오는 방향 → +180, 파향은 진행방향 유지
    X = alpha * wind_speed * np.cos(np.radians(wind_dir + 180)) + \
        beta  * wave_h     * np.cos(np.radians(wave_dir))
    Y = alpha * wind_speed * np.sin(np.radians(wind_dir + 180)) + \
        beta  * wave_h     * np.sin(np.radians(wave_dir))

    x = np.cumsum(X.values)
    y = np.cumsum(Y.values)
    return x, y

def extent_from_many(xys):
    xs = np.concatenate([xy[0] for xy in xys]); ys = np.concatenate([xy[1] for xy in xys])
    x_min, x_max = float(xs.min()), float(xs.max())
    y_min, y_max = float(ys.min()), float(ys.max())
    # 여유 여백(5%) 추가
    dx = (x_max - x_min) * 0.05; dy = (y_max - y_min) * 0.05
    return x_min - dx, x_max + dx, y_min - dy, y_max + dy

def residence_heatmap_on_grid(x, y, x_edges, y_edges):
    # 속도 역수 가중(체류 근사)
    dx = np.diff(x, prepend=x[0]); dy = np.diff(y, prepend=y[0])
    speed = np.sqrt(dx*dx + dy*dy)
    w = 1.0 / np.maximum(speed, MAX_SPEED_EPS)
    H, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges], weights=w)
    return H

def save_heatmap_png(H, x_edges, y_edges, title, outpng):
    plt.figure(figsize=(7,6))
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
    plt.colorbar(label='Residence time (weighted)')
    plt.title(title); plt.xlabel('X (km)'); plt.ylabel('Y (km)')
    plt.tight_layout(); plt.savefig(outpng); plt.close()

# ----------------- 메인 -----------------
def main():
    print('Step 1 ▶ 과거 10/13 히트맵 생성 시작')
    peryear_xy = {}
    for y in years_hist:
        df = load_month_csv(y, month)
        d  = subset_day(df, month, day)
        if d.empty:
            print(f'  - {y}-10-13 데이터 없음(스킵)')
            continue
        x, yv = compute_xy(d, alpha, beta)
        peryear_xy[y] = (x, yv)
        print(f'  - {y}: 표본 {len(x)}')

    if not peryear_xy:
        print('  !! 모든 연도 데이터가 비어 있음'); return

    # 공통 그리드(연도 전체 범위 기준)
    x_min, x_max, y_min, y_max = extent_from_many(list(peryear_xy.values()))
    x_edges = np.linspace(x_min, x_max, BINS)
    y_edges = np.linspace(y_min, y_max, BINS)

    # 연도별 히트맵 + PNG
    H_list = []
    summary = {"bins": BINS, "alpha": alpha, "beta": beta,
               "x_range":[x_min,x_max], "y_range":[y_min,y_max], "years":{}}

    for y,(x,yv) in peryear_xy.items():
        H = residence_heatmap_on_grid(x, yv, x_edges, y_edges)
        H_list.append(H)
        save_heatmap_png(H, x_edges, y_edges, f'{y}-10-13 Residence Heatmap', os.path.join(RESULT_DIR, f'H_{y}.png'))
        # 간단 통계
        dx = np.diff(x, prepend=x[0]); dy = np.diff(yv, prepend=yv[0])
        dist = float(np.sqrt(dx*dx + dy*dy).sum())
        summary["years"][str(y)] = {"samples": int(len(x)), "cum_distance_units": dist}

    # 과거 평균 히트맵
    H_hist = np.mean(np.stack(H_list, axis=0), axis=0)
    np.save(os.path.join(RESULT_DIR, 'H_hist.npy'), H_hist)
    save_heatmap_png(H_hist, x_edges, y_edges, 'Historical Hotspot Heatmap (2022+2023+2024, 10-13)',
                     os.path.join(RESULT_DIR, 'H_hist.png'))

    # 요약 저장
    summary["H_hist_nonzero"] = int((H_hist>0).sum())
    with open(os.path.join(RESULT_DIR, 'history_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print('Step 1 ✅ 완료')
    print(f'  - {RESULT_DIR}/H_hist.npy, H_hist.png, 연도별 H_*.png, history_summary.json 생성')

if __name__ == '__main__':
    main()
