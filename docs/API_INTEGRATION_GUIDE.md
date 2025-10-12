# 해양쓰레기 수거 네비게이션 시스템
## API 연동 가이드

이 문서는 실제 데이터 소스를 네비게이션 시스템에 연동하기 위한 가이드입니다.

## 📋 필요한 데이터 소스

### 1. AIS (자동선박식별장치) 데이터
**목적**: 주변 선박의 실시간 위치 및 정보 제공

**필요한 데이터 필드**:
- `vessel_name`: 선박명
- `mmsi`: 선박 고유 식별번호
- `latitude`: 위도
- `longitude`: 경도
- `speed`: 속도 (knots)
- `heading`: 방향 (도)
- `vessel_type`: 선박 종류
- `timestamp`: 데이터 수신 시간

**추천 API**:
- MarineTraffic API (https://www.marinetraffic.com/en/ais-api-services)
- AISHub (https://www.aishub.net/)
- VesselFinder API (https://www.vesselfinder.com/)

**연동 코드 예시**:
```javascript
async fetchAISData() {
    const response = await fetch('https://api.marinetraffic.com/vessel-data', {
        headers: {
            'Authorization': 'Bearer YOUR_API_KEY'
        }
    });
    const data = await response.json();
    return data.vessels.map(vessel => ({
        id: vessel.mmsi,
        name: vessel.shipname,
        type: vessel.type_name,
        lat: vessel.lat,
        lon: vessel.lon,
        speed: vessel.speed + ' knots',
        heading: vessel.course + '°',
        distance: calculateDistance(currentPosition, [vessel.lat, vessel.lon])
    }));
}
```

---

### 2. 쓰레기 핫스팟 예측 데이터
**목적**: 해양쓰레기가 집중될 것으로 예상되는 지역 표시

**필요한 데이터 필드**:
- `hotspot_id`: 핫스팟 고유 ID
- `latitude`: 위도
- `longitude`: 경도
- `priority`: 우선순위 (high/medium/low)
- `estimated_waste_amount`: 예상 쓰레기 양 (kg)
- `waste_types`: 쓰레기 종류 배열
- `confidence_level`: 예측 신뢰도 (0-100%)
- `detection_time`: 감지 시간
- `image_url`: 위성/드론 이미지 URL (선택)

**데이터 소스 옵션**:
1. **자체 AI 모델 구축**:
   - 위성 이미지 분석 (Sentinel-2, Landsat)
   - 해류 및 풍향 데이터 기반 예측 모델
   - 과거 수거 데이터 학습

2. **오픈 데이터 활용**:
   - NASA의 해양 관측 데이터
   - NOAA의 Marine Debris Tracker
   - Global Fishing Watch 데이터

**연동 코드 예시**:
```javascript
async fetchHotspots() {
    const response = await fetch('https://your-api.com/hotspots', {
        method: 'POST',
        body: JSON.stringify({
            area: {
                minLat: 35.0,
                maxLat: 35.5,
                minLon: 129.0,
                maxLon: 129.5
            },
            date: new Date().toISOString()
        })
    });
    const data = await response.json();
    return data.hotspots;
}
```

---

### 3. 기상 데이터
**목적**: 안전한 항해 및 작업 계획 수립

**필요한 데이터 필드**:
- `temperature`: 기온 (°C)
- `wind_direction`: 풍향 (도 또는 방위)
- `wind_speed`: 풍속 (m/s)
- `wave_height`: 파고 (m)
- `visibility`: 가시거리 (km)
- `weather_condition`: 날씨 상태 (맑음, 흐림, 비 등)
- `forecast`: 시간별 예보 데이터

**추천 API**:
- 기상청 API (https://www.data.go.kr/) - 한국 해역
- OpenWeatherMap API (https://openweathermap.org/api)
- WeatherAPI (https://www.weatherapi.com/)
- Marine Weather API (Windy, Stormglass)

**연동 코드 예시**:
```javascript
async fetchWeatherData() {
    const lat = currentPosition[0];
    const lon = currentPosition[1];
    
    // 기상청 API 예시
    const response = await fetch(
        `http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst?` +
        `serviceKey=YOUR_SERVICE_KEY&` +
        `numOfRows=100&pageNo=1&` +
        `base_date=${getToday()}&base_time=0500&` +
        `nx=${lat}&ny=${lon}`
    );
    
    const data = await response.json();
    
    // 데이터 파싱 및 변환
    return {
        temperature: parseTemperature(data),
        windDirection: parseWindDirection(data),
        windSpeed: parseWindSpeed(data),
        waveHeight: parseWaveHeight(data),
        visibility: parseVisibility(data)
    };
}
```

---

### 4. 해류 데이터
**목적**: 쓰레기 이동 예측 및 항해 효율성 향상

**필요한 데이터 필드**:
- `latitude`: 위도
- `longitude`: 경도
- `u_component`: 동서 방향 속도 (m/s)
- `v_component`: 남북 방향 속도 (m/s)
- `speed`: 해류 속도
- `direction`: 해류 방향

**추천 데이터 소스**:
- HYCOM (Hybrid Coordinate Ocean Model)
- Copernicus Marine Service
- NOAA Ocean Currents

**연동 코드 예시**:
```javascript
async fetchOceanCurrents() {
    const response = await fetch(
        `https://marine.copernicus.eu/api/currents?` +
        `lat=${currentPosition[0]}&lon=${currentPosition[1]}&` +
        `date=${new Date().toISOString()}`
    );
    
    const data = await response.json();
    
    // Leaflet 벡터 레이어로 표시
    const currentVectors = data.map(point => ({
        lat: point.lat,
        lon: point.lon,
        direction: Math.atan2(point.v, point.u) * 180 / Math.PI,
        speed: Math.sqrt(point.u ** 2 + point.v ** 2)
    }));
    
    return currentVectors;
}
```

---

### 5. 파도 데이터
**목적**: 작업 안전성 평가

**필요한 데이터 필드**:
- `significant_wave_height`: 유의파고 (m)
- `wave_period`: 파주기 (s)
- `wave_direction`: 파향 (도)
- `swell_height`: 너울 높이 (m)

**추천 API**:
- NOAA WaveWatch III
- Stormglass Marine API
- Windy API

---

## 🔧 코드 통합 방법

### app.js의 API 객체 수정

현재 `app.js`의 하단에 `API` 객체가 정의되어 있습니다. 각 함수를 실제 API로 교체하세요:

```javascript
const API = {
    // 1. AIS 데이터
    fetchAISData: async () => {
        const response = await fetch('YOUR_AIS_API_ENDPOINT', {
            headers: { 'Authorization': 'Bearer YOUR_API_KEY' }
        });
        return await response.json();
    },

    // 2. 핫스팟 데이터
    fetchHotspots: async () => {
        const response = await fetch('YOUR_HOTSPOT_API_ENDPOINT');
        return await response.json();
    },

    // 3. 기상 데이터
    fetchWeatherData: async () => {
        const response = await fetch('YOUR_WEATHER_API_ENDPOINT');
        const data = await response.json();
        
        // UI 업데이트
        document.getElementById('windDirection').textContent = data.windDirection;
        document.getElementById('windSpeed').textContent = data.windSpeed;
        document.getElementById('waveHeight').textContent = data.waveHeight;
        document.getElementById('visibility').textContent = data.visibility;
        
        return data;
    },

    // 4. 해류 데이터
    fetchOceanCurrents: async () => {
        const response = await fetch('YOUR_OCEAN_CURRENT_API_ENDPOINT');
        return await response.json();
    },

    // 5. 경로 최적화
    optimizeRoute: async (waypoints, constraints) => {
        const response = await fetch('YOUR_OPTIMIZATION_API_ENDPOINT', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ waypoints, constraints })
        });
        return await response.json();
    }
};
```

---

## 🎨 지도 레이어 추가

### 풍향/풍속 레이어
```javascript
function addWindLayer(windData) {
    // Leaflet Velocity 플러그인 사용 추천
    const windLayer = L.velocityLayer({
        data: windData,
        lineWidth: 2,
        displayOptions: {
            velocityType: 'Wind',
            displayPosition: 'bottomleft',
            displayEmptyString: 'No wind data'
        }
    });
    
    windLayer.addTo(map);
}
```

### 해류 레이어
```javascript
function addCurrentLayer(currentData) {
    // 화살표로 해류 방향 표시
    currentData.forEach(point => {
        const arrow = L.marker([point.lat, point.lon], {
            icon: L.divIcon({
                html: `<div style="transform: rotate(${point.direction}deg)">➤</div>`,
                className: 'current-arrow'
            })
        }).addTo(map);
    });
}
```

### 파고 레이어
```javascript
function addWaveLayer(waveData) {
    // 히트맵으로 파고 표시
    const heatmapData = waveData.map(point => [
        point.lat,
        point.lon,
        point.height
    ]);
    
    L.heatLayer(heatmapData, {
        radius: 25,
        blur: 35,
        maxZoom: 12
    }).addTo(map);
}
```

---

## 📱 실시간 데이터 업데이트

`app.js`의 `updateAllData()` 함수가 주기적으로 호출됩니다:

```javascript
async function updateAllData() {
    try {
        // 모든 데이터 동시 가져오기
        const [aisData, hotspots, weather, currents] = await Promise.all([
            API.fetchAISData(),
            API.fetchHotspots(),
            API.fetchWeatherData(),
            API.fetchOceanCurrents()
        ]);
        
        // UI 업데이트
        updateAISMarkers(aisData);
        updateHotspotMarkers(hotspots);
        updateWeatherDisplay(weather);
        
        if (document.getElementById('currentLayer').checked) {
            updateCurrentLayer(currents);
        }
        
        console.log('데이터 업데이트 완료');
    } catch (error) {
        console.error('데이터 업데이트 실패:', error);
        showErrorAlert('데이터 업데이트에 실패했습니다.');
    }
}

// 5분마다 업데이트
setInterval(updateAllData, 300000);
```

---

## 🛣️ 경로 최적화 알고리즘

경로 최적화를 위한 고려사항:

### TSP (외판원 문제) 기반 알고리즘
```javascript
function calculateOptimalRoute(hotspots, constraints) {
    // 1. 모든 핫스팟 간 거리 계산
    const distanceMatrix = calculateDistanceMatrix(hotspots);
    
    // 2. 제약 조건 적용
    // - 기상 조건 (풍속, 파고)
    // - 연료 효율
    // - 작업 시간 제한
    // - 우선순위
    
    // 3. 최적 경로 계산 (유전 알고리즘, 2-opt 등)
    const optimalRoute = solveTSP(distanceMatrix, constraints);
    
    return optimalRoute;
}
```

### 동적 경로 재계산
```javascript
function shouldRecalculateRoute(currentRoute, newConditions) {
    // 기상 악화, 새로운 핫스팟 발견 등의 경우 재계산
    if (newConditions.weatherDeteriorated || 
        newConditions.newHotspotsDetected ||
        newConditions.fuelLow) {
        return true;
    }
    return false;
}
```

---

## 🔐 보안 고려사항

### API 키 보호
```javascript
// 절대 클라이언트 코드에 API 키를 직접 넣지 마세요!
// 백엔드 프록시 서버를 통해 요청하세요

// 나쁜 예:
// const API_KEY = 'your-secret-key-here';

// 좋은 예:
async fetchProtectedData() {
    const response = await fetch('/api/proxy/weather', {
        credentials: 'include' // 쿠키 포함
    });
    return await response.json();
}
```

### CORS 문제 해결
백엔드 서버 설정 예시 (Node.js/Express):
```javascript
const express = require('express');
const app = express();

app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', 'https://your-domain.com');
    res.header('Access-Control-Allow-Methods', 'GET, POST');
    next();
});

