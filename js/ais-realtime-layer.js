/**
 * AIS 실시간 데이터 레이어 (프록시 수정 버전)
 */

class AISRealtimeLayer {
    constructor(map) {
        this.map = map;
        
        this.apiKey = '26b98bee868c73916870225a035294cbd43037f3ec8cc86c51854b91e54e00ad';
        this.baseUrl = 'https://api.odcloud.kr/api/15129186/v1';
        this.endpoint = 'uddi:2762dfc8-b8ae-4e17-8a44-86f39f480203';
        
        this.vesselLayer = null;
        this.heatmapLayer = null;
        this.vessels = [];
        
        this.updateInterval = 3600000;
        this.updateTimer = null;
        this.lastUpdate = null;
        
        this.isLoading = false;
        this.isEnabled = false;
        
        this.init();
    }
    
    init() {
        console.log('🚢 AIS 실시간 레이어 초기화...');
        
        this.vesselLayer = L.layerGroup().addTo(this.map);
        
        this.loadAISData();
        this.startAutoUpdate();
    }
    
    async loadAISData() {
        if (this.isLoading) {
            console.log('⏳ 이미 데이터 로딩 중...');
            return;
        }
        
        this.isLoading = true;
        this.showLoadingIndicator();
        
        try {
            console.log('📡 AIS 데이터 요청 중...');
            
            const data = await this.fetchFromAPI();
            
            this.vessels = this.parseAISData(data);
            
            console.log(`✅ AIS 데이터 로드 완료: ${this.vessels.length}척`);
            
            this.updateMap();
            this.saveToCache(data);
            
            this.lastUpdate = new Date();
            this.updateUI();
            
        } catch (error) {
            console.error('❌ AIS 데이터 로드 실패:', error);
            await this.loadFromCache();
            
        } finally {
            this.isLoading = false;
            this.hideLoadingIndicator();
        }
    }
    
    async fetchFromAPI() {
        const url = `${this.baseUrl}/${this.endpoint}`;
        
        const params = new URLSearchParams({
            serviceKey: this.apiKey,
            page: 1,
            perPage: 1000,
            returnType: 'JSON'
        });
        
        const targetUrl = `${url}?${params.toString()}`;
        
        // 🔥 여러 프록시 시도
        const proxies = [
            `https://api.allorigins.win/raw?url=${encodeURIComponent(targetUrl)}`,
            `https://cors-anywhere.herokuapp.com/${targetUrl}`,
            `https://thingproxy.freeboard.io/fetch/${targetUrl}`
        ];
        
        let lastError = null;
        
        for (const proxyUrl of proxies) {
            try {
                console.log('🌐 프록시 시도:', proxyUrl);
                
                const response = await fetch(proxyUrl);
                
                if (response.ok) {
                    const data = await response.json();
                    console.log('✅ 프록시 성공!');
                    return data;
                }
                
                console.warn(`⚠️ 프록시 실패 (${response.status}), 다음 시도...`);
                
            } catch (error) {
                console.warn(`⚠️ 프록시 에러: ${error.message}, 다음 시도...`);
                lastError = error;
            }
        }
        
        throw new Error(`모든 프록시 실패: ${lastError}`);
    }
    
    parseAISData(apiResponse) {
        console.log('📊 API 응답:', apiResponse);
        
        const vessels = [];
        
        try {
            const rawData = apiResponse.data || [];
            
            console.log(`📦 원본 데이터 개수: ${rawData.length}`);
            
            if (rawData.length > 0) {
                console.log('🔍 첫 번째 선박:', rawData[0]);
            }
            
            for (const record of rawData) {
                const vessel = this.parseVesselRecord(record);
                
                if (vessel) {
                    vessels.push(vessel);
                }
            }
            
            console.log(`✅ 유효한 선박: ${vessels.length}척`);
            
            vessels.slice(0, 3).forEach((v, i) => {
                console.log(`   선박 ${i+1}: 위도=${v.lat}, 경도=${v.lon}`);
            });
            
        } catch (error) {
            console.error('❌ 데이터 파싱 오류:', error);
        }
        
        return vessels;
    }
    
    parseVesselRecord(record) {
        try {
            let lat = parseFloat(record.위도 || record.latitude || record.LAT || 0);
            let lon = parseFloat(record.경도 || record.longitude || record.LON || 0);
            
            const vessel = {
                mmsi: record.MMSI || 'Unknown',
                name: `선박-${record.MMSI || 'Unknown'}`,
                lat: lat,
                lon: lon,
                speed: parseFloat(record.SOG || 0),
                course: parseFloat(record.COG || 0),
                heading: parseFloat(record.HEADING || 0),
                timestamp: record.수신시간 || new Date().toISOString()
            };
            
            if (!vessel.lat || !vessel.lon || vessel.lat === 0 || vessel.lon === 0) {
                return null;
            }
            
            if (isNaN(vessel.lat) || isNaN(vessel.lon)) {
                return null;
            }
            
            return vessel;
            
        } catch (error) {
            return null;
        }
    }
    
