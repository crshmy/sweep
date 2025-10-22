# -*- coding: utf-8 -*-
"""
Step 3: 기본 가중(0.5:0.5) 블렌딩 → 최종 핫스팟 생성
입력:
  - ./daily_results_hotspot_251013/H_hist.npy
  - ./daily_results_forecast_251013/H_pred.npy
  - ./daily_results_hotspot_251013/history_summary.json
출력:
  - ./daily_results_final_251013/H_final.npy, H_final.png
  - ./daily_results_final_251013/H_smooth.npy, H_smooth.png
  - ./daily_results_final_251013/hotspots.json  (Top-K)
"""

import os, json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from scipy.ndimage import gaussian_filter
from skimage.feature import peak_local_max

HIST_DIR   = './daily_results_hotspot_251013'
FORE_DIR   = './daily_results_forecast_251013'
FINAL_DIR  = './daily_results_final_251013'
os.makedirs(FINAL_DIR, exist_ok=True)

# ===== 시각화 공통 =====
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

# ===== 메인 =====
def main():
    # 1) 공통 격자 로드
    with open(os.path.join(HIST_DIR, 'history_summary.json'), 'r', encoding='utf-8') as f:
        summ = json.load(f)
    bins = int(summ['bins'])
    x_edges = np.linspace(summ['x_range'][0], summ['x_range'][1], bins)
    y_edges = np.linspace(summ['y_range'][0], summ['y_range'][1], bins)

    # 2) H_hist / H_pred 로드 (크기 체크)
    H_hist = np.load(os.path.join(HIST_DIR, 'H_hist.npy'))
    H_pred = np.load(os.path.join(FORE_DIR, 'H_pred.npy'))
    if H_hist.shape != H_pred.shape:
        raise ValueError(f'shape mismatch: H_hist {H_hist.shape} vs H_pred {H_pred.shape}')

    # 3) 기본 가중 블렌딩 (0.5 : 0.5)
    H_final = 0.5 * H_hist + 0.5 * H_pred
    np.save(os.path.join(FINAL_DIR, 'H_final.npy'), H_final)
    save_heatmap_png(H_final, x_edges, y_edges,
                     'Final Hotspot Heatmap (0.5 Hist + 0.5 Pred)',
                     os.path.join(FINAL_DIR, 'H_final.png'), auto_crop=True)

    # 4) 스무딩 후 핫스팟 추출
    sigma = 1.5           # 필요시 1.0~2.0 사이 튜닝
    H_s = gaussian_filter(H_final, sigma=sigma)
    np.save(os.path.join(FINAL_DIR, 'H_smooth.npy'), H_s)
    save_heatmap_png(H_s, x_edges, y_edges,
                     f'Final Hotspot Heatmap (Smoothed, σ={sigma})',
                     os.path.join(FINAL_DIR, 'H_smooth.png'), auto_crop=True)

    # 5) Top-K 핫스팟
    K = 20                # 필요시 K 조정
    min_dist = 3          # 격자 최소 간격
    coords = peak_local_max(H_s, num_peaks=K, min_distance=min_dist)
    hotspots = []
    for (i, j) in coords:
        # 셀 중심좌표로 변환
        x_center = (x_edges[i] + x_edges[i+1]) / 2.0
        y_center = (y_edges[j] + y_edges[j+1]) / 2.0
        hotspots.append({
            "x": float(x_center),
            "y": float(y_center),
            "value": float(H_s[i, j])
        })

    with open(os.path.join(FINAL_DIR, 'hotspots.json'), 'w', encoding='utf-8') as f:
        json.dump({"K": K, "sigma": sigma, "min_distance": min_dist,
                   "hotspots": hotspots}, f, ensure_ascii=False, indent=2)

    print('Step 3 ✅ 완료')
    print(f'  - {FINAL_DIR}/H_final.npy, H_final.png')
    print(f'  - {FINAL_DIR}/H_smooth.npy, H_smooth.png')
    print(f'  - {FINAL_DIR}/hotspots.json (Top-{K})')

if __name__ == '__main__':
    import numpy as np
    main()
