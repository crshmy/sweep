// 🚢 AIS 복잡도 히트맵 레이어
// AIS 데이터 기반 선박 통행 밀집도 시각화

class VesselLayer {
    constructor(map) {
        this.map = map;
        this.heatmapLayer = null;
        this.gridLayer = L.layerGroup();
        this.aisData = [];
        this.gridSize = 0.02; // 0.02도 간격 (약 2.2km)
        this.densityGrid = new Map();
        
        console.log('🚢 AIS 복잡도 레이어 초기화');
    }

    // 🚢 초기화
    async init() {
        try {
            await this.loadAISData();
            this.calculateDensityGrid();
            this.createHeatmapLayer();
            
            console.log('✅ AIS 복잡도 레이어 준비 완료');
            return true;
        } catch (error) {
            console.error('❌ AIS 레이어 초기화 실패:', error);
            return false;
        }
    }

    // 📊 AIS 데이터 로드
    async loadAISData() {
        try {
            const response = await fetch('./data/AIS/해양수산부_선박 AIS 동적정보_20220101.csv');
            const text = await response.text();
            
            const lines = text.split('\n').slice(1); // 헤더 제외
            
            console.log(`📊 총 ${lines.length}개 AIS 데이터 처리 중...`);
            
            // 샘플링 (너무 많으면 렉)
            const sampleRate = Math.max(1, Math.floor(lines.length / 50000));
            
            this.aisData = lines
                .filter((_, idx) => idx % sampleRate === 0)
                .map(line => {
                    const parts = line.split(',');
                    if (parts.length < 7) return null;
                    
                    // 위도/경도 변환 (10^7로 나눔)
                    const lat = parseFloat(parts[2]) / 10000000;
                    const lon = parseFloat(parts[3]) / 10000000;
                    const sog = parseFloat(parts[4]);
                    
                    // 부산 앞바다 범위만
                    if (lat >= 34.5 && lat <= 35.5 && lon >= 128.5 && lon <= 130.0) {
                        return { lat, lon, sog };
                    }
                    return null;
                })
                .filter(d => d !== null);
            
            console.log(`✅ ${this.aisData.length}개 AIS 포인트 로드 완료`);
        } catch (error) {
            console.error('❌ AIS 데이터 로드 실패:', error);
            // 더미 데이터 생성
            this.generateDummyData();
        }
    }

    // 📊 밀집도 격자 계산
    calculateDensityGrid() {
        this.densityGrid.clear();
        
        this.aisData.forEach(point => {
            const gridLat = Math.floor(point.lat / this.gridSize) * this.gridSize;
            const gridLon = Math.floor(point.lon / this.gridSize) * this.gridSize;
            const key = `${gridLat.toFixed(3)},${gridLon.toFixed(3)}`;
            
            const current = this.densityGrid.get(key) || { count: 0, totalSpeed: 0 };
            current.count += 1;
            current.totalSpeed += point.sog;
            this.densityGrid.set(key, current);
        });
        
        console.log(`✅ ${this.densityGrid.size}개 격자 밀집도 계산 완료`);
    }

    // 🗺️ 히트맵 레이어 생성
    createHeatmapLayer() {
        this.gridLayer.clearLayers();
        
        // 최대 밀집도 찾기
        let maxDensity = 0;
        this.densityGrid.forEach(data => {
            if (data.count > maxDensity) maxDensity = data.count;
        });
        
        console.log(`📊 최대 밀집도: ${maxDensity}`);
        
        // 격자 타일 생성
        this.densityGrid.forEach((data, key) => {
            const [lat, lon] = key.split(',').map(Number);
            const intensity = data.count / maxDensity;
            const avgSpeed = data.totalSpeed / data.count;
            
            const halfGrid = this.gridSize / 2;
            const bounds = [
                [lat, lon],
                [lat + this.gridSize, lon + this.gridSize]
            ];
            
            const color = this.getDensityColor(intensity);
            
            const rectangle = L.rectangle(bounds, {
                color: color,
                fillColor: color,
                fillOpacity: 0.3 + intensity * 0.4,
                weight: 0.5,
                opacity: 0.5
            });
            
            const popup = `
                <div style="font-size: 12px;">
                    <b>🚢 AIS 복잡도</b><br>
                    통행량: <strong>${data.count}척</strong><br>
                    평균속도: <strong>${avgSpeed.toFixed(1)} 노트</strong><br>
                    밀집도: <strong>${(intensity * 100).toFixed(0)}%</strong>
                </div>
            `;
            rectangle.bindPopup(popup);
            
            this.gridLayer.addLayer(rectangle);
        });
        
        console.log(`✅ ${this.densityGrid.size}개 격자 타일 생성 완료`);
    }

    // 🎨 밀집도에 따른 색상
    getDensityColor(intensity) {
        if (intensity < 0.1) return '#4caf50';  // 낮음 (녹색)
        if (intensity < 0.2) return '#8bc34a';
        if (intensity < 0.3) return '#cddc39';
        if (intensity < 0.4) return '#ffeb3b';  // 보통 (노란색)
        if (intensity < 0.5) return '#ffc107';
        if (intensity < 0.6) return '#ff9800';
        if (intensity < 0.7) return '#ff5722';  // 높음 (주황색)
        if (intensity < 0.8) return '#f44336';
        return '#d32f2f';                        // 매우 높음 (빨간색)
    }

    // 🎲 더미 데이터 생성 (로드 실패시)
    generateDummyData() {
        console.log('⚠️ 더미 데이터 생성 중...');
        
        // 부산 주요 항로
        const routes = [
            { start: [35.1, 129.0], end: [35.0, 129.1] },  // 부산항
            { start: [35.0, 129.1], end: [34.8, 129.3] },  // 남동쪽
            { start: [34.9, 129.0], end: [34.8, 128.8] },  // 거제 방향
        ];
        
        routes.forEach(route => {
            for (let i = 0; i < 100; i++) {
                const t = i / 100;
                const lat = route.start[0] + (route.end[0] - route.start[0]) * t;
                const lon = route.start[1] + (route.end[1] - route.start[1]) * t;
                const sog = 8 + Math.random() * 5;
                
                this.aisData.push({ lat, lon, sog });
            }
        });
        
        console.log(`✅ ${this.aisData.length}개 더미 데이터 생성 완료`);
    }

    // 🔄 레이어 토글
    toggle() {
        if (this.map.hasLayer(this.gridLayer)) {
            this.map.removeLayer(this.gridLayer);
            return false;
        } else {
            this.gridLayer.addTo(this.map);
            return true;
        }
    }

    // 🔄 데이터 새로고침
    async refresh() {
        console.log('🔄 AIS 데이터 새로고침...');
        await this.loadAISData();
        this.calculateDensityGrid();
        this.createHeatmapLayer();
        
        if (this.map.hasLayer(this.gridLayer)) {
            this.gridLayer.addTo(this.map);
        }
        console.log('✅ 새로고침 완료');
    }
}

// 전역으로 export
if (typeof window !== 'undefined') {
    window.VesselLayer = VesselLayer;
}