app.get('/api/weather', async (req, res) => {
    const data = await fetchFromWeatherAPI();
    res.json(data);
});
```

---

## 📊 데이터 포맷 예시

### AIS 데이터 응답 예시
```json
{
    "vessels": [
        {
            "mmsi": 440012345,
            "name": "OCEAN STAR",
            "type": "Cargo",
            "lat": 35.1796,
            "lon": 129.0756,
            "speed": 12.3,
            "course": 245,
            "timestamp": "2025-10-12T10:30:00Z"
        }
    ]
}
```

### 핫스팟 데이터 응답 예시
```json
{
    "hotspots": [
        {
            "id": "HS001",
            "lat": 35.2,
            "lon": 129.15,
            "priority": "high",
            "estimated_amount_kg": 500,
            "waste_types": ["plastic", "styrofoam"],
            "confidence": 0.87,
            "detected_at": "2025-10-12T09:00:00Z"
        }
    ]
}
```

### 기상 데이터 응답 예시
```json
{
    "temperature": 23.5,
    "wind": {
        "speed": 8.5,
        "direction": 45,
        "direction_name": "NE"
    },
    "waves": {
        "height": 1.2,
        "period": 6.5,
        "direction": 90
    },
    "visibility": 15,
    "weather": "clear",
    "timestamp": "2025-10-12T10:00:00Z"
}
```

---

## 🧪 테스트 방법

### 1. 모의 데이터로 테스트
현재 `app.js`의 `mockData` 객체를 수정하여 다양한 시나리오 테스트

### 2. API 엔드포인트 테스트
```javascript
// 콘솔에서 실행
API.fetchAISData().then(data => console.log('AIS Data:', data));
API.fetchHotspots().then(data => console.log('Hotspots:', data));
API.fetchWeatherData().then(data => console.log('Weather:', data));
```

### 3. 에러 처리 테스트
```javascript
async function testErrorHandling() {
    try {
        const data = await API.fetchAISData();
        console.log('Success:', data);
    } catch (error) {
        console.error('Error caught:', error);
        // 에러 메시지를 사용자에게 표시
        showErrorAlert('AIS 데이터를 가져올 수 없습니다.');
    }
}
```

---

## 📈 성능 최적화

### 데이터 캐싱
```javascript
const dataCache = {
    ais: { data: null, timestamp: null },
    weather: { data: null, timestamp: null }
};

