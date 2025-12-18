// 🌊 드라마틱한 바람 레이어 - 큰 화살표 버전

class WeatherLayer {
    constructor(map) {
        this.map = map;
        this.windLayer = null;
        this.waveLayer = null;
        
        // 고정 기상 데이터
        this.baseWindSpeed = 6.5;
        this.baseWindDir = 45;
        
        // 격자 설정 (더 넓게)
        this.gridSize = 0.12; // 0.12도 간격으로 넓게
        
        // 고정 범위 (부산 앞바다 전체)
        this.fixedBounds = {
            minLat: 34.2,
            maxLat: 35.3,
            minLon: 128.5,
            maxLon: 130.2
        };
        
        // 레이어 그룹
        this.windGridLayer = L.layerGroup();
        this.waveGridLayer = L.layerGroup();
        this.gridData = new Map();
        
        console.log('🌊 드라마틱 바람 레이어 초기화 (큰 화살표)');
    }

    // 🌊 초기화
    async init() {
        try {
            this.generateFixedWeatherData();
            this.createWindGridLayer();
            this.createWaveGridLayer();
            
            console.log('✅ 기상 격자 레이어 준비 완료');
            return true;
        } catch (error) {
            console.error('❌ 기상 레이어 초기화 실패:', error);
            return false;
        }
    }

    // 🌊 해양 판별
    isOcean(lat, lon) {
        if (lat < this.fixedBounds.minLat || lat > this.fixedBounds.maxLat) return false;
        if (lon < this.fixedBounds.minLon || lon > this.fixedBounds.maxLon) return false;
        
        if (lon >= 129.2) return true;
        if (lat <= 34.6) return true;
        if (lat <= 35.0 && lon >= 129.0) return true;
        if (lon >= 128.3 && lat <= 35.0) return true;
        if (lat >= 35.0 && lat <= 35.2 && lon >= 128.5 && lon <= 128.75) return true;
        if (lat <= 35.15 && lon >= 128.9) return true;
        
        if (lat >= 35.12 && lon <= 129.03) return false;
        if (lat >= 35.15 && lat <= 35.25 && lon <= 128.6) return false;
        if (lat >= 35.18 && lon <= 128.9) return false;
        
        return true;
    }

    // 📊 고정 범위 기상 데이터 생성
    generateFixedWeatherData() {
        const points = [];
        
        for (let lat = this.fixedBounds.minLat; lat <= this.fixedBounds.maxLat; lat += this.gridSize) {
            for (let lon = this.fixedBounds.minLon; lon <= this.fixedBounds.maxLon; lon += this.gridSize) {
                if (this.isOcean(lat, lon)) {
                    points.push([lat, lon]);
                }
            }
        }
        
        console.log(`🌐 ${points.length}개 해상 격자 생성 중...`);
        
        points.forEach(([lat, lon]) => {
            const key = `${lat.toFixed(3)},${lon.toFixed(3)}`;
            
            const latVar = Math.sin(lat * 40) * 2.0;
            const lonVar = Math.cos(lon * 40) * 2.0;
            
            const windSpeed = Math.max(3, this.baseWindSpeed + latVar);
            const windDir = (this.baseWindDir + lonVar * 15 + 360) % 360;
            
            this.gridData.set(key, {
                wind: {
                    speed: windSpeed,
                    direction: windDir,
                    gust: windSpeed * 1.3
                },
                waves: {
                    height: this.estimateWaveHeight(windSpeed),
                    period: 5 + windSpeed * 0.2,
                    direction: windDir
                },
                temperature: 23 + Math.sin(lat * 50) * 2,
                visibility: 15 + Math.cos(lon * 30) * 3
            });
        });
        
        console.log(`✅ ${this.gridData.size}개 격자 데이터 생성 완료`);
    }

