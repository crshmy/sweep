// 🌊 기상 시스템 통합 - 메인 컨트롤러
// 기존 app-animated.js와 통합되어 작동

let weatherLayer;
let weatherRouter;
let optimizedRoute = null;

// 기존 초기화 함수 확장
const originalInit = window.addEventListener('DOMContentLoaded', async () => {
    console.log('🌊 기상 통합 시스템 시작...');
    
    // 기존 지도가 초기화될 때까지 대기
    await waitForMap();
    
    // 기상 레이어 초기화
    weatherLayer = new WeatherLayer(map);
    await weatherLayer.init();
    
    // 경로 최적화 시스템 초기화
    weatherRouter = new WeatherAwareRouter(weatherLayer);
    
    // UI 이벤트 연결
    setupWeatherUI();
    
    // 현재 위치 기상 업데이트
    updateCurrentWeather();
    
    // 주기적 업데이트 (10분마다)
    setInterval(() => {
        weatherLayer.refresh();
        updateCurrentWeather();
    }, 10 * 60 * 1000);
    
    console.log('✅ 기상 시스템 준비 완료!');
});

// 지도 초기화 대기
function waitForMap() {
    return new Promise((resolve) => {
        const checkMap = setInterval(() => {
            if (typeof map !== 'undefined' && map) {
                clearInterval(checkMap);
                resolve();
            }
        }, 100);
    });
}

// UI 이벤트 설정
function setupWeatherUI() {
    // 기상 레이어 버튼
    const weatherLayerBtn = document.getElementById('weatherLayerBtn');
    if (weatherLayerBtn) {
        weatherLayerBtn.addEventListener('click', () => {
            const legend = document.getElementById('weatherLegend');
            if (legend.style.display === 'none') {
                legend.style.display = 'block';
            } else {
                legend.style.display = 'none';
            }
        });
    }
    
    // 바람 레이어 토글
    const windLayerCheck = document.getElementById('windLayer');
    if (windLayerCheck) {
        windLayerCheck.addEventListener('change', (e) => {
            const isActive = weatherLayer.toggleWindLayer();
            document.getElementById('weatherStatus').textContent = 
                isActive ? '🌬️ 바람 표시중' : '🌬️ 기상 준비';
        });
    }
    
    // 파도 레이어 토글
    const waveLayerCheck = document.getElementById('waveLayer');
    if (waveLayerCheck) {
        waveLayerCheck.addEventListener('change', (e) => {
            const isActive = weatherLayer.toggleWaveLayer();
            document.getElementById('weatherStatus').textContent = 
                isActive ? '🌊 파도 표시중' : '🌬️ 기상 준비';
        });
    }
    
    // 기상 데이터 갱신 버튼
    const refreshBtn = document.getElementById('refreshWeather');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            refreshBtn.textContent = '⏳ 갱신중...';
            refreshBtn.disabled = true;
            
            await weatherLayer.refresh();
            await updateCurrentWeather();
            
            refreshBtn.textContent = '🔄 기상 데이터 갱신';
            refreshBtn.disabled = false;
            
            // 성공 애니메이션
            refreshBtn.style.background = '#4caf50';
            setTimeout(() => {
                refreshBtn.style.background = '';
            }, 1000);
        });
    }
    
    // 경로 최적화 버튼
    const optimizeBtn = document.getElementById('optimizeRoute');
    if (optimizeBtn) {
        optimizeBtn.addEventListener('click', async () => {
            await calculateOptimalRoute();
        });
    }
}

// 현재 위치 기상 정보 업데이트
async function updateCurrentWeather() {
    if (!myVessel || !weatherLayer) return;
    
    try {
        const weather = await weatherLayer.getWeatherAt(
            myVessel.position[0], 
            myVessel.position[1]
        );
        
        if (weather) {
            // UI 업데이트
            updateWeatherUI(weather);
            
            // 상태 표시
            document.getElementById('weatherStatus').textContent = 
                `🌬️ ${weather.wind.speed.toFixed(1)} m/s`;
        }
    } catch (error) {
        console.error('기상 정보 업데이트 실패:', error);
        document.getElementById('weatherStatus').textContent = 
            '⚠️ 기상 오류';
    }
}

// 기상 UI 업데이트
function updateWeatherUI(weather) {
    // 온도
    const tempEl = document.getElementById('weatherTemp');
    if (tempEl) {
        tempEl.textContent = `${Math.round(weather.temperature)}°C`;
    }
    
    // 날씨 아이콘
    const iconEl = document.getElementById('weatherIcon');
    if (iconEl) {
        iconEl.textContent = getWeatherIcon(weather.wind.speed);
    }
    
    // 풍향
    const dirEl = document.getElementById('windDirection');
    if (dirEl) {
        const direction = degreesToDirection(weather.wind.direction);
        dirEl.textContent = `${direction} ${Math.round(weather.wind.direction)}°`;
    }
    
    // 풍속
    const speedEl = document.getElementById('windSpeed');
    if (speedEl) {
        speedEl.textContent = `${weather.wind.speed.toFixed(1)} m/s`;
        
        // 색상 변경 (위험도)
        if (weather.wind.speed > 15) {
            speedEl.style.color = '#f44336';
        } else if (weather.wind.speed > 10) {
            speedEl.style.color = '#ff9800';
        } else {
            speedEl.style.color = '#fff';
        }
    }
    
    // 파고
    const waveEl = document.getElementById('waveHeight');
    if (waveEl) {
        waveEl.textContent = `${weather.waves.height.toFixed(1)} m`;
        
        // 색상 변경
        if (weather.waves.height > 2.5) {
            waveEl.style.color = '#f44336';
        } else if (weather.waves.height > 1.5) {
            waveEl.style.color = '#ff9800';
        } else {
            waveEl.style.color = '#fff';
        }
    }
    
    // 가시거리
    const visEl = document.getElementById('visibility');
    if (visEl) {
        visEl.textContent = `${weather.visibility.toFixed(1)} km`;
    }
}

