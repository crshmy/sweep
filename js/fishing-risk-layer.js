/**
 * 어선 조업 위험도 레이어
 * AI 모델 기반 격자별 시간대별 조업 확률 표시
 */

class FishingRiskLayer {
    constructor(map) {
        this.map = map;
        this.gridData = null;
        this.gridCircles = [];
        this.currentHour = new Date().getHours();
        this.isVisible = true;
        
        console.log('🎣 FishingRiskLayer 초기화...');
        this.loadData();
    }
    
    async loadData() {
        try {
            console.log('📡 격자 데이터 로딩 중...');
            const response = await fetch('data/fishing_risk_grid.json');
            this.gridData = await response.json();
            
            console.log(`✅ ${this.gridData.grids.length}개 격자 로딩 완료`);
            console.log(`   모델 정확도: ${this.gridData.metadata.model_accuracy}`);
            
            this.createControls();
            this.displayGrids();
            
        } catch (error) {
            console.error('❌ 격자 데이터 로딩 실패:', error);
        }
    }
    
    displayGrids() {
        if (!this.gridData) return;
        
        console.log(`🗺️ 격자 표시 중... (${this.currentHour}시 기준)`);
        
        // 기존 격자 제거
        this.clearGrids();
        
        if (!this.isVisible) return;
        
        // 각 격자 표시
        this.gridData.grids.forEach(grid => {
            const probability = grid.hourly_fishing_probability[this.currentHour.toString()];
            
            // 확률 기반 색상
            const color = this.getProbabilityColor(probability);
            const radius = this.getProbabilityRadius(probability);
            
            const circle = L.circle([grid.lat, grid.lon], {
                radius: radius,
                color: color,
                fillColor: color,
                fillOpacity: 0.4,
                weight: 2
            }).addTo(this.map);
            
            // 팝업
            circle.bindPopup(this.createPopupContent(grid, probability));
            
            this.gridCircles.push(circle);
        });
        
        console.log(`✅ ${this.gridCircles.length}개 격자 표시 완료`);
    }
    
    createPopupContent(grid, currentProb) {
        // 24시간 중 가장 위험한 시간 찾기
        const hourlyProbs = grid.hourly_fishing_probability;
        let maxHour = 0;
        let maxProb = 0;
        
        Object.keys(hourlyProbs).forEach(hour => {
            if (hourlyProbs[hour] > maxProb) {
                maxProb = hourlyProbs[hour];
                maxHour = parseInt(hour);
            }
        });
        
        return `
            <div style="font-size: 13px; min-width: 200px;">
                <strong style="color: #2c3e50;">🎣 자망 조업 위험도</strong>
                <hr style="margin: 5px 0; border: none; border-top: 1px solid #ddd;">
                
                <div style="margin: 8px 0;">
                    <strong>📍 위치</strong><br>
                    ${grid.lat.toFixed(2)}°N, ${grid.lon.toFixed(2)}°E
                </div>
                
                <div style="margin: 8px 0; padding: 8px; background: ${this.getProbabilityBgColor(currentProb)}; border-radius: 5px;">
                    <strong>현재 시간 (${this.currentHour}시)</strong><br>
                    조업 확률: <strong style="font-size: 16px;">${(currentProb * 100).toFixed(1)}%</strong>
                </div>
                
                <div style="margin: 8px 0;">
                    <strong>⚠️ 가장 위험한 시간</strong><br>
                    ${maxHour}시: ${(maxProb * 100).toFixed(1)}%
                </div>
                
                <div style="margin: 8px 0;">
                    <strong>📊 평균 조업 확률</strong><br>
                    ${(grid.avg_fishing_probability * 100).toFixed(1)}%
                </div>
                
                <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 11px; color: #666;">
                    💡 ${this.getRiskDescription(currentProb)}
                </div>
            </div>
        `;
    }
    
    getRiskDescription(prob) {
        if (prob > 0.7) return "매우 위험합니다. 회피를 권장합니다.";
        if (prob > 0.5) return "위험합니다. 주의가 필요합니다.";
        if (prob > 0.3) return "조업 가능성이 있습니다.";
        return "비교적 안전합니다.";
    }
    
    getProbabilityColor(prob) {
        if (prob > 0.7) return '#E74C3C';      // 빨강 (High)
        if (prob > 0.5) return '#FF6B35';      // 주황-빨강
        if (prob > 0.4) return '#FFA500';      // 주황 (Medium)
        if (prob > 0.3) return '#FFD700';      // 노랑
        return '#50C878';                       // 초록 (Low)
    }
    
    getProbabilityBgColor(prob) {
        if (prob > 0.7) return '#ffebee';
        if (prob > 0.5) return '#fff3e0';
        if (prob > 0.4) return '#fff9c4';
        return '#e8f5e9';
    }
    
    getProbabilityRadius(prob) {
        // 확률에 따라 원 크기 조절 (2km ~ 6km) - 축소!
        return 2000 + (prob * 4000);
    }
    
    clearGrids() {
        this.gridCircles.forEach(circle => this.map.removeLayer(circle));
        this.gridCircles = [];
    }
    
