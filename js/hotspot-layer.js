// 🗑️ 쓰레기 밀집구역 레이어 (핫스팟)
// hotspots.json 기반 자연스러운 히트맵 + 클릭 가능한 마커

class HotspotLayer {
    constructor(map) {
        this.map = map;
        this.heatLayer = null;
        this.markerLayer = L.layerGroup(); // 클릭 가능한 마커들
        this.hotspots = [];
        
        // 좌표 변환 파라미터 (history_summary.json 기준)
        this.gridRange = {
            x_min: -13.09067800238495,
            x_max: 0.451239766783554,
            y_min: -17.82655521790533,
            y_max: 1.0299445138357493
        };
        
        // 부산 앞바다 실제 좌표 범위
        this.geoRange = {
            lat_min: 34.5,
            lat_max: 35.5,
            lon_min: 128.5,
            lon_max: 130.0
        };
        
        console.log('🗑️ 쓰레기 밀집구역 레이어 초기화 (Interactive Heatmap)');
    }

    // 🗑️ 초기화
    async init() {
        try {
            await this.loadHotspots();
            this.createSmoothHeatmap();
            this.createClickableMarkers();
            
            console.log('✅ 쓰레기 밀집구역 히트맵 + 마커 준비 완료');
            return true;
        } catch (error) {
            console.error('❌ 핫스팟 레이어 초기화 실패:', error);
            return false;
        }
    }

    // 📊 hotspots.json 로드
    async loadHotspots() {
        try {
            const response = await fetch('./hotspot/daily_results_final_251013/hotspots.json');
            const data = await response.json();
            
            this.hotspots = data.hotspots.map((h, idx) => ({
                id: idx + 1,
                grid_x: h.x,
                grid_y: h.y,
                value: h.value,
                lat: this.gridToLat(h.y),
                lon: this.gridToLon(h.x)
            }));
            
            // 값으로 정렬 (높은 순)
            this.hotspots.sort((a, b) => b.value - a.value);
            
            console.log(`✅ ${this.hotspots.length}개 핫스팟 로드 완료`);
            console.log('Top 3 핫스팟:', this.hotspots.slice(0, 3).map(h => 
                `#${h.id} - 밀집도: ${h.value.toFixed(2)}`
            ));
        } catch (error) {
            console.error('❌ hotspots.json 로드 실패:', error);
            this.generateDummyHotspots();
        }
    }

    // 📐 격자 좌표 → 위도 변환
    gridToLat(grid_y) {
        const { y_min, y_max } = this.gridRange;
        const { lat_min, lat_max } = this.geoRange;
        
        // 격자 Y를 0~1로 정규화
        const normalized = (grid_y - y_min) / (y_max - y_min);
        
        // 위도로 변환
        return lat_min + normalized * (lat_max - lat_min);
    }

    // 📐 격자 좌표 → 경도 변환
    gridToLon(grid_x) {
        const { x_min, x_max } = this.gridRange;
        const { lon_min, lon_max } = this.geoRange;
        
        // 격자 X를 0~1로 정규화
        const normalized = (grid_x - x_min) / (x_max - x_min);
        
        // 경도로 변환
        return lon_min + normalized * (lon_max - lon_min);
    }

