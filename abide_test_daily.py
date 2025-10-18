import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.colors import LogNorm

# ----------------- 설정 -----------------
DATA_DIR = './data'
RESULT_DIR = './results_trash_daily'
os.makedirs(RESULT_DIR, exist_ok=True)

# 기존 결과 삭제
for file in os.listdir(RESULT_DIR):
    file_path = os.path.join(RESULT_DIR, file)
    if os.path.isfile(file_path):
        os.remove(file_path)
print(f'🧹 Existing result files deleted: {RESULT_DIR}')

# 분석 대상 연도 및 쓰레기 종류 설정
years = [2022, 2023, 2024]
trash_types = {
    'Light Small Trash': {'alpha': 0.05, 'beta': 0.02},
    'Light Medium Trash': {'alpha': 0.04, 'beta': 0.03},
    'Heavy Small Trash': {'alpha': 0.03, 'beta': 0.04},
    'Heavy Medium Trash': {'alpha': 0.02, 'beta': 0.05},
    'Heavy Large Trash': {'alpha': 0.01, 'beta': 0.06},
}
selected_trash = 'Light Small Trash'
alpha = trash_types[selected_trash]['alpha']
beta = trash_types[selected_trash]['beta']

# ----------------- 데이터 로딩 -----------------
def load_data(year, month):
    filename = f'{year}년 {month:02d}월 대한해협 해양관측부이.csv'
    filepath = os.path.join(DATA_DIR, filename)
    print(f'📁 Checking file: {filepath}')
    try:
        df = pd.read_csv(filepath, encoding='cp949', sep='\t', skiprows=3)
        required_cols = ['관측시간', '표층유속(cm/s)', '풍속(m/s)', '풍향(deg)',
                         '유의파고(MOSE.HF)(m)', '파향(deg)']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f'Missing required columns in {filepath}')
        df['관측시간'] = pd.to_datetime(df['관측시간'])
        return df
    except Exception as e:
        print(f'❗ CSV loading failed: {filepath}')
        print(f'    Error: {e}')
        return None

# ----------------- 하루 단위 데이터 계산 -----------------
def calculate_day_data(year, month, day, df):
    day_str = f'{year}-{month:02d}-{day:02d}'
    
    # 해당 날짜 데이터 선택
    day_df = df[df['관측시간'].dt.day == day]
    if day_df.empty:
        return None

    # 풍속, 풍향, 파고, 파향
    wind_speed = pd.to_numeric(day_df['풍속(m/s)'], errors='coerce').fillna(0)
    wind_direction = pd.to_numeric(day_df['풍향(deg)'], errors='coerce').fillna(0)
    wave_height = pd.to_numeric(day_df['유의파고(MOSE.HF)(m)'], errors='coerce').fillna(0)
    wave_direction = pd.to_numeric(day_df['파향(deg)'], errors='coerce').fillna(0)

    # X, Y 좌표 계산
    X = alpha * wind_speed * np.cos(np.radians(wind_direction + 180)) + \
        beta * wave_height * np.cos(np.radians(wave_direction))
    Y = alpha * wind_speed * np.sin(np.radians(wind_direction + 180)) + \
        beta * wave_height * np.sin(np.radians(wave_direction))

    x = np.cumsum(X.values)
    y = np.cumsum(Y.values)

    # 이동 거리 및 최종 방향 계산
    distance = np.sqrt(X**2 + Y**2)
    direction = np.degrees(np.arctan2(Y, X))

    return {
        'year': year,
        'day_str': day_str,
        'x': x,
        'y': y,
        'distance': distance.sum(),
        'direction': direction.iloc[-1]
    }