    updateHour(hour) {
        this.currentHour = parseInt(hour);
        this.displayGrids();
        
        const label = document.getElementById('hourLabel');
        if (label) {
            label.textContent = `${this.currentHour}시`;
        }
    }
    
    togglePanelCollapse() {
        const content = document.getElementById('fishingPanelContent');
        const btn = document.getElementById('collapseFishingPanel');
        
        if (content && btn) {
            if (content.style.display === 'none') {
                content.style.display = 'block';
                btn.textContent = '▼';
            } else {
                content.style.display = 'none';
                btn.textContent = '▶';
            }
        }
    }
    
    toggleVisibility() {
        this.isVisible = !this.isVisible;
        
        const btn = document.getElementById('toggleFishingLayer');
        if (btn) {
            if (this.isVisible) {
                btn.innerHTML = '👁️ 레이어 숨기기';
                btn.style.background = '#27ae60';
            } else {
                btn.innerHTML = '👁️ 레이어 보이기';
                btn.style.background = '#95a5a6';
            }
        }
        
        this.displayGrids();
    }
    
    createControls() {
        const controlDiv = L.DomUtil.create('div', 'fishing-risk-controls');
        controlDiv.innerHTML = `
            <div style="background: white; padding: 15px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); min-width: 300px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #e74c3c;">
                    <h4 style="margin: 0; color: #2c3e50;">🎣 어선 조업 위험도</h4>
                    <button id="collapseFishingPanel" style="background: none; border: none; font-size: 20px; cursor: pointer; padding: 0; color: #666;">▼</button>
                </div>
                
                <div id="fishingPanelContent">
                
                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 12px; font-size: 12px;">
                    <div style="margin-bottom: 5px;">
                        <strong>AI 모델:</strong> Random Forest
                    </div>
                    <div style="margin-bottom: 5px;">
                        <strong>정확도:</strong> <span style="color: #27ae60; font-weight: bold;">87.24%</span>
                    </div>
                    <div>
                        <strong>격자 수:</strong> ${this.gridData ? this.gridData.grids.length : 0}개
                    </div>
                </div>
                
                <div style="margin-bottom: 12px;">
                    <label style="font-size: 13px; color: #555; display: block; margin-bottom: 5px;">
                        ⏰ 시간대: <span id="hourLabel" style="font-weight: bold; color: #e74c3c;">${this.currentHour}시</span>
                    </label>
                    <input type="range" id="hourSlider" min="0" max="23" value="${this.currentHour}" 
                           style="width: 100%; cursor: pointer;">
                    <div style="display: flex; justify-content: space-between; font-size: 10px; color: #999; margin-top: 2px;">
                        <span>0시</span>
                        <span>6시</span>
                        <span>12시</span>
                        <span>18시</span>
                        <span>23시</span>
                    </div>
                </div>
                
                <div style="margin-bottom: 12px;">
                    <button id="toggleFishingLayer" style="width: 100%; padding: 10px; background: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px;">
                        👁️ 레이어 숨기기
                    </button>
                </div>
                
                <div style="padding: 10px; background: #fff3cd; border-left: 3px solid #ffc107; border-radius: 3px; font-size: 11px; margin-bottom: 12px;">
                    <strong>💡 사용 팁:</strong><br>
                    슬라이더로 시간대를 바꿔보세요!<br>
                    새벽 3-4시가 가장 위험합니다.
                </div>
                
                <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 11px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">
                        <span style="width: 20px; height: 20px; background: #E74C3C; border-radius: 50%; display: inline-block;"></span>
                        <span>70%+ 매우 위험</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">
                        <span style="width: 20px; height: 20px; background: #FFA500; border-radius: 50%; display: inline-block;"></span>
                        <span>40-70% 위험</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="width: 20px; height: 20px; background: #50C878; border-radius: 50%; display: inline-block;"></span>
                        <span>40% 미만 안전</span>
                    </div>
                </div>
                
                </div>
            </div>
        `;
        
        const CustomControl = L.Control.extend({
            options: { position: 'topleft' },
            onAdd: function() { return controlDiv; }
        });
        
        this.map.addControl(new CustomControl());
        
        // 이벤트 리스너
        setTimeout(() => {
            document.getElementById('hourSlider')?.addEventListener('input', (e) => {
                this.updateHour(e.target.value);
            });
            
            document.getElementById('toggleFishingLayer')?.addEventListener('click', () => {
                this.toggleVisibility();
            });
            
            document.getElementById('collapseFishingPanel')?.addEventListener('click', () => {
                this.togglePanelCollapse();
            });
        }, 100);
    }
}

window.FishingRiskLayer = FishingRiskLayer;

// 자동 초기화
function tryInitFishingRisk() {
    if (typeof map !== 'undefined' && map instanceof L.Map) {
        if (map._loaded) {
            const fishingRisk = new FishingRiskLayer(map);
            window.fishingRisk = fishingRisk;
        } else {
            map.on('load', () => {
                const fishingRisk = new FishingRiskLayer(map);
                window.fishingRisk = fishingRisk;
            });
        }
    } else {
        setTimeout(tryInitFishingRisk, 1000);
    }
}

window.addEventListener('load', () => {
    setTimeout(tryInitFishingRisk, 1500);
});