const CACHE_DURATION = 60000; // 1분

async function fetchWithCache(key, fetchFunction) {
    const now = Date.now();
    const cached = dataCache[key];
    
    if (cached.data && (now - cached.timestamp) < CACHE_DURATION) {
        return cached.data;
    }
    
    const data = await fetchFunction();
    dataCache[key] = { data, timestamp: now };
    return data;
}
```

### 마커 클러스터링
```javascript
// Leaflet MarkerCluster 플러그인 사용
const markers = L.markerClusterGroup();
hotspots.forEach(hotspot => {
    const marker = L.marker([hotspot.lat, hotspot.lon]);
    markers.addLayer(marker);
});
map.addLayer(markers);
```

---

## 🚀 배포 체크리스트

- [ ] 모든 API 키를 환경 변수로 이동
- [ ] HTTPS 설정 확인
- [ ] CORS 정책 설정
- [ ] 에러 로깅 시스템 구축
- [ ] 성능 모니터링 도구 설치
- [ ] 백업 시스템 구축
- [ ] 사용자 매뉴얼 작성
- [ ] 테스트 완료 (단위, 통합, E2E)

---

## 📞 추가 지원

문제가 발생하거나 추가 기능이 필요한 경우:
1. GitHub Issues 등록
2. 개발 문서 참조
3. 커뮤니티 포럼 질문

---

## 📝 버전 관리

- v1.0 (2025-10-12): 초기 네비게이션 UI 구축
- v1.1 (예정): AIS 데이터 연동
- v1.2 (예정): AI 기반 핫스팟 예측 모델 통합
- v2.0 (예정): 모바일 앱 버전 출시