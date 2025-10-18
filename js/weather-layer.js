// 🌊 실시간 기상/해양 레이어 시스템
// OpenWeatherMap + Windy 통합

class WeatherLayer {
    constructor(map) {
        this.map = map;
        this.windLayer = null;
        this.waveLayer = null;
        this.currentLayer = null;
        
        // OpenWeatherMap API (무료)
        this.OWM_API_KEY = '33751f8e0734dcf6415f5010de776f4b'; // https://openweathermap.org/api 에서 발급
        this.OWM_BASE = 'https://api.openweathermap.org/data/2.5';
        
        // 캐시
        this.weatherCache = new Map();
        this.cacheExpiry = 10 * 60 * 1000; // 10분
        
        // 격자 설정
        this.gridSize = 0.2; // 0.1 → 0.2도 간격 (약 22km, 더 넓게)
        this.gridData = new Map();
        
        // 레이어 그룹
        this.windArrows = L.layerGroup();
        this.waveCircles = L.layerGroup();
        
        console.log('🌊 기상 레이어 시스템 초기화');
    }

    // 🌊 초기화 - 지도에 레이어 추가
    async init() {
        try {
            // 초기 기상 데이터 로드
            await this.updateWeatherData();
            
            // 바람 화살표 레이어 생성
            this.createWindArrowLayer();
            
            // 파도 레이어 생성  
            this.createWaveLayer();
            
            console.log('✅ 기상 레이어 준비 완료');
            return true;
        } catch (error) {
            console.error('❌ 기상 레이어 초기화 실패:', error);
            return false;
        }
    }

    // 🌐 기상 데이터 가져오기 (OpenWeatherMap)
    async fetchWeatherData(lat, lon) {
        const cacheKey = `${lat.toFixed(2)},${lon.toFixed(2)}`;
        
        // 캐시 확인
        const cached = this.weatherCache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < this.cacheExpiry) {
            return cached.data;
        }
        
