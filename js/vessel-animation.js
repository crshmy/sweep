/**
 * 실제 어선 궤적 애니메이션 v2
 * 날짜 구간 감지 + 간격 표시
 */

class VesselAnimationLayer {
    constructor(map) {
        this.map = map;
        this.vessels = [];
        this.vesselMarkers = new Map();
        this.vesselPaths = new Map();
        this.isPlaying = false;
        this.currentTimeIndex = 0;
        this.animationSpeed = 1000;
        this.animationInterval = null;
        this.segments = [];  // 날짜 구간
        this.currentSegment = 0;
        this.isLayerVisible = true;
        
        console.log('🚢 VesselAnimationLayer v2 초기화...');
        this.loadVesselData();
    }
    
    async loadVesselData() {
        try {
            console.log('📡 어선 데이터 로딩 중...');
            const response = await fetch('data/vessel_trajectories.json');
            const data = await response.json();
            
            this.vessels = data.vessels;
            console.log(`✅ ${this.vessels.length}척 로딩 완료`);
            
            // 날짜 구간 분석
            this.analyzeTimeSegments();
            
            this.createControls();
            this.initializeVessels();
            
        } catch (error) {
            console.error('❌ 어선 데이터 로딩 실패:', error);
        }
    }
    
    analyzeTimeSegments() {
        console.log('📅 날짜 구간 분석 중...');
        
        if (this.vessels.length === 0) return;
        
        const path = this.vessels[0].path;
        let currentSegment = {
            start: 0,
            end: 0,
            startTime: path[0].timestamp,
            endTime: path[0].timestamp
        };
        
        for (let i = 1; i < path.length; i++) {
            const t1 = new Date(path[i-1].timestamp);
            const t2 = new Date(path[i].timestamp);
            const gapHours = (t2 - t1) / (1000 * 60 * 60);
            
            // 1시간 이상 간격이면 새 구간
            if (gapHours > 1) {
                currentSegment.end = i - 1;
                currentSegment.endTime = path[i-1].timestamp;
                this.segments.push({...currentSegment});
                
                // 새 구간 시작
                currentSegment = {
                    start: i,
                    end: i,
                    startTime: path[i].timestamp,
                    endTime: path[i].timestamp,
                    gapDays: gapHours / 24
                };
            } else {
                currentSegment.end = i;
                currentSegment.endTime = path[i].timestamp;
            }
        }
        
        // 마지막 구간
        this.segments.push(currentSegment);
        
        console.log(`✅ ${this.segments.length}개 구간 발견`);
        this.segments.forEach((seg, idx) => {
            const duration = (new Date(seg.endTime) - new Date(seg.startTime)) / (1000 * 60 * 60);
            console.log(`구간 ${idx+1}: ${seg.startTime} ~ ${seg.endTime} (${duration.toFixed(1)}시간, ${seg.end - seg.start + 1}개 포인트)`);
        });
    }
    
    initializeVessels() {
        console.log('🎯 어선 마커 생성 중...');
        
        this.vessels.forEach((vessel) => {
            const firstPoint = vessel.path[0];
            
            const marker = L.circleMarker([firstPoint.lat, firstPoint.lon], {
                radius: 10,
                fillColor: this.getColorByBehavior(firstPoint.behavior),
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.9
            }).addTo(this.map);
            
            marker.bindPopup(this.createPopupContent(vessel, firstPoint));
            
            this.vesselMarkers.set(vessel.vessel_id, marker);
            
            const pathLine = L.polyline([], {
                color: '#3388ff',
                weight: 3,
                opacity: 0.6,
                dashArray: '10, 5'
            }).addTo(this.map);
            
            this.vesselPaths.set(vessel.vessel_id, {
                line: pathLine,
                coordinates: []
            });
        });
        
        console.log('✅ 어선 마커 초기화 완료!');
        
        if (this.vessels.length > 0) {
            const firstPoint = this.vessels[0].path[0];
            this.map.setView([firstPoint.lat, firstPoint.lon], 11);
        }
    }
    
    createPopupContent(vessel, point) {
        return `
            <div style="font-size: 13px;">
                <strong style="color: #2c3e50;">${vessel.vessel_name}</strong><br>
                <span style="color: #e74c3c;">●</span> ${point.behavior_name}<br>
                <hr style="margin: 5px 0; border: none; border-top: 1px solid #ddd;">
                📍 위치: ${point.lat.toFixed(4)}°N, ${point.lon.toFixed(4)}°E<br>
                🚢 속도: ${point.sog} knots<br>
                ⏰ 시간: ${point.timestamp}
            </div>
        `;
    }
    