    // 🌬️ 바람 격자 레이어 생성
    createWindGridLayer() {
        this.windGridLayer.clearLayers();
        
        if (this.map.hasLayer(this.windGridLayer)) {
            this.map.removeLayer(this.windGridLayer);
        }
        
        this.gridData.forEach((data, key) => {
            const [lat, lon] = key.split(',').map(Number);
            const gridTile = this.createWindGridTile(lat, lon, data.wind);
            this.windGridLayer.addLayer(gridTile);
        });
        
        console.log(`✅ ${this.gridData.size}개 바람 격자 생성`);
    }

    // 🌊 파도 격자 레이어 생성
    createWaveGridLayer() {
        this.waveGridLayer.clearLayers();
        
        if (this.map.hasLayer(this.waveGridLayer)) {
            this.map.removeLayer(this.waveGridLayer);
        }
        
        this.gridData.forEach((data, key) => {
            const [lat, lon] = key.split(',').map(Number);
            const gridTile = this.createWaveGridTile(lat, lon, data.waves);
            this.waveGridLayer.addLayer(gridTile);
        });
        
        console.log(`✅ ${this.gridData.size}개 파도 격자 생성`);
    }

    // 📐 바람 격자 타일 생성 (드라마틱 큰 화살표!)
    createWindGridTile(lat, lon, wind) {
        const color = this.getWindSpeedColor(wind.speed);
        const halfGrid = this.gridSize / 2;
        
        const bounds = [
            [lat - halfGrid, lon - halfGrid],
            [lat + halfGrid, lon + halfGrid]
        ];
        
        const rectangle = L.rectangle(bounds, {
            color: color,
            fillColor: color,
            fillOpacity: 0.25,
            weight: 0.5,
            opacity: 0.4
        });
        
        // 🎯 매우 큰 바람 화살표!
        const arrowIcon = L.divIcon({
            className: 'wind-arrow-big',
            html: `
                <div style="
                    width: 50px;
                    height: 50px;
                    transform: rotate(${wind.direction}deg);
                    filter: drop-shadow(0 3px 6px rgba(0,0,0,0.6));
                    animation: windPulse 2.5s ease-in-out infinite;
                ">
                    <svg width="50" height="50" viewBox="0 0 50 50">
                        <!-- 화살표 몸통 -->
                        <line x1="25" y1="12" x2="25" y2="42" 
                              stroke="white" 
                              stroke-width="5" 
                              stroke-linecap="round"
                              opacity="0.95"/>
                        <!-- 화살표 머리 -->
                        <path d="M25 4 L35 16 L25 13 L15 16 Z" 
                              fill="white" 
                              stroke="${color}" 
                              stroke-width="2.5"
                              opacity="0.95"/>
                        <!-- 바람 강도 표시 (깃털) -->
                        <line x1="25" y1="22" x2="32" y2="19" 
                              stroke="white" 
                              stroke-width="4" 
                              stroke-linecap="round"
                              opacity="0.85"/>
                        <line x1="25" y1="30" x2="32" y2="27" 
                              stroke="white" 
                              stroke-width="4" 
                              stroke-linecap="round"
                              opacity="0.85"/>
                    </svg>
                </div>
                <style>
                @keyframes windPulse {
                    0%, 100% { transform: scale(1) rotate(${wind.direction}deg); opacity: 0.9; }
                    50% { transform: scale(1.15) rotate(${wind.direction}deg); opacity: 1; }
                }
                </style>
            `,
            iconSize: [50, 50],
            iconAnchor: [25, 25]
        });
        
        const arrowMarker = L.marker([lat, lon], { icon: arrowIcon });
        
        const popup = `
            <div style="font-size: 13px; font-weight: bold;">
                <b style="color: ${color};">🌬️ 바람</b><br>
                풍속: <strong style="font-size: 16px;">${wind.speed.toFixed(1)} m/s</strong><br>
                풍향: ${this.degreesToDirection(wind.direction)} (${Math.round(wind.direction)}°)<br>
                돌풍: ${wind.gust.toFixed(1)} m/s
            </div>
        `;
        rectangle.bindPopup(popup);
        arrowMarker.bindPopup(popup);
        
        return L.layerGroup([rectangle, arrowMarker]);
    }