# ----------------- 날짜별 통합 처리 -----------------
def process_combined_day(month, day, year_data_list):
    day_str = f'{month:02d}-{day:02d}'
    print(f'\n📦 Processing combined {day_str}')

    if not year_data_list:
        print(f'⚠️ No data for {day_str}')
        return

    # ----------------- Combined Route Graph -----------------
    plt.figure(figsize=(8, 6))
    colors = ['blue', 'green', 'red']
    
    for i, data in enumerate(year_data_list):
        plt.plot(data['x'], data['y'], color=colors[i], 
                label=f"{data['year']} ({data['distance']:.2f} km)", alpha=0.7)
        print(f"  {data['year']}: Distance={data['distance']:.2f} km, Direction={data['direction']:.2f}°")
    
    plt.title(f'Drift Routes Comparison - {day_str}')
    plt.xlabel('X coordinate (km)')
    plt.ylabel('Y coordinate (km)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    route_path = os.path.join(RESULT_DIR, f'{day_str}_combined_route.png')
    plt.savefig(route_path)
    plt.close()
    print(f'✅ Combined route graph saved: {route_path}')

    # ----------------- Combined Residence Time Heatmap -----------------
    # 모든 연도의 x, y 범위를 합쳐서 격자 생성
    all_x = np.concatenate([data['x'] for data in year_data_list])
    all_y = np.concatenate([data['y'] for data in year_data_list])
    
    if len(all_x) > 10:
        x_edges = np.linspace(min(all_x), max(all_x), 100)
        y_edges = np.linspace(min(all_y), max(all_y), 100)

        # 통합 히트맵 생성
        combined_heatmap = np.zeros((len(x_edges)-1, len(y_edges)-1))

        for data in year_data_list:
            x = data['x']
            y = data['y']
            
            # 체류시간 가중치 계산
            speed = np.sqrt(np.diff(x, prepend=x[0])**2 + np.diff(y, prepend=y[0])**2)
            epsilon = 0.01
            residence_weights = 1.0 / np.maximum(speed, epsilon)
            residence_weights = np.clip(residence_weights, 0, 100)

            # 2D 히트맵 누적
            heatmap, _, _ = np.histogram2d(
                x, y, bins=[x_edges, y_edges], weights=residence_weights
            )
            combined_heatmap += heatmap

        # LogNorm 대비 적용
        if np.any(combined_heatmap > 0):
            vmin = np.percentile(combined_heatmap[combined_heatmap > 0], 5)
            vmax = np.percentile(combined_heatmap, 95)
            if vmax <= vmin:
                vmax = vmin * 10
        else:
            vmin, vmax = 1e-3, 1

        plt.figure(figsize=(8, 6))
        plt.imshow(
            combined_heatmap.T,
            origin='lower',
            cmap='plasma',
            extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
            aspect='auto',
            norm=LogNorm(vmin=vmin, vmax=vmax)
        )
        plt.colorbar(label='Combined Residence Time (2022+2023+2024)')
        plt.title(f'Combined Residence Time Heatmap - {day_str}')
        plt.xlabel('X coordinate (km)')
        plt.ylabel('Y coordinate (km)')
        plt.tight_layout()

        heatmap_path = os.path.join(RESULT_DIR, f'{day_str}_combined_heatmap.png')
        plt.savefig(heatmap_path)
        plt.close()
        print(f'🕒 Combined Residence Time Heatmap saved: {heatmap_path}')
    else:
        print('⚠️ Not enough data points for heatmap')

# ----------------- 메인 실행 -----------------
if __name__ == '__main__':
    print('🟢 Script started')
    selected_month = int(input("Enter month to analyze (1~12): "))
    print(f'🔹 Selected month: {selected_month}')

    # 모든 연도의 데이터를 먼저 로드
    year_dataframes = {}
    for year in years:
        df = load_data(year, selected_month)
        if df is not None:
            year_dataframes[year] = df

    # 날짜별로 처리
    for day in range(1, 32):
        year_data_list = []
        
        for year in years:
            if year not in year_dataframes:
                continue
            
            df = year_dataframes[year]
            if day > df['관측시간'].dt.day.max():
                continue
            
            data = calculate_day_data(year, selected_month, day, df)
            if data is not None:
                year_data_list.append(data)
        
        if year_data_list:
            process_combined_day(selected_month, day, year_data_list)

    print('\n✅ All days processed!')