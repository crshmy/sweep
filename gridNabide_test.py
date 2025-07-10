import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# ✅ 설정
DATA_DIR = './data'
RESULT_DIR = './results_trash_combined_allinone'
os.makedirs(RESULT_DIR, exist_ok=True)

years = [2022, 2023, 2024]

trash_types = {
    '가벼운 소형 쓰레기': {'alpha': 0.05, 'beta': 0.02},
    '가벼운 중형 쓰레기': {'alpha': 0.04, 'beta': 0.03},
    '무거운 소형 쓰레기': {'alpha': 0.03, 'beta': 0.04},
    '무거운 중형 쓰레기': {'alpha': 0.02, 'beta': 0.05},
    '무거운 대형 쓰레기': {'alpha': 0.01, 'beta': 0.06},
}
selected_trash = '가벼운 소형 쓰레기'
alpha = trash_types[selected_trash]['alpha']
beta = trash_types[selected_trash]['beta']

color_merge_rules = {
    ('#92cbff', '#92cbff'): '#92cbff',
    ('#92cbff', '#fbfdec'): '#fbfdec',
    ('#92cbff', '#e1e036'): '#e1e036',
    ('#92cbff', '#feb24c'): '#feb24c',
    ('#92cbff', '#fd8d3c'): '#fd8d3c',
    ('#92cbff', '#f03b20'): '#f03b20',
    ('#fbfdec', '#fbfdec'): '#fbfdec',
    ('#fbfdec', '#e1e036'): '#e1e036',
    ('#fbfdec', '#feb24c'): '#feb24c',
    ('#fbfdec', '#fd8d3c'): '#fd8d3c',
    ('#fbfdec', '#f03b20'): '#f03b20',
    ('#e1e036', '#e1e036'): '#dbc328',
    ('#e1e036', '#feb24c'): '#feb24c',
    ('#e1e036', '#fd8d3c'): '#fd8d3c',
    ('#e1e036', '#f03b20'): '#f03b20',
    ('#feb24c', '#feb24c'): '#fd8d3c',
    ('#feb24c', '#fd8d3c'): '#fd8d3c',
    ('#feb24c', '#f03b20'): '#f03b20',
    ('#fd8d3c', '#fd8d3c'): '#ed5757',
    ('#fd8d3c', '#f03b20'): '#ed5757',
    ('#f03b20', '#f03b20'): '#f03b20',
}
def rgba_to_hex(rgba):
    rgb = tuple(int(round(255 * c)) for c in rgba[:3])
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def load_data(year, month):
    filename = f'{year}년 {month:02d}월 대한해협 해양관측부이.csv'
    filepath = os.path.join(DATA_DIR, filename)
    try:
        df = pd.read_csv(filepath, encoding='euc-kr', sep='\t', skiprows=3)
        print(f'✅ {filename} 불러오기 완료')
        return df
    except Exception as e:
        print(f'❗ 파일 로딩 실패: {filepath}, 에러: {e}')
        return None

def process_month(month):
    all_x, all_y = [], []

    for year in years:
        df = load_data(year, month)
        if df is None:
            continue

        # ✅ 컬럼명 자동 확인 + 방어 코드
        required_cols = ['풍속(m/s)', '풍향(deg)', '유의파고(MOSE.HF)(m)', '파향(deg)']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            print(f'⚠️ {year}년 {month}월: 누락된 컬럼: {missing}')
            continue  # 다음으로 넘어감

        wind_speed = pd.to_numeric(df['풍속(m/s)'], errors='coerce').fillna(0)
        wind_dir = pd.to_numeric(df['풍향(deg)'], errors='coerce').fillna(0)
        wave_height = pd.to_numeric(df['유의파고(MOSE.HF)(m)'], errors='coerce').fillna(0)
        wave_dir = pd.to_numeric(df['파향(deg)'], errors='coerce').fillna(0)

        X = (alpha * wind_speed * np.cos(np.radians(wind_dir + 180))) + \
            (beta * wave_height * np.cos(np.radians(wave_dir)))
        Y = (alpha * wind_speed * np.sin(np.radians(wind_dir + 180))) + \
            (beta * wave_height * np.sin(np.radians(wave_dir)))

        x = np.cumsum(X)
        y = np.cumsum(Y)

        all_x.extend(x)
        all_y.extend(y)

    if len(all_x) < 10:
        print(f'⚠️ 월 {month:02d}: 좌표 부족으로 히트맵 생략')
        return

    x_edges = np.linspace(min(all_x), max(all_x), 100)
    y_edges = np.linspace(min(all_y), max(all_y), 100)

    # ✅ 히트맵 1: 격자 기반
    heatmap1, _, _ = np.histogram2d(all_x, all_y, bins=[x_edges, y_edges])
    rgba_img1 = create_colored_rgba(heatmap1)

    # ✅ 히트맵 2: 체류시간 기반
    speed = np.sqrt(np.diff(all_x, prepend=all_x[0])**2 + np.diff(all_y, prepend=all_y[0])**2)
    weights = 1.0 / (speed + 1e-6)
    heatmap2, _, _ = np.histogram2d(all_x, all_y, bins=[x_edges, y_edges], weights=weights)
    rgba_img2 = create_colored_rgba(heatmap2)

    # ✅ 통합 히트맵
    combined_rgba = np.zeros_like(rgba_img1)
    for i in range(rgba_img1.shape[0]):
        for j in range(rgba_img1.shape[1]):
            color1 = rgba_to_hex(rgba_img1[i, j])
            color2 = rgba_to_hex(rgba_img2[i, j])
            merged_color = color_merge_rules.get((color1, color2)) or \
                           color_merge_rules.get((color2, color1)) or color1
            combined_rgba[i, j] = plt.matplotlib.colors.to_rgba(merged_color)

    # ✅ 저장
    plt.figure(figsize=(12, 9))
    plt.imshow(combined_rgba, extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
               origin='lower', aspect='auto')
    plt.title(f'Unified Trash Heatmap - Month {month:02d}')
    plt.axis('off')
    save_path = os.path.join(RESULT_DIR, f'month_{month:02d}_unified_heatmap.png')
    plt.savefig(save_path)
    plt.close()
    print(f'✅ 월 {month:02d} 통합 히트맵 저장 완료: {save_path}')

def create_colored_rgba(heatmap):
    colors = ['#fbfdec', '#e1e036', '#feb24c', '#fd8d3c', '#f03b20']
    rgba_img = np.zeros((*heatmap.shape, 4))
    norm_heat = heatmap.copy()
    norm_heat[norm_heat == 0] = np.nan
    min_val, max_val = np.nanmin(norm_heat), np.nanmax(norm_heat)
    bins = np.linspace(min_val, max_val, 6)
    for i in range(heatmap.shape[0]):
        for j in range(heatmap.shape[1]):
            val = norm_heat[i, j]
            if np.isnan(val):
                rgba_img[i, j] = [0.5725, 0.7961, 1.0, 1.0]
            else:
                for k in range(5):
                    if bins[k] <= val <= bins[k + 1]:
                        rgba_img[i, j] = plt.matplotlib.colors.to_rgba(colors[k])
                        break
    return rgba_img

# ✅ 메인 실행
if __name__ == '__main__':
    for month in range(1, 13):
        process_month(month)
    print('\n✅ 모든 월 자동 통합 히트맵 생성 완료!')