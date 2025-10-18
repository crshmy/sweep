/**
 * 어선 데이터 소스 추상화
 * 과거 데이터 vs 실시간 AIS 쉽게 전환 가능
 */

class FishingDataSource {
    constructor(mode = 'demo') {
        this.mode = mode;  // 'demo' or 'live'
        this.config = this.getConfig();
    }
    
    getConfig() {
        if (this.mode === 'demo') {
            return {
                type: 'static',
                dataFile: 'data/fishing_risk_grid.json',
                updateInterval: null,
                description: '사전 계산된 격자 데이터'
            };
        } else if (this.mode === 'live') {
            return {
                type: 'realtime',
                apiEndpoint: 'https://api.your-server.com/ais',
                updateInterval: 30000,  // 30초
                description: '실시간 AIS 수신'
            };
        }
    }
    
    async loadData() {
        if (this.mode === 'demo') {
            return await this.loadStaticData();
        } else {
            return await this.loadRealtimeData();
        }
    }
    
    async loadStaticData() {
        console.log('📦 정적 데이터 로딩 (데모 모드)');
        const response = await fetch(this.config.dataFile);
        const data = await response.json();
        return data;
    }
    
    async loadRealtimeData() {
        console.log('📡 실시간 AIS 데이터 수신');
        // 나중에 구현
        const response = await fetch(this.config.apiEndpoint);
        const aisData = await response.json();
        
        // AI 모델로 예측
        const predictions = await this.predictFishingActivity(aisData);
        return predictions;
    }
    
    async predictFishingActivity(aisData) {
        // 실시간 예측 로직
        // Flask API 호출
        const response = await fetch('http://localhost:5000/predict', {
            method: 'POST',
            body: JSON.stringify(aisData)
        });
        return await response.json();
    }
    
    startAutoUpdate(callback) {
        if (this.config.updateInterval) {
            setInterval(async () => {
                const data = await this.loadData();
                callback(data);
            }, this.config.updateInterval);
        }
    }
}

// 사용 예시
class FishingRiskLayer {
    constructor(map, mode = 'demo') {
        this.map = map;
        this.dataSource = new FishingDataSource(mode);
        this.initialize();
    }
    
    async initialize() {
        // 모드와 관계없이 동일한 초기화
        const data = await this.dataSource.loadData();
        this.displayOnMap(data);
        
        // 실시간 모드면 자동 업데이트
        this.dataSource.startAutoUpdate((newData) => {
            this.updateMap(newData);
        });
    }
    
    displayOnMap(data) {
        // 격자 표시 (동일한 로직)
        data.grids.forEach(grid => {
            const color = this.getRiskColor(grid.risk_level);
            L.circle([grid.lat, grid.lon], {
                radius: 5000,
                color: color,
                fillOpacity: 0.5
            }).addTo(this.map);
        });
    }
    
    updateMap(newData) {
        // 맵 업데이트 (실시간 모드)
        console.log('🔄 실시간 데이터 업데이트');
        this.clearMap();
        this.displayOnMap(newData);
    }
    
    getRiskColor(riskLevel) {
        return {
            'high': '#FF0000',
            'medium': '#FFA500',
            'low': '#00FF00'
        }[riskLevel];
    }
    
    clearMap() {
        // 기존 레이어 제거
    }
}

// ============================================
// 사용법
// ============================================

// 데모 모드 (지금)
const fishingLayer = new FishingRiskLayer(map, 'demo');

// 실시간 모드로 전환 (나중에)
// const fishingLayer = new FishingRiskLayer(map, 'live');

// 전역 설정으로 관리
window.FISHING_CONFIG = {
    mode: 'demo',  // 'demo' or 'live'
    autoUpdate: false
};