    getColorByBehavior(behavior) {
        const colors = {
            0: '#4A90E2',  // 항해중
            1: '#50C878',  // 귀항중
            2: '#FFB347',  // 조업지이동
            3: '#E74C3C',  // 조업중
            4: '#95A5A6',  // 정박
            5: '#9B59B6',  // 출항
            6: '#BDC3C7'   // 기타
        };
        return colors[behavior] || '#3498DB';
    }
    
    createControls() {
        const controlDiv = L.DomUtil.create('div', 'vessel-animation-controls');
        controlDiv.innerHTML = `
            <div style="background: white; padding: 15px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); min-width: 280px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #3498db;">
                    <h4 style="margin: 0; color: #2c3e50;">🚢 어선 실시간 추적</h4>
                    <button id="collapseVesselPanel" style="background: none; border: none; font-size: 20px; cursor: pointer; padding: 0; color: #666;">▼</button>
                </div>
                
                <div id="vesselPanelContent">
                
                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 12px; font-size: 12px;">
                    <div style="margin-bottom: 5px;">
                        <strong>📅 현재 구간:</strong> <span id="currentSegmentInfo">구간 1</span>
                    </div>
                    <div id="segmentDetails" style="color: #666; font-size: 11px; margin-top: 5px;">
                        로딩 중...
                    </div>
                    <div id="gapWarning" style="margin-top: 8px; padding: 8px; background: #fff3cd; border-left: 3px solid #ffc107; border-radius: 3px; display: none;">
                        <strong>⚠️ 데이터 간격:</strong> <span id="gapInfo"></span>
                    </div>
                </div>
                
                <div style="margin-bottom: 12px;">
                    <button id="toggleVesselLayer" style="width: 100%; padding: 10px; margin-bottom: 8px; background: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: bold;">
                        👁️ 어선 레이어 숨기기
                    </button>
                </div>
                
                <div id="vesselControls" style="margin-bottom: 12px;">
                    <button id="playPauseBtn" style="padding: 10px 20px; margin-right: 5px; background: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: bold;">
                        ▶️ 재생
                    </button>
                    <button id="resetBtn" style="padding: 10px 15px; margin-right: 5px; background: #e74c3c; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px;">
                        🔄
                    </button>
                    <button id="nextSegmentBtn" style="padding: 10px 15px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px;">
                        ⏭️
                    </button>
                </div>
                
                <div style="margin-bottom: 12px;">
                    <label style="font-size: 12px; color: #555; display: block; margin-bottom: 5px;">
                        재생 속도: <span id="speedLabel" style="font-weight: bold; color: #3498db;">1x</span>
                    </label>
                    <input type="range" id="speedSlider" min="1" max="20" value="1" 
                           style="width: 100%; cursor: pointer;">
                </div>
                
                <div style="padding: 10px; background: #ecf0f1; border-radius: 5px; font-size: 12px;">
                    <div id="timeDisplay" style="margin: 3px 0; color: #2c3e50;">⏰ 시간: 대기중...</div>
                    <div id="progressDisplay" style="margin: 3px 0; color: #7f8c8d;">📊 진행: 0%</div>
                </div>
                
                <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 11px;">
                    <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                        <span><span style="color: #E74C3C; font-size: 16px;">●</span> 조업중</span>
                        <span><span style="color: #4A90E2; font-size: 16px;">●</span> 항해중</span>
                        <span><span style="color: #50C878; font-size: 16px;">●</span> 귀항중</span>
                    </div>
                </div>
                
                </div>
            </div>
        `;
        
        const CustomControl = L.Control.extend({
            options: { position: 'topright' },
            onAdd: function() { return controlDiv; }
        });
        
        this.map.addControl(new CustomControl());
        
        setTimeout(() => {
            document.getElementById('collapseVesselPanel')?.addEventListener('click', () => this.togglePanelCollapse());
            document.getElementById('toggleVesselLayer')?.addEventListener('click', () => this.toggleLayerVisibility());
            document.getElementById('playPauseBtn')?.addEventListener('click', () => this.togglePlayPause());
            document.getElementById('resetBtn')?.addEventListener('click', () => this.reset());
            document.getElementById('nextSegmentBtn')?.addEventListener('click', () => this.nextSegment());
            document.getElementById('speedSlider')?.addEventListener('input', (e) => this.setSpeed(e.target.value));
            
            this.updateSegmentInfo();
        }, 100);
    }
    