    // 🌊 부드러운 히트맵 생성 (leaflet-heat 사용)
    createSmoothHeatmap() {
        // 기존 레이어 제거
        if (this.heatLayer) {
            this.map.removeLayer(this.heatLayer);
        }
        
        // 최대값 찾기 (정규화용)
        const maxValue = Math.max(...this.hotspots.map(h => h.value));
        const minValue = Math.min(...this.hotspots.map(h => h.value));
        
        console.log(`📊 밀집도 범위: ${minValue.toFixed(2)} ~ ${maxValue.toFixed(2)}`);
        
        // 히트맵 데이터 생성 [위도, 경도, 강도]
        // ⚠️ 로그 스케일 적용 (작은 값도 보이게)
        const heatData = this.hotspots.map(h => {
            // 로그 스케일 정규화 (0.01 이하는 0.01로)
            const logValue = Math.log10(Math.max(h.value, 0.01));
            const logMax = Math.log10(maxValue);
            const logMin = Math.log10(0.01);
            const intensity = (logValue - logMin) / (logMax - logMin);
            
            return [
                h.lat,
                h.lon,
                Math.max(0.3, intensity) // 최소 0.3 (보이게)
            ];
        });
        
        console.log('🎨 히트맵 샘플:', heatData.slice(0, 3));
        
        // leaflet-heat 플러그인 사용
        this.heatLayer = L.heatLayer(heatData, {
            radius: 40,           // 히트맵 반경 (더 크게)
            blur: 50,             // 블러 정도 (더 부드럽게)
            maxZoom: 17,          // 최대 줌 레벨
            max: 1.0,             // 최대 강도
            minOpacity: 0.4,      // 최소 투명도 (더 진하게)
            gradient: {           // 🎨 색상 그라데이션
                0.0: '#000080',   // 파랑 (가장 낮음)
                0.2: '#0000FF',   // 밝은 파랑
                0.35: '#00FFFF',  // 청록
                0.5: '#00FF00',   // 초록
                0.65: '#FFFF00',  // 노랑
                0.8: '#FF8000',   // 주황
                0.9: '#FF0000',   // 빨강
                1.0: '#800000'    // 진한 빨강 (가장 높음)
            }
        });
        
        console.log(`✅ ${this.hotspots.length}개 포인트로 부드러운 히트맵 생성 완료`);
        console.log('🎨 그라데이션: 파랑(낮음) → 빨강(높음)');
    }

    // 📍 클릭 가능한 투명 마커 생성
    createClickableMarkers() {
        this.markerLayer.clearLayers();
        
        const maxValue = Math.max(...this.hotspots.map(h => h.value));
        
        this.hotspots.forEach((hotspot, idx) => {
            const intensity = hotspot.value / maxValue;
            const color = this.getIntensityColor(intensity);
            
            // 투명한 원형 마커 (클릭 가능)
            const circle = L.circle([hotspot.lat, hotspot.lon], {
                radius: 800, // 800m 반경
                color: 'transparent',
                fillColor: 'transparent',
                fillOpacity: 0,
                weight: 0
            });
            
            // 팝업 정보
            const rank = idx + 1;
            const popupContent = `
                <div style="min-width: 200px; font-family: 'Segoe UI', sans-serif;">
                    <div style="background: linear-gradient(135deg, ${color}, ${this.darkenColor(color)}); 
                                padding: 12px; margin: -15px -20px 10px -20px; border-radius: 8px 8px 0 0;">
                        <h3 style="margin: 0; color: white; font-size: 16px; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                            🗑️ 쓰레기 밀집구역 #${rank}
                        </h3>
                    </div>
                    
                    <div style="padding: 5px 0;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span style="color: #666;">🎯 밀집도:</span>
                            <strong style="color: ${color}; font-size: 18px;">${hotspot.value.toFixed(2)}</strong>
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span style="color: #666;">📊 순위:</span>
                            <strong>${rank} / ${this.hotspots.length}</strong>
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span style="color: #666;">📍 위치:</span>
                            <span style="font-size: 11px; color: #999;">
                                ${hotspot.lat.toFixed(4)}°N<br>
                                ${hotspot.lon.toFixed(4)}°E
                            </span>
                        </div>
                        
                        <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div style="width: 100%; height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden;">
                                    <div style="width: ${intensity * 100}%; height: 100%; 
                                                background: linear-gradient(90deg, #00ff00, ${color}); 
                                                transition: width 0.3s;"></div>
                                </div>
                                <span style="color: #999; font-size: 11px;">${(intensity * 100).toFixed(0)}%</span>
                            </div>
                        </div>
                        
                        <div style="margin-top: 10px; padding: 8px; background: #f8f9fa; border-radius: 4px; font-size: 12px; color: #666;">
                            ${this.getIntensityDescription(intensity)}
                        </div>
                    </div>
                </div>
            `;
            
            circle.bindPopup(popupContent, {
                maxWidth: 300,
                className: 'hotspot-popup'
            });
            
            // 호버 효과
            circle.on('mouseover', function() {
                this.setStyle({
                    fillColor: color,
                    fillOpacity: 0.2,
                    color: color,
                    weight: 2
                });
            });
            
            circle.on('mouseout', function() {
                this.setStyle({
                    fillColor: 'transparent',
                    fillOpacity: 0,
                    color: 'transparent',
                    weight: 0
                });
            });
            
            this.markerLayer.addLayer(circle);
        });
        
        console.log(`✅ ${this.hotspots.length}개 클릭 가능한 마커 생성 완료`);
    }