        try {
            const response = await fetch(
                `${this.OWM_BASE}/weather?lat=${lat}&lon=${lon}&appid=${this.OWM_API_KEY}&units=metric`
            );
            
            if (!response.ok) {
                throw new Error(`API 오류: ${response.status}`);
            }
            
            const data = await response.json();
            
            const weatherData = {
                wind: {
                    speed: data.wind.speed,      // m/s
                    direction: data.wind.deg,    // 도
                    gust: data.wind.gust || data.wind.speed * 1.3
                },
                waves: {
                    height: this.estimateWaveHeight(data.wind.speed), // 풍속에서 파고 추정
                    period: 5 + data.wind.speed * 0.2,  // 파주기 추정
                    direction: data.wind.deg
                },
                visibility: data.visibility / 1000, // km
                temperature: data.main.temp,
                description: data.weather[0].description,
                timestamp: Date.now()
            };
            
            // 캐시 저장
            this.weatherCache.set(cacheKey, {
                data: weatherData,
                timestamp: Date.now()
            });
            
            return weatherData;
            
        } catch (error) {
            console.error('기상 데이터 로드 실패:', error);
            
            // Fallback: 더미 데이터
            return this.getDummyWeatherData(lat, lon);
        }
    }

    // 📊 영역 전체 기상 데이터 수집
    async updateWeatherData() {
        const bounds = this.map.getBounds();
        const sw = bounds.getSouthWest();
        const ne = bounds.getNorthEast();
        
        const points = [];
        
        // 격자로 나눠서 샘플링
        for (let lat = sw.lat; lat <= ne.lat; lat += this.gridSize) {
            for (let lon = sw.lng; lon <= ne.lng; lon += this.gridSize) {
                points.push([lat, lon]);
            }
        }
        
        console.log(`🌐 ${points.length}개 지점 기상 데이터 수집 중...`);
        
        // 병렬로 데이터 가져오기 (너무 많으면 제한)
        const samples = points.slice(0, 20); // 최대 20개 지점
        const promises = samples.map(([lat, lon]) => 
            this.fetchWeatherData(lat, lon)
        );
        
        const results = await Promise.allSettled(promises);
        
        // 그리드 데이터 저장
        results.forEach((result, idx) => {
            if (result.status === 'fulfilled') {
                const [lat, lon] = samples[idx];
                const key = `${lat.toFixed(2)},${lon.toFixed(2)}`;
                this.gridData.set(key, result.value);
            }
        });
        
        console.log(`✅ ${this.gridData.size}개 지점 데이터 수집 완료`);
    }

    // 🌬️ 바람 화살표 레이어 생성
    createWindArrowLayer() {
        // 기존 레이어 완전 제거
        this.windArrows.clearLayers();
        
        // 지도에서 제거
        if (this.map.hasLayer(this.windArrows)) {
            this.map.removeLayer(this.windArrows);
        }
        
        this.gridData.forEach((data, key) => {
            const [lat, lon] = key.split(',').map(Number);
            
            // 바람 화살표 마커
            const arrow = this.createWindArrow(lat, lon, data.wind);
            this.windArrows.addLayer(arrow);
        });
    }

    // 🌊 파도 레이어 생성
    createWaveLayer() {
        // 기존 레이어 완전 제거
        this.waveCircles.clearLayers();
        
        // 지도에서 제거
        if (this.map.hasLayer(this.waveCircles)) {
            this.map.removeLayer(this.waveCircles);
        }
        
        this.gridData.forEach((data, key) => {
            const [lat, lon] = key.split(',').map(Number);
            
            // 파고를 색상으로 표현
            const circle = this.createWaveCircle(lat, lon, data.waves);
            this.waveCircles.addLayer(circle);
        });
    }

    // ➡️ 바람 화살표 마커 생성
    createWindArrow(lat, lon, wind) {
        const color = this.getWindSpeedColor(wind.speed);
        const size = Math.min(30 + wind.speed * 2, 50); // 크기 조정
        
        const icon = L.divIcon({
            className: 'wind-arrow-marker',
            html: `
                <div style="
                    width: ${size}px;
                    height: ${size}px;
                    position: relative;
                    transform: rotate(${wind.direction}deg);
                    filter: drop-shadow(0 2px 6px rgba(0,0,0,0.4));
                ">
                    <svg width="${size}" height="${size}" viewBox="0 0 24 24">
                        <!-- 화살표 모양 개선 -->
                        <path d="M12 2 L16 12 L12 10 L8 12 Z" 
                              fill="${color}" 
                              stroke="white" 
                              stroke-width="1.5"
                              opacity="0.9"/>
                        <!-- 꿀리 -->
                        <line x1="12" y1="10" x2="12" y2="18" 
                              stroke="${color}" 
                              stroke-width="2" 
                              opacity="0.7"/>
                    </svg>
                </div>
            `,
            iconSize: [size, size],
            iconAnchor: [size/2, size/2]
        });
        
        return L.marker([lat, lon], { icon: icon })
            .bindPopup(`
                <b>🌬️ 바람</b><br>
                풍속: <strong>${wind.speed.toFixed(1)} m/s</strong><br>
                풍향: ${this.degreesToDirection(wind.direction)} (${Math.round(wind.direction)}°)<br>
                돌풍: ${wind.gust.toFixed(1)} m/s
            `);
    }

    // 🌊 파도 원형 마커 생성
    createWaveCircle(lat, lon, waves) {
        const color = this.getWaveHeightColor(waves.height);
        const radius = 8000 + waves.height * 2000; // 크기 조정 (10km 기본)
        
        return L.circle([lat, lon], {
            radius: radius,
            color: color,
            fillColor: color,
            fillOpacity: 0.15, // 더 투명하게
            weight: 1.5,
            opacity: 0.4
        }).bindPopup(`
            <b>🌊 파도</b><br>
            파고: <strong>${waves.height.toFixed(1)} m</strong><br>
            파주기: ${waves.period.toFixed(1)} 초<br>
            방향: ${this.degreesToDirection(waves.direction)}°
        `);
    }

    // 🎨 풍속에 따른 색상
    getWindSpeedColor(speed) {
        // Beaufort scale 기반
        if (speed < 2) return '#90caf9';      // 약한 바람
        if (speed < 6) return '#64b5f6';      // 보통
        if (speed < 10) return '#42a5f5';     // 약간 강함
        if (speed < 15) return '#ff9800';     // 강함
        if (speed < 20) return '#ff5722';     // 매우 강함
        return '#f44336';                      // 위험
    }

    // 🎨 파고에 따른 색상
    getWaveHeightColor(height) {
        if (height < 0.5) return '#4caf50';   // 잔잔
        if (height < 1.0) return '#8bc34a';   // 약간
        if (height < 1.5) return '#cddc39';   // 보통
        if (height < 2.5) return '#ff9800';   // 높음
        if (height < 4.0) return '#ff5722';   // 매우 높음
        return '#f44336';                      // 위험
    }

    // 📍 특정 위치의 기상 데이터 가져오기
    async getWeatherAt(lat, lon) {
        // 가장 가까운 그리드 포인트 찾기
        const gridLat = Math.round(lat / this.gridSize) * this.gridSize;
        const gridLon = Math.round(lon / this.gridSize) * this.gridSize;
        const key = `${gridLat.toFixed(2)},${gridLon.toFixed(2)}`;
        
        let data = this.gridData.get(key);
        
        // 없으면 새로 가져오기
        if (!data) {
            data = await this.fetchWeatherData(lat, lon);
            this.gridData.set(key, data);
        }
        
        return data;
    }

    // 🧮 풍속에서 파고 추정 (경험식)
    estimateWaveHeight(windSpeed) {
        // Simplified wave height estimation
        // H ≈ 0.21 * V^2 (where V is wind speed in m/s)
        return Math.min(0.21 * Math.pow(windSpeed, 1.5) / 9.8, 10);
    }

    // 🧭 각도를 방향으로 변환
    degreesToDirection(degrees) {
        const directions = ['북', '북동', '동', '남동', '남', '남서', '서', '북서'];
        const index = Math.round(degrees / 45) % 8;
        return directions[index];
    }

    // 🔄 레이어 토글
    toggleWindLayer() {
        if (this.map.hasLayer(this.windArrows)) {
            this.map.removeLayer(this.windArrows);
            return false;
        } else {
            this.windArrows.addTo(this.map);
            return true;
        }
    }

    toggleWaveLayer() {
        if (this.map.hasLayer(this.waveCircles)) {
            this.map.removeLayer(this.waveCircles);
            return false;
        } else {
            this.waveCircles.addTo(this.map);
            return true;
        }
    }

    // 🔄 데이터 새로고침
    async refresh() {
        console.log('🔄 기상 데이터 새로고침...');
        await this.updateWeatherData();
        this.createWindArrowLayer();
        this.createWaveLayer();
        
        // 활성화된 레이어 다시 추가
        if (this.map.hasLayer(this.windArrows)) {
            this.windArrows.addTo(this.map);
        }
        if (this.map.hasLayer(this.waveCircles)) {
            this.waveCircles.addTo(this.map);
        }
    }

    // 🎲 더미 데이터 (API 실패시)
    getDummyWeatherData(lat, lon) {
        const randomWind = 5 + Math.random() * 10;
        const randomDir = Math.random() * 360;
        
        return {
            wind: {
                speed: randomWind,
                direction: randomDir,
                gust: randomWind * 1.3
            },
            waves: {
                height: this.estimateWaveHeight(randomWind),
                period: 5 + randomWind * 0.2,
                direction: randomDir
            },
            visibility: 10 + Math.random() * 10,
            temperature: 15 + Math.random() * 10,
            description: '맑음',
            timestamp: Date.now()
        };
    }
}

// 전역으로 export
if (typeof window !== 'undefined') {
    window.WeatherLayer = WeatherLayer;
}