    // 🌊 파도 격자 타일 생성
    createWaveGridTile(lat, lon, waves) {
        const color = this.getWaveHeightColor(waves.height);
        const halfGrid = this.gridSize / 2;
        
        const bounds = [
            [lat - halfGrid, lon - halfGrid],
            [lat + halfGrid, lon + halfGrid]
        ];
        
        const rectangle = L.rectangle(bounds, {
            color: color,
            fillColor: color,
            fillOpacity: 0.25,
            weight: 0.5,
            opacity: 0.3
        });
        
        const textIcon = L.divIcon({
            className: 'wave-text-grid',
            html: `
                <div style="
                    color: white;
                    font-size: 11px;
                    font-weight: bold;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
                    text-align: center;
                ">
                    🌊 ${waves.height.toFixed(1)}m
                </div>
            `,
            iconSize: [50, 20],
            iconAnchor: [25, 10]
        });
        
        const textMarker = L.marker([lat, lon], { icon: textIcon });
        
        const popup = `
            <div style="font-size: 12px;">
                <b>🌊 파도</b><br>
                파고: <strong>${waves.height.toFixed(1)} m</strong><br>
                파주기: ${waves.period.toFixed(1)} 초<br>
                방향: ${this.degreesToDirection(waves.direction)}°
            </div>
        `;
        rectangle.bindPopup(popup);
        textMarker.bindPopup(popup);
        
        return L.layerGroup([rectangle, textMarker]);
    }

    // 🎨 풍속에 따른 색상
    getWindSpeedColor(speed) {
        if (speed < 3) return '#b3e5fc';
        if (speed < 5) return '#81d4fa';
        if (speed < 7) return '#4fc3f7';
        if (speed < 9) return '#29b6f6';
        if (speed < 12) return '#039be5';
        if (speed < 15) return '#ff9800';
        if (speed < 20) return '#ff5722';
        return '#f44336';
    }

    // 🎨 파고에 따른 색상
    getWaveHeightColor(height) {
        if (height < 0.5) return '#81c784';
        if (height < 1.0) return '#66bb6a';
        if (height < 1.5) return '#4caf50';
        if (height < 2.0) return '#ffa726';
        if (height < 2.5) return '#ff9800';
        if (height < 4.0) return '#ff5722';
        return '#f44336';
    }

    // 📍 특정 위치의 기상 데이터 (중요!)
    getWindAtPosition(lat, lon) {
        const gridLat = Math.round(lat / this.gridSize) * this.gridSize;
        const gridLon = Math.round(lon / this.gridSize) * this.gridSize;
        const key = `${gridLat.toFixed(3)},${gridLon.toFixed(3)}`;
        
        const data = this.gridData.get(key);
        if (data && data.wind) {
            return data.wind;
        }
        
        return {
            speed: this.baseWindSpeed,
            direction: this.baseWindDir,
            gust: this.baseWindSpeed * 1.3
        };
    }

    // 🧮 풍속에서 파고 추정
    estimateWaveHeight(windSpeed) {
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
        if (this.map.hasLayer(this.windGridLayer)) {
            this.map.removeLayer(this.windGridLayer);
            return false;
        } else {
            this.windGridLayer.addTo(this.map);
            return true;
        }
    }

    toggleWaveLayer() {
        if (this.map.hasLayer(this.waveGridLayer)) {
            this.map.removeLayer(this.waveGridLayer);
            return false;
        } else {
            this.waveGridLayer.addTo(this.map);
            return true;
        }
    }

    // 🔄 데이터 새로고침
    async refresh() {
        console.log('🔄 기상 데이터 새로고침...');
        console.log('✅ 고정 데이터 사용 중 (일관성 유지)');
    }
}

// 전역으로 export
if (typeof window !== 'undefined') {
    window.WeatherLayer = WeatherLayer;
}
