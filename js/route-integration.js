// 🧭 경로 계산 통합 시스템 - 발표용 완전판
// 실제 선박 위치 사용 + 자세한 로그

console.log('📦 route-integration.js 시작...');

(function() {
    console.log('🧭 경로 계산 시스템 초기화 중...');
    
    // 전역 변수 대기
    const initRouteSystem = setInterval(() => {
        if (typeof map === 'undefined' || 
            typeof weatherLayer === 'undefined' || 
            typeof hotspotLayer === 'undefined' ||
            typeof WeatherAwareRouter === 'undefined' ||
            typeof myVessel === 'undefined') {
            console.log('⏳ 필수 객체 로딩 대기중...', {
                map: typeof map !== 'undefined',
                weatherLayer: typeof weatherLayer !== 'undefined',
                hotspotLayer: typeof hotspotLayer !== 'undefined',
                WeatherAwareRouter: typeof WeatherAwareRouter !== 'undefined',
                myVessel: typeof myVessel !== 'undefined'
            });
            return;
        }
        
        clearInterval(initRouteSystem);
        console.log('✅ 모든 객체 로딩 완료! 경로 시스템 시작');
        
        // 경로 최적화 시스템 초기화
        const router = new WeatherAwareRouter(weatherLayer);
        let currentRoute = null;
        let routeLayer = null;
        
        console.log('🔍 버튼 찾는 중...');
        
        // 🎯 버튼 클릭 이벤트
        const optimizeBtn = document.getElementById('optimizeRoute');
        
        if (!optimizeBtn) {
            console.error('❌ optimizeRoute 버튼을 찾을 수 없습니다!');
            return;
        }
        
        console.log('✅ 버튼 발견!', optimizeBtn);
        
        optimizeBtn.addEventListener('click', async function() {
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.log('🧭 경로 계산 시작!');
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            
            // 버튼 상태 변경
            optimizeBtn.disabled = true;
            optimizeBtn.innerHTML = '⏳ 계산 중...';
            optimizeBtn.style.background = 'linear-gradient(135deg, #607d8b, #455a64)';
            
            try {
                // 1. 현재 선박 위치 (실제 myVessel 사용)
                console.log('');
                console.log('📍 [1단계] 출발 위치 확인');
                console.log('─────────────────────────────────────────');
                
                const startPosition = myVessel.position;
                console.log('✅ 실제 선박(sweep-1호) 위치 사용');
                console.log('   위도:', startPosition[0].toFixed(6), '°N');
                console.log('   경도:', startPosition[1].toFixed(6), '°E');
                console.log('   선박명:', myVessel.name);
                console.log('   현재 속도:', myVessel.speed, 'knots');
                console.log('   현재 방향:', myVessel.heading, '°');
                
                // 2. 핫스팟 데이터 가져오기
                console.log('');
                console.log('🗑️ [2단계] 쓰레기 핫스팟 데이터 로드');
                console.log('─────────────────────────────────────────');
                
                const allHotspots = hotspotLayer.getAllHotspots();
                
                if (!allHotspots || allHotspots.length === 0) {
                    throw new Error('핫스팟 데이터가 없습니다');
                }
                
                console.log(`✅ 총 ${allHotspots.length}개 핫스팟 발견`);
                console.log('핫스팟 샘플 (상위 3개):');
                allHotspots.slice(0, 3).forEach((h, i) => {
                    console.log(`   ${i+1}. ${h.name} - 밀집도: ${h.density.toFixed(2)}, 우선순위: ${h.priority}`);
                });
                
                // 3. 상위 5개 선택 (발표용)
                console.log('');
                console.log('🎯 [3단계] 최적 핫스팟 선택');
                console.log('─────────────────────────────────────────');
                
                const topHotspots = allHotspots
                    .sort((a, b) => (b.density || 0) - (a.density || 0))
                    .slice(0, 5);
                
                console.log('✅ 상위 5개 핫스팟 선택 (밀집도 순):');
                topHotspots.forEach((h, i) => {
                    const distance = calculateDistanceKm(startPosition, [h.lat, h.lon]);
                    console.log(`   ${i+1}. ${h.name}`);
                    console.log(`      - 위치: ${h.lat.toFixed(4)}°N, ${h.lon.toFixed(4)}°E`);
                    console.log(`      - 밀집도: ${h.density.toFixed(2)}`);
                    console.log(`      - 우선순위: ${h.priority}`);
                    console.log(`      - 출발지로부터 거리: ${distance.toFixed(2)} km`);
                });
                
                // 4. 경로 계산
                console.log('');
                console.log('🔍 [4단계] A* 알고리즘 경로 계산');
                console.log('─────────────────────────────────────────');
                console.log('알고리즘: A* (기상 데이터 + 육지 회피)');
                console.log('고려 요소:');
                console.log('   - 🏝️ 육지 회피 (비용: 99999)');
                console.log('   - 풍속 (위험: >20 m/s)');
                console.log('   - 파고 (위험: >3.0 m)');
                console.log('   - 최단 거리');
                console.log('   - 핫스팟 우선순위');
                console.log('경로 타입: 🔄 왕복 (출발지 → 핫스팟들 → 출발지)');
                console.log('');
                console.log('계산 중...');
                
                const route = await router.calculateOptimalRoute(
                    startPosition, 
                    topHotspots, 
                    startPosition,
                    true  // ✅ 왕복 경로 활성화!
                );
                
                console.log('');
                console.log('✅ 경로 계산 완료!');
                console.log('   경로 포인트 수:', route.path.length, '개');
                console.log('   총 거리:', route.totalDistance.toFixed(2), 'km');
                console.log('   예상 시간:', route.totalTime.toFixed(2), '시간');
                console.log('   경유지 수:', route.waypoints.length, '개');
                console.log('   세그먼트 수:', route.segments.length, '개');
                
                // 5. 경로 상세 정보
                console.log('');
                console.log('📊 [5단계] 경로 상세 정보');
                console.log('─────────────────────────────────────────');
                console.log('경유 순서:');
                route.waypoints.forEach((wp, idx) => {
                    console.log(`   ${idx + 1}. ${wp.name || `핫스팟 ${idx + 1}`}`);
                    console.log(`      위치: ${wp.lat.toFixed(4)}°N, ${wp.lon.toFixed(4)}°E`);
                    console.log(`      밀집도: ${wp.density}`);
                });
                
                console.log('');
                console.log('구간별 거리:');
                let cumulativeDistance = 0;
                route.segments.forEach((seg, idx) => {
                    cumulativeDistance += seg.cost;
                    console.log(`   구간 ${idx + 1}: ${seg.cost.toFixed(2)} km (누적: ${cumulativeDistance.toFixed(2)} km)`);
                });
                
                // 6. 기존 경로 제거
                if (routeLayer) {
                    map.removeLayer(routeLayer);
                    console.log('');
                    console.log('🗑️ 기존 경로 제거');
                }
                
                // 7. 새 경로 그리기
                console.log('');
                console.log('🎨 [6단계] 지도에 경로 표시');
                console.log('─────────────────────────────────────────');
                console.log('경로 색상: 청록색 (#00bcd4)');
                console.log('경로 두께: 4px');
                console.log('경유지 마커: 1, 2, 3, 4, 5');
                
                routeLayer = router.drawRoute(map, route, '#00bcd4');
                console.log('✅ 지도 표시 완료');
                
                // 8. UI 업데이트
                console.log('');
                console.log('📱 [7단계] UI 업데이트');
                console.log('─────────────────────────────────────────');
                
                const summary = router.getRouteSummary(route);
                console.log('요약 정보:', summary);
                
                document.getElementById('totalDistance').textContent = summary.distance;
                document.getElementById('estimatedTime').textContent = summary.time;
                document.getElementById('hotspotCount').textContent = `${summary.waypoints}개 지점`;
                
                console.log('✅ UI 업데이트 완료');
                
                // 9. 지도 중심 이동
                console.log('');
                console.log('🗺️ [8단계] 지도 뷰 조정');
                console.log('─────────────────────────────────────────');
                
                if (route.path && route.path.length > 0) {
                    const bounds = L.latLngBounds(route.path);
                    map.fitBounds(bounds, { padding: [50, 50] });
                    console.log('✅ 전체 경로가 보이도록 지도 조정');
                }
                
                // 10. 알림 추가
                addRouteAlert(summary);
                
                // 11. 성공 메시지
                console.log('');
                console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                console.log('🎉 경로 계산 완료!');
                console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                console.log('총 거리:', summary.distance);
                console.log('예상 시간:', summary.time);
                console.log('경유지:', summary.waypoints, '개');
                console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                
                optimizeBtn.innerHTML = '✅ 경로 계산 완료!';
                optimizeBtn.style.background = 'linear-gradient(135deg, #4caf50, #388e3c)';
                
                setTimeout(() => {
                    optimizeBtn.innerHTML = '🧭 기상 기반 경로 재계산';
                    optimizeBtn.style.background = '';
                    optimizeBtn.disabled = false;
                }, 3000);
                
                currentRoute = route;
                
            } catch (error) {
                console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                console.error('❌ 경로 계산 실패!');
                console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                console.error('에러 메시지:', error.message);
                console.error('에러 스택:', error.stack);
                console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                
                optimizeBtn.innerHTML = '❌ 계산 실패';
                optimizeBtn.style.background = 'linear-gradient(135deg, #f44336, #c62828)';
                
                setTimeout(() => {
                    optimizeBtn.innerHTML = '🧭 기상 기반 경로 계산';
                    optimizeBtn.style.background = '';
                    optimizeBtn.disabled = false;
                }, 3000);
                
                // 에러 알림
                addAlert('error', `경로 계산 실패: ${error.message}`);
            }
        });
        
        console.log('✅ 경로 계산 버튼 연결 완료!');
        
        // 거리 계산 헬퍼 함수
        function calculateDistanceKm(pos1, pos2) {
            const R = 6371;
            const lat1 = pos1[0] * Math.PI / 180;
            const lat2 = pos2[0] * Math.PI / 180;
            const deltaLat = (pos2[0] - pos1[0]) * Math.PI / 180;
            const deltaLon = (pos2[1] - pos1[1]) * Math.PI / 180;

            const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
                      Math.cos(lat1) * Math.cos(lat2) *
                      Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
            
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
            return R * c;
        }
        
        // ⚠️ 알림 추가 함수
        function addAlert(type, message) {
            const alertList = document.getElementById('alertList');
            if (!alertList) return;
            
            const colors = {
                'success': { bg: 'rgba(76, 175, 80, 0.2)', border: '#4caf50', icon: '✅' },
                'warning': { bg: 'rgba(255, 152, 0, 0.2)', border: '#ff9800', icon: '⚠️' },
                'error': { bg: 'rgba(244, 67, 54, 0.2)', border: '#f44336', icon: '❌' },
                'info': { bg: 'rgba(33, 150, 243, 0.2)', border: '#2196f3', icon: 'ℹ️' }
            };
            
            const style = colors[type] || colors['info'];
            
            const item = document.createElement('div');
            item.style.cssText = `
                background: ${style.bg};
                border-left: 4px solid ${style.border};
                padding: 12px;
                margin-bottom: 10px;
                border-radius: 8px;
                display: flex;
                gap: 10px;
                animation: alert-slide 0.3s ease-out;
            `;
            
            item.innerHTML = `
                <div style="font-size: 20px;">${style.icon}</div>
                <div style="flex: 1;">
                    <div style="font-weight: bold; color: #fff; margin-bottom: 4px;">${message}</div>
                    <div style="font-size: 11px; color: #78909c; margin-top: 4px;">방금 전</div>
                </div>
            `;
            
            alertList.insertBefore(item, alertList.firstChild);
            
            // 오래된 알림 제거 (최대 5개)
            while (alertList.children.length > 5) {
                alertList.removeChild(alertList.lastChild);
            }
        }
        
        // 🎉 경로 계산 완료 알림
        function addRouteAlert(summary) {
            addAlert('success', `
                🧭 최적 경로 계산 완료!<br>
                <span style="font-size: 13px; color: #b0bec5;">
                거리: ${summary.distance} | 시간: ${summary.time}
                </span>
            `);
        }
        
    }, 500);
    
})();

console.log('📦 route-integration.js 로드 완료');
