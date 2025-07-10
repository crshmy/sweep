import pandas as pd
import numpy as np
import folium
import os

# 설정
DATA_DIR = './data'
RESULT_DIR = './results_trash_maps_by_type_month'
os.makedirs(RESULT_DIR, exist_ok=True)

years = [2022, 2023, 2024]
months = range(1, 13)

trash_types = {
    '가벼운 소형 쓰레기': {'alpha': 3.0, 'beta': 1.0},
    '가벼운 중형 쓰레기': {'alpha': 2.5, 'beta': 1.2},
    '가벼운 대형 쓰레기': {'alpha': 1.5, 'beta': 2.0},
    '무거운 소형 쓰레기': {'alpha': 1.2, 'beta': 2.5},
    '무거운 중형 쓰레기': {'alpha': 0.8, 'beta': 3.0},
}

year_colors = {
    2022: 'red',
    2023: 'green',
    2024: 'blue',
}

start_lat = 34.919
start_lon = 129.12125

for trash_name, params in trash_types.items():
    alpha = params['alpha']
    beta = params['beta']

    for month in months:
        m = folium.Map(location=[start_lat, start_lon], zoom_start=6)
        date_log = []

        for year in years:
            color = year_colors[year]
            filename = f'{year}년 {month:02d}월 대한해협 해양관측부이.csv'
            filepath = os.path.join(DATA_DIR, filename)
            try:
                df = pd.read_csv(filepath, encoding='cp949', sep='\t', skiprows=3)
                required_cols = ['풍속(m/s)', '풍향(deg)', '유의파고(MOSE.HF)(m)', '파향(deg)', '관측시간']
                if not all(col in df.columns for col in required_cols):
                    print(f'❌ {filepath} → 컬럼 없음 → 스킵됨')
                    continue
            except Exception as e:
                print(f'❌ {filepath} 에서 오류: {e}')
                continue

            wind_speed = pd.to_numeric(df['풍속(m/s)'], errors='coerce').fillna(0)
            wind_dir = pd.to_numeric(df['풍향(deg)'], errors='coerce').fillna(0)
            wave_height = pd.to_numeric(df['유의파고(MOSE.HF)(m)'], errors='coerce').fillna(0)
            wave_dir = pd.to_numeric(df['파향(deg)'], errors='coerce').fillna(0)

            X = (alpha * wind_speed * np.cos(np.radians(wind_dir + 180))) + \
                (beta * wave_height * np.cos(np.radians(wave_dir)))
            Y = (alpha * wind_speed * np.sin(np.radians(wind_dir + 180))) + \
                (beta * wave_height * np.sin(np.radians(wave_dir)))

            dx_km = X * 0.001
            dy_km = Y * 0.001

            delta_lon = dx_km / (111 * abs(np.cos(np.radians(start_lat))))
            delta_lat = dy_km / 111

            lon = np.cumsum(delta_lon) + start_lon
            lat = np.cumsum(delta_lat) + start_lat

            points = list(zip(lat, lon))
            folium.PolyLine(points, color=color, weight=2.5, opacity=1,
                            tooltip=f"{year}년 {month}월").add_to(m)

            dates = df['관측시간'].tolist()
            date_log.append(f"## {year}년 {month}월\n" + "\n".join(dates))

        # 범례 추가
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 260px; height: 130px; 
                    background-color: white; z-index:9999; font-size:14px;
                    border:2px solid grey; padding: 10px;">
        <b>📅 년도별 경로 색상</b><br>
        <span style="color:red;">■</span> 2022년<br>
        <span style="color:green;">■</span> 2023년<br>
        <span style="color:blue;">■</span> 2024년<br>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # 지도 저장 (쓰레기 종류 + 월별 저장)
        save_name = f'{trash_name}_{month:02d}월_3개년_경로.html'
        m.save(os.path.join(RESULT_DIR, save_name))

        # # 날짜 로그 저장
        # with open(os.path.join(RESULT_DIR, f'{trash_name}_{month:02d}월_3개년_날짜.txt'), 'w', encoding='utf-8') as f:
        #     f.write("\n\n".join(date_log))

print("\n✅ 쓰레기 종류별 월별 3개년 지도 + 날짜 로그 저장 완료!")