// 최적 경로 계산
async function calculateOptimalRoute() {
    if (!weatherRouter || !myVessel || !hotspots) {
        console.error('경로 계산 준비 안 됨');
        return;
    }
    
    const optimizeBtn = document.getElementById('optimizeRoute');
    optimizeBtn.textContent = '⏳ 경로 계산중...';
    optimizeBtn.disabled = true;
    
    try {
        // 기상 데이터 최신화
        await weatherLayer.refresh();
        
        // 경로 계산
        optimizedRoute = await weatherRouter.calculateOptimalRoute(
            myVessel.position,
            hotspots,
            myVessel.position
        );
        
        // 지도에 경로 그리기
        weatherRouter.drawRoute(map, optimizedRoute, '#2196f3');
        
        // UI 업데이트
        updateRouteUI(optimizedRoute);
        
        // 성공 알림
        addAlert('info', '✅ 경로 계산 완료', 
            `기상 조건을 반영한 최적 경로가 생성되었습니다.`);
        
        console.log('✅ 최적 경로:', optimizedRoute);
        
    } catch (error) {
        console.error('경로 계산 실패:', error);
        addAlert('danger', '❌ 경로 계산 실패', 
            '경로 계산 중 오류가 발생했습니다.');
    } finally {
        optimizeBtn.textContent = '🧭 기상 기반 경로 계산';
        optimizeBtn.disabled = false;
    }
}

// 경로 정보 UI 업데이트
function updateRouteUI(route) {
    const summary = weatherRouter.getRouteSummary(route);
    
    // 총 거리
    const distEl = document.getElementById('totalDistance');
    if (distEl) {
        distEl.textContent = summary.distance;
    }
    
    // 예상 시간
    const timeEl = document.getElementById('estimatedTime');
    if (timeEl) {
        timeEl.textContent = summary.time;
    }
    
    // 핫스팟 개수
    const countEl = document.getElementById('hotspotCount');
    if (countEl) {
        countEl.textContent = `${summary.waypoints}개 지점`;
    }
}

// 날씨 아이콘 선택
function getWeatherIcon(windSpeed) {
    if (windSpeed < 2) return '☀️';
    if (windSpeed < 6) return '🌤️';
    if (windSpeed < 10) return '⛅';
    if (windSpeed < 15) return '🌥️';
    if (windSpeed < 20) return '🌧️';
    return '⛈️';
}

// 각도를 방향으로 변환
function degreesToDirection(degrees) {
    const directions = ['북', '북동', '동', '남동', '남', '남서', '서', '북서'];
    const index = Math.round(degrees / 45) % 8;
    return directions[index];
}

// 알림 추가 (기존 시스템과 통합)
function addAlert(type, title, message) {
    const alertList = document.getElementById('alertList');
    if (!alertList) return;
    
    const icons = {
        'info': 'ℹ️',
        'warning': '⚠️',
        'danger': '🚨'
    };
    
    const item = document.createElement('div');
    item.className = `alert-item ${type} alert-slide-in`;
    item.innerHTML = `
        <div class="alert-icon">${icons[type] || 'ℹ️'}</div>
        <div class="alert-content">
            <div class="alert-title">${title}</div>
            <div class="alert-message">${message}</div>
            <div class="alert-time">방금 전</div>
        </div>
    `;
    
    // 맨 위에 추가
    alertList.insertBefore(item, alertList.firstChild);
    
    // 최대 5개만 유지
    while (alertList.children.length > 5) {
        alertList.removeChild(alertList.lastChild);
    }
}

// 기상 경고 자동 감지
function checkWeatherWarnings() {
    if (!myVessel || !weatherLayer) return;
    
    weatherLayer.getWeatherAt(myVessel.position[0], myVessel.position[1])
        .then(weather => {
            if (!weather) return;
            
            // 강풍 경고
            if (weather.wind.speed > 15) {
                addAlert('warning', '⚠️ 강풍 주의', 
                    `현재 풍속 ${weather.wind.speed.toFixed(1)} m/s - 작업 시 주의하세요`);
            }
            
            // 높은 파도 경고
            if (weather.waves.height > 2.5) {
                addAlert('warning', '🌊 높은 파도', 
                    `현재 파고 ${weather.waves.height.toFixed(1)} m - 안전에 유의하세요`);
            }
            
            // 위험 수준
            if (weather.wind.speed > 20 || weather.waves.height > 3.5) {
                addAlert('danger', '🚨 작업 중단 권고', 
                    '기상 조건이 위험 수준입니다. 안전한 곳으로 이동하세요.');
            }
        });
}

// 주기적 기상 경고 체크 (5분마다)
setInterval(checkWeatherWarnings, 5 * 60 * 1000);

console.log('🌊 기상 통합 모듈 로드 완료');