    // 🎨 밀집도에 따른 색상
    getIntensityColor(intensity) {
        if (intensity > 0.9) return '#800000';  // 진한 빨강
        if (intensity > 0.8) return '#FF0000';  // 빨강
        if (intensity > 0.65) return '#FF8000'; // 주황
        if (intensity > 0.5) return '#FFFF00';  // 노랑
        if (intensity > 0.35) return '#00FF00'; // 초록
        if (intensity > 0.2) return '#00FFFF';  // 청록
        if (intensity > 0.1) return '#0000FF';  // 파랑
        return '#000080';                        // 진한 파랑
    }

    // 🎨 색상 어둡게
    darkenColor(color) {
        const factor = 0.7;
        const hex = color.replace('#', '');
        const r = Math.floor(parseInt(hex.substr(0, 2), 16) * factor);
        const g = Math.floor(parseInt(hex.substr(2, 2), 16) * factor);
        const b = Math.floor(parseInt(hex.substr(4, 2), 16) * factor);
        return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }

    // 📝 밀집도 설명
    getIntensityDescription(intensity) {
        if (intensity > 0.9) return '⚠️ 매우 위험 - 즉시 수거 필요!';
        if (intensity > 0.7) return '🔴 높음 - 우선 수거 권장';
        if (intensity > 0.5) return '🟠 중상 - 수거 필요';
        if (intensity > 0.3) return '🟡 중간 - 수거 고려';
        return '🟢 낮음 - 모니터링';
    }

    // 🎲 더미 핫스팟 생성 (로드 실패시)
    generateDummyHotspots() {
        console.log('⚠️ 더미 핫스팟 생성 중...');
        
        // 부산 앞바다 주요 지점
        const dummyPoints = [
            { lat: 35.1, lon: 129.1, value: 38.0 },  // 부산항 앞 (최고 밀집)
            { lat: 35.08, lon: 129.12, value: 35.0 },
            { lat: 35.06, lon: 129.14, value: 32.0 },
            { lat: 35.0, lon: 129.2, value: 28.0 },  // 해운대 앞
            { lat: 34.98, lon: 129.22, value: 25.0 },
            { lat: 34.96, lon: 129.24, value: 22.0 },
            { lat: 34.9, lon: 129.3, value: 20.0 },  // 기장 앞
            { lat: 34.88, lon: 129.28, value: 18.0 },
            { lat: 34.86, lon: 129.26, value: 15.0 },
            { lat: 34.8, lon: 129.0, value: 12.0 },  // 거제 북쪽
            { lat: 34.78, lon: 129.02, value: 10.0 },
            { lat: 34.76, lon: 128.98, value: 8.0 },
            { lat: 34.7, lon: 128.9, value: 6.0 },   // 거제 서쪽
            { lat: 35.05, lon: 129.15, value: 15.0 },
            { lat: 34.95, lon: 129.25, value: 12.0 },
            { lat: 34.85, lon: 129.1, value: 10.0 },
            { lat: 35.02, lon: 129.18, value: 8.0 },
            { lat: 34.92, lon: 129.28, value: 6.0 },
            { lat: 34.82, lon: 129.08, value: 5.0 },
            { lat: 35.12, lon: 129.08, value: 4.0 },
        ];
        
        this.hotspots = dummyPoints.map((p, i) => ({
            id: i + 1,
            grid_x: 0,
            grid_y: 0,
            value: p.value,
            lat: p.lat,
            lon: p.lon
        }));
        
        console.log(`✅ ${this.hotspots.length}개 더미 핫스팟 생성 완료`);
    }

