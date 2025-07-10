import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# 설정
DATA_DIR = './data'
RESULT_DIR = './results_trash_longtime'
os.makedirs(RESULT_DIR, exist_ok=True)

# ✅ 기존 결과 삭제
for file in os.listdir(RESULT_DIR):
    file_path = os.path.join(RESULT_DIR, file)
    if os.path.isfile(file_path):
        os.remove(file_path)
print(f'🧹 기존 결과 파일 모두 삭제 완료: {RESULT_DIR}')

years = [2022, 2023, 2024]

trash_types = {
    '가벼운 소형 쓰레기': {'alpha': 0.05, 'beta': 0.02},
    '가벼운 중형 쓰레기': {'alpha': 0.04, 'beta': 0.03},
    '기벼운 대형 쓰레기': {'alpha': 0.03, 'beta': 0.04},
    '무거운 소형 쓰레기': {'alpha': 0.02, 'beta': 0.05},
    '무거운 중형 쓰레기': {'alpha': 0.01, 'beta': 0.06},
}
selected_trash = '가벼운 소형 쓰레기'
alpha = trash_types[selected_trash]['alpha']
beta = trash_types[selected_trash]['beta']

def load_data(year, month):
    filename = f'{year}년 {month:02d}월 대한해협 해양관측부이.csv'
    filepath = os.path.join(DATA_DIR, filename)
    print(f'📁 파일 확인 중: {filepath}')  # 디버깅 출력
    try:
        df = pd.read_csv(filepath, encoding='cp949', sep='\t', skiprows=3)
        required_cols = ['표층유속(cm/s)', '풍속(m/s)', '풍향(deg)', '유의파고(MOSE.HF)(m)', '파향(deg)']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f'Missing required columns in {filepath}')
        return df
    except Exception as e:
        print(f'❗ CSV 로딩 실패: {filepath}')
        print(f'    에러 내용: {e}')
        return None

def process_month(month):
    print(f'\n📦 {month}월 처리 시작')  # 실행 확인
    plt.figure(figsize=(12, 9))
    colors = {2022: 'red', 2023: 'green', 2024: 'blue'}

    all_x = []
    all_y = []

    with open(os.path.join(RESULT_DIR, 'summary.txt'), 'a', encoding='utf-8') as f:
        for year in years:
            df = load_data(year, month)
            if df is None:
                continue

            wind_speed = pd.to_numeric(df['풍속(m/s)'], errors='coerce').fillna(0)
            wind_direction = pd.to_numeric(df['풍향(deg)'], errors='coerce').fillna(0)
            wave_height = pd.to_numeric(df['유의파고(MOSE.HF)(m)'], errors='coerce').fillna(0)
            wave_direction = pd.to_numeric(df['파향(deg)'], errors='coerce').fillna(0)

            X = (alpha * wind_speed * np.cos(np.radians(wind_direction + 180))) + \
                (beta * wave_height * np.cos(np.radians(wave_direction)))
            Y = (alpha * wind_speed * np.sin(np.radians(wind_direction + 180))) + \
                (beta * wave_height * np.sin(np.radians(wave_direction)))

            x = np.cumsum(X)
            y = np.cumsum(Y)

            print(f'🧪 {year}년 {month}월 - 좌표 수: {len(x)}개')  # 확인용
            all_x.extend(x)
            all_y.extend(y)

            plt.plot(x, y, color=colors[year], label=f'{year}')

            distance = np.sqrt(X**2 + Y**2)
            direction = np.degrees(np.arctan2(Y, X))

            msg1 = f'📊 {year}년 {month}월 이동 거리 합계: {distance.sum():.2f} km'
            msg2 = f'📊 {year}년 {month}월 최종 이동 방향: {direction.iloc[-1]:.2f}°'

            print(msg1)
            print(msg2)
            f.write(msg1 + '\n')
            f.write(msg2 + '\n')

    # 이동 경로 그래프 저장
    plt.title(f'Trash Drift Routes ({selected_trash}) - Month {month:02d}')
    plt.xlabel('Longitude (Pseudo)')
    plt.ylabel('Latitude (Pseudo)')
    plt.legend()
    plt.grid(True)
    route_path = os.path.join(RESULT_DIR, f'month_{month:02d}_routes.png')
    plt.savefig(route_path)
    plt.close()
    print(f'✅ 궤적 그래프 저장됨: {route_path}')

    # ✅ 체류 시간 기반 히트맵
    if len(all_x) > 10:
        x_edges = np.linspace(min(all_x), max(all_x), 100)
        y_edges = np.linspace(min(all_y), max(all_y), 100)
        
        print(f'📏 격자 칸당 거리: X축 {(max(all_x) - min(all_x)) / 100:.4f} km, Y축 {(max(all_y) - min(all_y)) / 100:.4f} km')

        speed = np.sqrt(np.diff(all_x, prepend=all_x[0])**2 + np.diff(all_y, prepend=all_y[0])**2)
        residence_weights = 1.0 / (speed + 1e-6)  # 체류 시간 가중치

        heatmap, xedges, yedges = np.histogram2d(
            all_x, all_y, bins=[x_edges, y_edges], weights=residence_weights
        )

        colors = ['#fbfdec', '#e1e036', '#feb24c', '#fd8d3c', '#f03b20']

        norm_heat = heatmap.copy()
        norm_heat[norm_heat == 0] = np.nan

        min_val = np.nanmin(norm_heat)
        max_val = np.nanmax(norm_heat)
        bins = np.linspace(min_val, max_val, 6)

        rgba_img = np.zeros((heatmap.shape[0], heatmap.shape[1], 4))

        for i in range(heatmap.shape[0]):
            for j in range(heatmap.shape[1]):
                val = norm_heat[i, j]
                if np.isnan(val):
                    rgba_img[i, j] = [0.5725, 0.7961, 1.0, 1.0]  # 배경색 (#92cbff)
                else:
                    for k in range(5):
                        if bins[k] <= val <= bins[k+1]:
                            rgba_img[i, j] = plt.matplotlib.colors.to_rgba(colors[k])
                            break

        plt.figure(figsize=(12, 9))
        plt.imshow(
            rgba_img,
            extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
            origin='lower',
            aspect='auto'
        )
        plt.title(f'Trash Residence-Time Weighted Heatmap ({selected_trash}) - Month {month:02d}')
        plt.xlabel('Longitude (Pseudo, km)')
        plt.ylabel('Latitude (Pseudo, km)')
        plt.grid(False)

        heatmap_path = os.path.join(RESULT_DIR, f'month_{month:02d}_residence_time_weighted_heatmap.png')
        plt.savefig(heatmap_path)
        plt.close()
        print(f'🕒 체류 시간 기반 히트맵 저장됨: {heatmap_path}')
    else:
        print('⚠️ 히트맵 생략: 좌표 수 부족')

# ✅ 메인 실행부
if __name__ == '__main__':
    print('🟢 스크립트 실행 시작')
    for month in range(1, 13):
        process_month(month)
    print('\n✅ 모든 월 완료!')