    updateMap() {
        this.vesselLayer.clearLayers();
        
        if (this.vessels.length === 0) {
            console.warn('⚠️ 표시할 선박 데이터 없음');
            return;
        }
        
        console.log('🗺️ 지도에 표시 중...');
        
        const heatPoints = this.vessels.map(vessel => {
            return [vessel.lat, vessel.lon, 0.5];
        });
        
        if (this.heatmapLayer) {
            this.map.removeLayer(this.heatmapLayer);
        }
        
        this.heatmapLayer = L.heatLayer(heatPoints, {
            radius: 25,
            blur: 35,
            maxZoom: 10,
            max: 1.0,
            gradient: {
                0.0: '#000080',
                0.3: '#0080FF',
                0.5: '#00FF80',
                0.7: '#FFFF00',
                0.9: '#FF8000',
                1.0: '#FF0000'
            }
        }).addTo(this.map);
        
        for (const vessel of this.vessels) {
            this.addVesselMarker(vessel);
        }
        
        console.log(`🗺️ 완료: ${this.vessels.length}척 표시됨`);
    }
    
    addVesselMarker(vessel) {
        const icon = L.divIcon({
            className: 'vessel-marker',
            html: `
                <div style="transform: rotate(${vessel.course}deg)">
                    <svg width="20" height="20" viewBox="0 0 20 20">
                        <path d="M10 2 L16 18 L10 14 L4 18 Z" 
                              fill="#00FF00" 
                              stroke="#fff" 
                              stroke-width="2"/>
                    </svg>
                </div>
            `,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
        
        const marker = L.marker([vessel.lat, vessel.lon], { icon })
            .addTo(this.vesselLayer);
        
        marker.bindPopup(`
            <div>
                <h3>🚢 ${vessel.name}</h3>
                <p><strong>MMSI:</strong> ${vessel.mmsi}</p>
                <p><strong>위치:</strong> ${vessel.lat.toFixed(4)}°N, ${vessel.lon.toFixed(4)}°E</p>
                <p><strong>속도:</strong> ${vessel.speed.toFixed(1)} knots</p>
            </div>
        `);
    }
    
    saveToCache(data) {
        try {
            localStorage.setItem('ais_cache', JSON.stringify({
                data: data,
                timestamp: Date.now(),
                vessels: this.vessels
            }));
            console.log('💾 캐시 저장');
        } catch (error) {
            console.warn('⚠️ 캐시 저장 실패');
        }
    }
    
    async loadFromCache() {
        try {
            const cached = localStorage.getItem('ais_cache');
            if (!cached) return;
            
            const cacheData = JSON.parse(cached);
            console.log('📦 캐시 사용');
            
            this.vessels = cacheData.vessels || [];
            this.updateMap();
            this.updateUI();
        } catch (error) {
            console.error('❌ 캐시 로드 실패');
        }
    }
    
    startAutoUpdate() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        this.updateTimer = setInterval(() => {
            this.loadAISData();
        }, this.updateInterval);
    }
    
    stopAutoUpdate() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }
    
    toggle() {
        this.isEnabled = !this.isEnabled;
        if (this.isEnabled) {
            this.show();
        } else {
            this.hide();
        }
    }
    
    show() {
        if (this.heatmapLayer) this.map.addLayer(this.heatmapLayer);
        this.map.addLayer(this.vesselLayer);
        this.isEnabled = true;
    }
    
    hide() {
        if (this.heatmapLayer) this.map.removeLayer(this.heatmapLayer);
        this.map.removeLayer(this.vesselLayer);
        this.isEnabled = false;
    }
    
    updateUI() {
        const vesselCountEl = document.getElementById('aisVesselCount');
        const lastUpdateEl = document.getElementById('aisLastUpdate');
        
        if (vesselCountEl) {
            vesselCountEl.textContent = `${this.vessels.length}척`;
            vesselCountEl.style.color = '#4caf50';
        }
        
        if (lastUpdateEl && this.lastUpdate) {
            lastUpdateEl.textContent = this.lastUpdate.toLocaleTimeString('ko-KR');
        }
    }
    
    showLoadingIndicator() {
        const indicator = document.getElementById('aisLoadingIndicator');
        if (indicator) indicator.style.display = 'block';
    }
    
    hideLoadingIndicator() {
        const indicator = document.getElementById('aisLoadingIndicator');
        if (indicator) indicator.style.display = 'none';
    }
    
    refresh() {
        console.log('🔄 새로고침');
        this.loadAISData();
    }
    
    destroy() {
        this.stopAutoUpdate();
        this.vesselLayer.clearLayers();
        if (this.heatmapLayer) this.map.removeLayer(this.heatmapLayer);
        this.map.removeLayer(this.vesselLayer);
    }
}

window.AISRealtimeLayer = AISRealtimeLayer;