    togglePanelCollapse() {
        const content = document.getElementById('vesselPanelContent');
        const btn = document.getElementById('collapseVesselPanel');
        
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
    
    toggleLayerVisibility() {
        this.isLayerVisible = !this.isLayerVisible;
        
        const btn = document.getElementById('toggleVesselLayer');
        const controls = document.getElementById('vesselControls');
        
        if (this.isLayerVisible) {
            // 보이기
            btn.innerHTML = '👁️ 어선 레이어 숨기기';
            btn.style.background = '#27ae60';
            if (controls) controls.style.display = 'block';
            
            // 마커와 경로 보이기
            this.vesselMarkers.forEach(marker => marker.addTo(this.map));
            this.vesselPaths.forEach(pathData => pathData.line.addTo(this.map));
        } else {
            // 숨기기
            btn.innerHTML = '👁️ 어선 레이어 보이기';
            btn.style.background = '#95a5a6';
            if (controls) controls.style.display = 'none';
            
            // 일시정지
            this.pause();
            
            // 마커와 경로 숨기기
            this.vesselMarkers.forEach(marker => this.map.removeLayer(marker));
            this.vesselPaths.forEach(pathData => this.map.removeLayer(pathData.line));
        }
        
        console.log(`👁️ 어선 레이어: ${this.isLayerVisible ? '보이기' : '숨기기'}`);
    }
    
    updateSegmentInfo() {
        if (this.segments.length === 0) return;
        
        const seg = this.segments[this.currentSegment];
        const duration = (new Date(seg.endTime) - new Date(seg.startTime)) / (1000 * 60 * 60);
        
        const info = document.getElementById('currentSegmentInfo');
        if (info) {
            info.textContent = `구간 ${this.currentSegment + 1}/${this.segments.length}`;
        }
        
        const details = document.getElementById('segmentDetails');
        if (details) {
            details.innerHTML = `
                시작: ${seg.startTime}<br>
                종료: ${seg.endTime}<br>
                길이: ${duration.toFixed(1)}시간 (${seg.end - seg.start + 1}개 포인트)
            `;
        }
        
        // 다음 구간과의 간격 표시
        const gapWarning = document.getElementById('gapWarning');
        const gapInfo = document.getElementById('gapInfo');
        
        if (this.currentSegment < this.segments.length - 1) {
            const nextSeg = this.segments[this.currentSegment + 1];
            if (nextSeg.gapDays) {
                if (gapWarning) gapWarning.style.display = 'block';
                if (gapInfo) gapInfo.textContent = `다음 구간까지 ${nextSeg.gapDays.toFixed(1)}일`;
            } else {
                if (gapWarning) gapWarning.style.display = 'none';
            }
        } else {
            if (gapWarning) gapWarning.style.display = 'none';
        }
    }
    
    nextSegment() {
        if (this.currentSegment >= this.segments.length - 1) {
            console.log('마지막 구간입니다');
            return;
        }
        
        this.pause();
        this.currentSegment++;
        this.currentTimeIndex = this.segments[this.currentSegment].start;
        
        // 경로 초기화
        this.vesselPaths.forEach(pathData => {
            pathData.coordinates = [];
            pathData.line.setLatLngs([]);
        });
        
        // 마커를 새 구간 시작 위치로
        this.vessels.forEach(vessel => {
            const point = vessel.path[this.currentTimeIndex];
            const marker = this.vesselMarkers.get(vessel.vessel_id);
            
            if (marker && point) {
                marker.setLatLng([point.lat, point.lon]);
                marker.setStyle({
                    fillColor: this.getColorByBehavior(point.behavior)
                });
                this.map.setView([point.lat, point.lon], this.map.getZoom());
            }
        });
        
        this.updateSegmentInfo();
        this.updateDisplay();
        
        console.log(`⏭️ 구간 ${this.currentSegment + 1}로 이동`);
    }
    
    togglePlayPause() {
        const btn = document.getElementById('playPauseBtn');
        
        if (this.isPlaying) {
            this.pause();
            if (btn) btn.innerHTML = '▶️ 재생';
        } else {
            this.play();
            if (btn) btn.innerHTML = '⏸️ 일시정지';
        }
    }
    
    play() {
        if (this.vessels.length === 0) return;
        
        this.isPlaying = true;
        this.animationInterval = setInterval(() => this.updateFrame(), this.animationSpeed);
        console.log('▶️ 재생 시작');
    }
    
    pause() {
        this.isPlaying = false;
        if (this.animationInterval) {
            clearInterval(this.animationInterval);
        }
    }
    
    reset() {
        this.pause();
        this.currentSegment = 0;
        this.currentTimeIndex = 0;
        
        this.vesselPaths.forEach(pathData => {
            pathData.coordinates = [];
            pathData.line.setLatLngs([]);
        });
        
        this.vessels.forEach(vessel => {
            const firstPoint = vessel.path[0];
            const marker = this.vesselMarkers.get(vessel.vessel_id);
            
            if (marker) {
                marker.setLatLng([firstPoint.lat, firstPoint.lon]);
                marker.setStyle({
                    fillColor: this.getColorByBehavior(firstPoint.behavior)
                });
            }
        });
        
        this.updateSegmentInfo();
        this.updateDisplay();
        
        const btn = document.getElementById('playPauseBtn');
        if (btn) btn.innerHTML = '▶️ 재생';
    }
    
    setSpeed(speed) {
        const speedValue = parseInt(speed);
        this.animationSpeed = 1000 / speedValue;
        
        const label = document.getElementById('speedLabel');
        if (label) label.textContent = `${speedValue}x`;
        
        if (this.isPlaying) {
            clearInterval(this.animationInterval);
            this.animationInterval = setInterval(() => this.updateFrame(), this.animationSpeed);
        }
    }
    
    updateFrame() {
        // 현재 구간 끝에 도달하면 일시정지
        const currentSeg = this.segments[this.currentSegment];
        if (this.currentTimeIndex > currentSeg.end) {
            this.pause();
            const btn = document.getElementById('playPauseBtn');
            if (btn) btn.innerHTML = '▶️ 재생';
            console.log(`✅ 구간 ${this.currentSegment + 1} 완료`);
            return;
        }
        
        this.vessels.forEach(vessel => {
            if (this.currentTimeIndex >= vessel.path.length) return;
            
            const currentPoint = vessel.path[this.currentTimeIndex];
            const marker = this.vesselMarkers.get(vessel.vessel_id);
            const pathData = this.vesselPaths.get(vessel.vessel_id);
            
            if (marker && currentPoint) {
                marker.setLatLng([currentPoint.lat, currentPoint.lon]);
                marker.setStyle({
                    fillColor: this.getColorByBehavior(currentPoint.behavior)
                });
                marker.setPopupContent(this.createPopupContent(vessel, currentPoint));
                
                pathData.coordinates.push([currentPoint.lat, currentPoint.lon]);
                pathData.line.setLatLngs(pathData.coordinates);
            }
        });
        
        this.currentTimeIndex++;
        this.updateDisplay();
    }
    
    updateDisplay() {
        const timeDisplay = document.getElementById('timeDisplay');
        const progressDisplay = document.getElementById('progressDisplay');
        
        if (this.vessels.length > 0 && this.vessels[0].path[this.currentTimeIndex]) {
            const currentPoint = this.vessels[0].path[this.currentTimeIndex];
            if (timeDisplay) {
                timeDisplay.textContent = `⏰ ${currentPoint.timestamp}`;
            }
        }
        
        const currentSeg = this.segments[this.currentSegment];
        if (currentSeg) {
            const segmentProgress = ((this.currentTimeIndex - currentSeg.start) / (currentSeg.end - currentSeg.start) * 100);
            if (progressDisplay) {
                progressDisplay.textContent = `📊 구간 진행: ${segmentProgress.toFixed(1)}%`;
            }
        }
    }
}

window.VesselAnimationLayer = VesselAnimationLayer;

function tryInitVesselAnimation() {
    if (typeof map !== 'undefined' && map instanceof L.Map) {
        if (map._loaded) {
            const vesselAnimation = new VesselAnimationLayer(map);
            window.vesselAnimation = vesselAnimation;
        } else {
            map.on('load', () => {
                const vesselAnimation = new VesselAnimationLayer(map);
                window.vesselAnimation = vesselAnimation;
            });
        }
    } else {
        setTimeout(tryInitVesselAnimation, 1000);
    }
}

window.addEventListener('load', () => {
    setTimeout(tryInitVesselAnimation, 1000);
});