    // 🔄 레이어 토글
    toggle() {
        if (!this.heatLayer) {
            console.warn('⚠️ 히트맵이 아직 생성되지 않았습니다');
            return false;
        }
        
        const hasHeat = this.map.hasLayer(this.heatLayer);
        const hasMarkers = this.map.hasLayer(this.markerLayer);
        
        if (hasHeat || hasMarkers) {
            // 둘 다 제거
            if (hasHeat) this.map.removeLayer(this.heatLayer);
            if (hasMarkers) this.map.removeLayer(this.markerLayer);
            console.log('🔴 히트맵 + 마커 숨김');
            return false;
        } else {
            // 둘 다 표시
            this.heatLayer.addTo(this.map);
            this.markerLayer.addTo(this.map);
            console.log('🟢 히트맵 + 마커 표시');
            return true;
        }
    }

    // 🔄 데이터 새로고침
    async refresh() {
        console.log('🔄 핫스팟 데이터 새로고침...');
        await this.loadHotspots();
        this.createSmoothHeatmap();
        this.createClickableMarkers();
        
        const wasVisible = this.map.hasLayer(this.heatLayer);
        if (wasVisible) {
            this.heatLayer.addTo(this.map);
            this.markerLayer.addTo(this.map);
        }
        console.log('✅ 새로고침 완료');
    }

    // 📍 특정 핫스팟으로 이동
    focusHotspot(index) {
        if (index >= 0 && index < this.hotspots.length) {
            const hotspot = this.hotspots[index];
            this.map.setView([hotspot.lat, hotspot.lon], 13);
            console.log(`🎯 핫스팟 #${index + 1}로 이동: ${hotspot.lat.toFixed(4)}, ${hotspot.lon.toFixed(4)}`);
        }
    }

    // 🎨 히트맵 스타일 변경 (런타임)
    updateStyle(options = {}) {
        const {
            radius = 40,
            blur = 50,
            minOpacity = 0.4,
            gradient = null
        } = options;
        
        // 새 옵션으로 히트맵 재생성
        const maxValue = Math.max(...this.hotspots.map(h => h.value));
        const minValue = Math.min(...this.hotspots.map(h => h.value));
        
        const heatData = this.hotspots.map(h => {
            const logValue = Math.log10(Math.max(h.value, 0.01));
            const logMax = Math.log10(maxValue);
            const logMin = Math.log10(0.01);
            const intensity = (logValue - logMin) / (logMax - logMin);
            return [h.lat, h.lon, Math.max(0.3, intensity)];
        });
        
        if (this.heatLayer) {
            this.map.removeLayer(this.heatLayer);
        }
        
        const heatOptions = {
            radius,
            blur,
            maxZoom: 17,
            max: 1.0,
            minOpacity
        };
        
        if (gradient) {
            heatOptions.gradient = gradient;
        } else {
            // 기본 그라데이션
            heatOptions.gradient = {
                0.0: '#000080',
                0.2: '#0000FF',
                0.35: '#00FFFF',
                0.5: '#00FF00',
                0.65: '#FFFF00',
                0.8: '#FF8000',
                0.9: '#FF0000',
                1.0: '#800000'
            };
        }
        
        this.heatLayer = L.heatLayer(heatData, heatOptions);
        this.heatLayer.addTo(this.map);
        
        console.log('✅ 히트맵 스타일 업데이트:', options);
    }
}

// 전역으로 export
if (typeof window !== 'undefined') {
    window.HotspotLayer = HotspotLayer;
}
