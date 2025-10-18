// 고급 애니메이션 버전 - 모든 선박이 실시간으로 움직입니다!

// 전역 변수
let map;
let animationFrame;
let vessels = []; // 모든 선박 정보
let trails = {}; // 선박 경로 자취

// 내 선박 초기 위치 및 설정
const myVessel = {
    id: 'my-vessel',
    name: '클린오션-1호',
    position: [35.1796, 129.0756],
    targetPosition: [35.1796, 129.0756],
    speed: 12, // knots
    heading: 45,
    marker: null,
    route: [], // 이동할 경로
    currentRouteIndex: 0,
    trail: [],
    maxTrailLength: 50,
    color: '#2196f3'
};

// 가짜 AIS 선박들 - 각자 다른 경로로 움직임
const aisVessels = [
    {
        id: 'ais-1',
        name: '화물선 OCEAN-1',
        type: '화물선',
        position: [35.19, 129.08],
        targetPosition: [35.19, 129.08],
        speed: 14,
        heading: 125,
        marker: null,
        route: [
            [35.19, 129.08],
            [35.21, 129.12],
            [35.23, 129.16],
            [35.25, 129.14]
        ],
        currentRouteIndex: 0,
        trail: [],
        maxTrailLength: 30,
        color: '#64b5f6'
    },
    {
        id: 'ais-2',
        name: '어선 해풍호',
        type: '어선',
        position: [35.17, 129.1],
        targetPosition: [35.17, 129.1],
        speed: 8,
        heading: 270,
        marker: null,
        route: [
            [35.17, 129.1],
            [35.16, 129.05],
            [35.15, 129.02],
            [35.14, 129.04],
            [35.15, 129.08]
        ],
        currentRouteIndex: 0,
        trail: [],
        maxTrailLength: 40,
        color: '#81c784'
    },
    {
        id: 'ais-3',
        name: '여객선 부산스타',
        type: '여객선',
        position: [35.21, 129.12],
        targetPosition: [35.21, 129.12],
        speed: 18,
        heading: 45,
        marker: null,
        route: [
            [35.21, 129.12],
            [35.24, 129.18],
            [35.27, 129.22],
            [35.22, 129.25]
        ],
        currentRouteIndex: 0,
        trail: [],
        maxTrailLength: 25,
        color: '#ff9800'
    },
    {
        id: 'ais-4',
        name: '유조선 SEA KING',
        type: '유조선',
        position: [35.13, 129.15],
        targetPosition: [35.13, 129.15],
        speed: 10,
        heading: 180,
        marker: null,
        route: [
            [35.13, 129.15],
            [35.11, 129.13],
            [35.09, 129.11],
            [35.08, 129.08]
        ],
        currentRouteIndex: 0,
        trail: [],
        maxTrailLength: 35,
        color: '#e91e63'
    },
    {
        id: 'ais-5',
        name: '컨테이너선 BLUE WAVE',
        type: '컨테이너선',
        position: [35.25, 129.05],
        targetPosition: [35.25, 129.05],
        speed: 16,
        heading: 90,
        marker: null,
        route: [
            [35.25, 129.05],
            [35.26, 129.12],
            [35.27, 129.18],
            [35.28, 129.22]
        ],
        currentRouteIndex: 0,
        trail: [],
        maxTrailLength: 28,
        color: '#9c27b0'
    }
];

// 쓰레기 핫스팟 데이터
const hotspots = [
    {
        id: 1,
        name: "동해 핫스팟 A",
        lat: 35.2,
        lon: 129.15,
        priority: "high",
        estimatedWaste: "대량 (500kg 이상)",
        type: "플라스틱, 스티로폼",
        marker: null,
        pulseAnimation: null
    },
    {
        id: 2,
        name: "남해 핫스팟 B",
        lat: 35.15,
        lon: 129.0,
        priority: "medium",
        estimatedWaste: "중간 (200-500kg)",
        type: "어망, 부표",
        marker: null,
        pulseAnimation: null
    },
    {
        id: 3,
        name: "연안 핫스팟 C",
        lat: 35.1,
        lon: 129.1,
        priority: "low",
        estimatedWaste: "소량 (200kg 이하)",
        type: "생활쓰레기",
        marker: null,
        pulseAnimation: null
    },
    {
        id: 4,
        name: "외해 핫스팟 D",
        lat: 35.25,
        lon: 129.2,
        priority: "high",
        estimatedWaste: "대량 (500kg 이상)",
        type: "폐목재, 플라스틱",
        marker: null,
        pulseAnimation: null
    },
    {
        id: 5,
        name: "근해 핫스팟 E",
        lat: 35.12,
        lon: 129.05,
        priority: "medium",
        estimatedWaste: "중간 (200-500kg)",
        type: "폐타이어, 어구",
        marker: null,
        pulseAnimation: null
    }
];

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initClock();
    initHotspots();
    initAISList();
    initAlerts();
    initEventListeners();
    
    // 내 선박 경로 설정 (핫스팟 순회)
    myVessel.route = [
        myVessel.position,
        [35.2, 129.15],  // 핫스팟 1
        [35.25, 129.2],  // 핫스팟 4
        [35.15, 129.0],  // 핫스팟 2
        [35.12, 129.05], // 핫스팟 5
        [35.1, 129.1],   // 핫스팟 3
        myVessel.position
    ];
    
    vessels = [myVessel, ...aisVessels];
    
    // 애니메이션 시작!
    startAnimation();
    
    console.log('🚢 애니메이션 시작! 선박들이 움직입니다!');
});

// 지도 초기화
function initMap() {
    map = L.map('map').setView(myVessel.position, 11);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    // 모든 선박 마커 생성
    createVesselMarker(myVessel, true);
    aisVessels.forEach(vessel => createVesselMarker(vessel, false));
    
    // 핫스팟 마커 생성
    hotspots.forEach(hotspot => createHotspotMarker(hotspot));
}

// 선박 마커 생성
function createVesselMarker(vessel, isMyVessel) {
    const size = isMyVessel ? 24 : 18;
    const icon = L.divIcon({
        className: 'vessel-marker-animated',
        html: `
            <div class="vessel-container" style="width: ${size}px; height: ${size}px;">
                <div class="vessel-icon" style="
                    background: ${vessel.color};
                    width: ${size}px;
                    height: ${size}px;
                    border-radius: 50%;
                    border: 3px solid white;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.5);
                    position: relative;
                    transition: transform 0.3s;
                ">
                    <div class="vessel-direction" style="
                        position: absolute;
                        top: -${size/2}px;
                        left: 50%;
                        transform: translateX(-50%) rotate(${vessel.heading}deg);
                        width: 0;
                        height: 0;
                        border-left: ${size/4}px solid transparent;
                        border-right: ${size/4}px solid transparent;
                        border-bottom: ${size/2}px solid ${vessel.color};
                        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
                    "></div>
                </div>
                ${isMyVessel ? `<div class="vessel-pulse"></div>` : ''}
            </div>
        `,
        iconSize: [size + 10, size + 10],
        iconAnchor: [(size + 10) / 2, (size + 10) / 2]
    });

    vessel.marker = L.marker(vessel.position, { icon: icon })
        .addTo(map)
        .bindPopup(`
            <b>${vessel.name}</b><br>
            ${vessel.type || '수거선'}<br>
            속도: ${vessel.speed} knots<br>
            방향: ${vessel.heading}°
        `);
    
    // 경로 자취 레이어 생성
    trails[vessel.id] = L.polyline([], {
        color: vessel.color,
        weight: 3,
        opacity: 0.6,
        smoothFactor: 1,
        dashArray: '5, 5'
    }).addTo(map);
}

// 핫스팟 마커 생성
function createHotspotMarker(hotspot) {
    let color;
    switch(hotspot.priority) {
        case 'high': color = '#f44336'; break;
        case 'medium': color = '#ff9800'; break;
        case 'low': color = '#4caf50'; break;
    }

    const icon = L.divIcon({
        className: 'hotspot-marker-animated',
        html: `
            <div class="hotspot-container">
                <div class="hotspot-icon" style="
                    background: ${color};
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    border: 3px solid white;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 16px;
                ">🗑️</div>
                ${hotspot.priority === 'high' ? '<div class="hotspot-pulse"></div>' : ''}
            </div>
        `,
        iconSize: [36, 36],
        iconAnchor: [18, 18]
    });

    hotspot.marker = L.marker([hotspot.lat, hotspot.lon], { icon: icon })
        .addTo(map)
        .bindPopup(`
            <b>${hotspot.name}</b><br>
            우선순위: <span style="color: ${color}; font-weight: bold;">${hotspot.priority.toUpperCase()}</span><br>
            예상량: ${hotspot.estimatedWaste}<br>
            종류: ${hotspot.type}
        `);
}

// 애니메이션 시작
function startAnimation() {
    let lastTime = Date.now();
    
    function animate() {
        const currentTime = Date.now();
        const deltaTime = (currentTime - lastTime) / 1000; // 초 단위
        lastTime = currentTime;
        
        // 모든 선박 업데이트
        vessels.forEach(vessel => {
            updateVesselPosition(vessel, deltaTime);
            updateVesselMarker(vessel);
            updateVesselTrail(vessel);
            updateVesselInfo(vessel);
        });
        
        // 충돌 체크
        checkCollisions();
        
        animationFrame = requestAnimationFrame(animate);
    }
    
    animate();
}

// 선박 위치 업데이트
function updateVesselPosition(vessel, deltaTime) {
    // 목표 지점에 도달했으면 다음 목표로
    const distanceToTarget = calculateDistance(
        vessel.position,
        vessel.route[vessel.currentRouteIndex]
    );
    
    if (distanceToTarget < 0.1) { // 100m 이내
        vessel.currentRouteIndex = (vessel.currentRouteIndex + 1) % vessel.route.length;
    }
    
    vessel.targetPosition = vessel.route[vessel.currentRouteIndex];
    
    // 목표 방향 계산
    vessel.heading = calculateBearing(vessel.position, vessel.targetPosition);
    
    // 이동 거리 계산 (속도 기반)
    const speedKmPerHour = vessel.speed * 1.852; // knots to km/h
    const distanceKm = (speedKmPerHour / 3600) * deltaTime; // 이동 거리
    
    // 새 위치 계산
    const newPosition = moveTowards(
        vessel.position,
        vessel.targetPosition,
        distanceKm
    );
    
    // 자취에 추가
    vessel.trail.push([...vessel.position]);
    if (vessel.trail.length > vessel.maxTrailLength) {
        vessel.trail.shift();
    }
    
    vessel.position = newPosition;
}

// 선박 마커 업데이트
function updateVesselMarker(vessel) {
    if (vessel.marker) {
        vessel.marker.setLatLng(vessel.position);
        
        // 방향 표시 회전
        const markerElement = vessel.marker.getElement();
        if (markerElement) {
            const directionArrow = markerElement.querySelector('.vessel-direction');
            if (directionArrow) {
                directionArrow.style.transform = `translateX(-50%) rotate(${vessel.heading}deg)`;
            }
        }
    }
}

// 선박 경로 자취 업데이트
function updateVesselTrail(vessel) {
    if (trails[vessel.id]) {
        trails[vessel.id].setLatLngs(vessel.trail);
    }
}

// 선박 정보 업데이트 (UI)
function updateVesselInfo(vessel) {
    if (vessel.id === 'my-vessel') {
        document.getElementById('currentLat').textContent = `${vessel.position[0].toFixed(4)}° N`;
        document.getElementById('currentLon').textContent = `${vessel.position[1].toFixed(4)}° E`;
        document.getElementById('currentSpeed').textContent = `${vessel.speed.toFixed(1)} knots`;
        
        const direction = degreesToDirection(vessel.heading);
        document.getElementById('currentHeading').textContent = `${Math.round(vessel.heading)}° ${direction}`;
    }
}

// 충돌 체크
function checkCollisions() {
    const warningDistance = 2; // km
    
    for (let i = 0; i < vessels.length; i++) {
        for (let j = i + 1; j < vessels.length; j++) {
            const distance = calculateDistance(
                vessels[i].position,
                vessels[j].position
            );
            
            if (distance < warningDistance) {
                showCollisionWarning(vessels[i], vessels[j], distance);
            }
        }
    }
}

// 충돌 경고 표시
let collisionWarningTime = 0; // 이름 변경
function showCollisionWarning(vessel1, vessel2, distance) {
    const now = Date.now();
    if (now - collisionWarningTime < 5000) return; // 5초에 한 번만
    
    collisionWarningTime = now;
    
    // 마커 깜빡임 효과
    if (vessel1.marker) {
        const el1 = vessel1.marker.getElement();
        if (el1) el1.classList.add('collision-warning');
        setTimeout(() => el1.classList.remove('collision-warning'), 2000);
    }
    
    if (vessel2.marker) {
        const el2 = vessel2.marker.getElement();
        if (el2) el2.classList.add('collision-warning');
        setTimeout(() => el2.classList.remove('collision-warning'), 2000);
    }
    
    console.warn(`⚠️ 충돌 주의! ${vessel1.name}와 ${vessel2.name} 거리: ${distance.toFixed(2)}km`);
    
    // UI에 알림 추가 - 즉시 실행
    setTimeout(() => {
        const alertList = document.getElementById('alertList');
        if (!alertList) {
            console.error('❌ alertList를 찾을 수 없습니다!');
            return;
        }
        
        const item = document.createElement('div');
        item.className = 'alert-item warning alert-slide-in';
        item.style.animation = 'alert-slide 0.3s ease-out';
        item.innerHTML = `
            <div class="alert-icon">⚠️</div>
            <div class="alert-content">
                <div class="alert-title">실시간 충돌 감지!</div>
                <div class="alert-message">${vessel1.name}와 ${vessel2.name}<br>거리: ${distance.toFixed(2)}km</div>
                <div class="alert-time">방금 전</div>
            </div>
        `;
        
        // 맨 위에 추가
        alertList.insertBefore(item, alertList.firstChild);
        console.log('✅ 충돌 알림 UI에 추가됨!');
        
        // 스크롤 맨 위로
        alertList.scrollTop = 0;
        
        // 최대 5개만 유지
        while (alertList.children.length > 5) {
            alertList.removeChild(alertList.lastChild);
        }
    }, 100); // 100ms 지연
}

// 충돌 알림 UI 추가 함수
function addCollisionAlert(vessel1Name, vessel2Name, distance) {
    const alertList = document.getElementById('alertList');
    if (!alertList) return;
    
    const item = document.createElement('div');
    item.className = 'alert-item warning alert-slide-in';
    item.innerHTML = `
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
            <div class="alert-title">충돌 주의!</div>
            <div class="alert-message">${vessel1Name}와 ${vessel2Name}<br>거리: ${distance.toFixed(2)}km</div>
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

// 충돌 알림 UI 추가 함수
function addCollisionAlert(vessel1Name, vessel2Name, distance) {
    const alertList = document.getElementById('alertList');
    if (!alertList) return;
    
    const item = document.createElement('div');
    item.className = 'alert-item warning alert-slide-in';
    item.innerHTML = `
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
            <div class="alert-title">충돌 주의!</div>
            <div class="alert-message">${vessel1Name}와 ${vessel2Name}<br>거리: ${distance.toFixed(2)}km</div>
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

// 유틸리티 함수들
function calculateDistance(pos1, pos2) {
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

function calculateBearing(from, to) {
    const lat1 = from[0] * Math.PI / 180;
    const lat2 = to[0] * Math.PI / 180;
    const deltaLon = (to[1] - from[1]) * Math.PI / 180;

    const y = Math.sin(deltaLon) * Math.cos(lat2);
    const x = Math.cos(lat1) * Math.sin(lat2) -
              Math.sin(lat1) * Math.cos(lat2) * Math.cos(deltaLon);
    
    let bearing = Math.atan2(y, x) * 180 / Math.PI;
    bearing = (bearing + 360) % 360;
    return bearing;
}

function moveTowards(from, to, distanceKm) {
    const R = 6371;
    const bearing = calculateBearing(from, to) * Math.PI / 180;
    const lat1 = from[0] * Math.PI / 180;
    const lon1 = from[1] * Math.PI / 180;
    const d = distanceKm / R;

    const lat2 = Math.asin(
        Math.sin(lat1) * Math.cos(d) +
        Math.cos(lat1) * Math.sin(d) * Math.cos(bearing)
    );

    const lon2 = lon1 + Math.atan2(
        Math.sin(bearing) * Math.sin(d) * Math.cos(lat1),
        Math.cos(d) - Math.sin(lat1) * Math.sin(lat2)
    );

    return [lat2 * 180 / Math.PI, lon2 * 180 / Math.PI];
}

function degreesToDirection(degrees) {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(degrees / 45) % 8;
    return directions[index];
}

// 시계 업데이트
function initClock() {
    updateClock();
    setInterval(updateClock, 1000);
}

function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('currentTime').textContent = timeString;
}

// 핫스팟 목록 초기화
function initHotspots() {
    const hotspotList = document.getElementById('hotspotList');
    hotspotList.innerHTML = '';

    hotspots.forEach(hotspot => {
        const distance = calculateDistance(myVessel.position, [hotspot.lat, hotspot.lon]);
        const item = document.createElement('div');
        item.className = 'hotspot-item';
        item.innerHTML = `
            <div class="hotspot-header">
                <span class="hotspot-name">${hotspot.name}</span>
                <span class="hotspot-priority priority-${hotspot.priority}">${hotspot.priority.toUpperCase()}</span>
            </div>
            <div class="hotspot-details">
                <div>📍 거리: ${distance.toFixed(1)} km</div>
                <div>⚖️ ${hotspot.estimatedWaste}</div>
                <div>🗑️ ${hotspot.type}</div>
            </div>
        `;
        
        item.addEventListener('click', () => {
            map.setView([hotspot.lat, hotspot.lon], 13);
            hotspot.marker.openPopup();
        });

        hotspotList.appendChild(item);
    });
}

// AIS 목록 초기화
function initAISList() {
    const aisList = document.getElementById('aisList');
    aisList.innerHTML = '';

    aisVessels.forEach((vessel, index) => {
        const distance = calculateDistance(myVessel.position, vessel.position);
        const item = document.createElement('div');
        item.className = 'ais-item';
        item.innerHTML = `
            <div class="ais-header">
                <span class="ais-name">${vessel.name}</span>
                <span class="ais-distance">${distance.toFixed(1)} km</span>
            </div>
            <div class="ais-details">
                ${vessel.type} | ${vessel.speed} knots | ${Math.round(vessel.heading)}°
            </div>
        `;

        item.addEventListener('click', () => {
            map.setView(vessel.position, 13);
            vessel.marker.openPopup();
        });

        aisList.appendChild(item);
    });
}

// 알림 목록 초기화
function initAlerts() {
    const alerts = [
        {
            type: "warning",
            icon: "⚠️",
            title: "선박 근접 경고",
            message: "2km 이내 선박 5척 감지",
            time: "방금 전"
        },
        {
            type: "info",
            icon: "ℹ️",
            title: "새로운 핫스팟 감지",
            message: "35.25°N, 129.20°E 지역",
            time: "5분 전"
        },
        {
            type: "info",
            icon: "✅",
            title: "경로 업데이트",
            message: "최적 경로로 자동 조정됨",
            time: "10분 전"
        }
    ];

    const alertList = document.getElementById('alertList');
    alertList.innerHTML = ''; // 초기화만 하고

    alerts.forEach(alert => {
        const item = document.createElement('div');
        item.className = `alert-item ${alert.type}`;
        item.innerHTML = `
            <div class="alert-icon">${alert.icon}</div>
            <div class="alert-content">
                <div class="alert-title">${alert.title}</div>
                <div class="alert-message">${alert.message}</div>
                <div class="alert-time">${alert.time}</div>
            </div>
        `;
        alertList.appendChild(item);
    });
}

// 이벤트 리스너 초기화
function initEventListeners() {
    document.getElementById('centerBtn').addEventListener('click', () => {
        map.setView(myVessel.position, 11);
    });

    document.getElementById('layerBtn').addEventListener('click', () => {
        const layerPanel = document.getElementById('layerPanel');
        layerPanel.classList.toggle('active');
    });

    document.getElementById('routeBtn').addEventListener('click', showRouteInfo);
    document.getElementById('optimizeRoute').addEventListener('click', showRouteInfo);

    document.getElementById('aisLayer').addEventListener('change', (e) => {
        aisVessels.forEach(vessel => {
            if (e.target.checked) {
                vessel.marker.addTo(map);
                trails[vessel.id].addTo(map);
            } else {
                map.removeLayer(vessel.marker);
                map.removeLayer(trails[vessel.id]);
            }
        });
    });

    document.getElementById('hotspotLayer').addEventListener('change', (e) => {
        hotspots.forEach(hotspot => {
            if (e.target.checked) {
                hotspot.marker.addTo(map);
            } else {
                map.removeLayer(hotspot.marker);
            }
        });
    });
}

function showRouteInfo() {
    const totalDistance = myVessel.route.reduce((sum, point, i) => {
        if (i === 0) return 0;
        return sum + calculateDistance(myVessel.route[i-1], point);
    }, 0);
    
    const eta = totalDistance / (myVessel.speed * 1.852);
    const hours = Math.floor(eta);
    const minutes = Math.round((eta - hours) * 60);
    
    alert(`🛣️ 경로 정보\n\n총 거리: ${totalDistance.toFixed(1)} km\n예상 시간: ${hours}시간 ${minutes}분\n핫스팟: ${hotspots.length}개 지점\n현재 속도: ${myVessel.speed} knots`);
}

// 🔥 충돌 알림 강제 패치 - 파일 끝에 추가
console.log('🔥 충돌 알림 시스템 패치 시작...');

setTimeout(() => {
    console.log('✅ 3초 후 충돌 감지 시스템 활성화...');
    
    // checkCollisions 함수를 완전히 교체
    let collisionAlertTime = 0; // 다른 이름 사용
    
    checkCollisions = function() {
        const warningDistance = 2;
        
        for (let i = 0; i < vessels.length; i++) {
            for (let j = i + 1; j < vessels.length; j++) {
                const distance = calculateDistance(vessels[i].position, vessels[j].position);
                
                if (distance < warningDistance) {
                    const now = Date.now();
                    if (now - collisionAlertTime > 5000) {
                        collisionAlertTime = now;
                        
                        console.log(`⚠️ 충돌 감지! ${vessels[i].name} vs ${vessels[j].name}, 거리: ${distance.toFixed(2)}km`);
                        
                        // UI에 알림 추가
                        try {
                            const alertList = document.getElementById('alertList');
                            if (alertList) {
                                const item = document.createElement('div');
                                item.style.cssText = 'background: rgba(255, 152, 0, 0.2); border-left: 4px solid #ff9800; padding: 12px; margin-bottom: 10px; border-radius: 8px; display: flex; gap: 10px; animation: alert-slide 0.3s ease-out;';
                                item.innerHTML = `
                                    <div style="font-size: 20px;">⚠️</div>
                                    <div style="flex: 1;">
                                        <div style="font-weight: bold; color: #fff; margin-bottom: 4px;">🔴 실시간 충돌 경고!</div>
                                        <div style="font-size: 13px; color: #b0bec5;">${vessels[i].name}와 ${vessels[j].name}<br>거리: ${distance.toFixed(2)}km</div>
                                        <div style="font-size: 11px; color: #78909c; margin-top: 4px;">방금 전</div>
                                    </div>
                                `;
                                alertList.insertBefore(item, alertList.firstChild);
                                alertList.scrollTop = 0;
                                
                                console.log('✅ UI에 알림 추가 성공!');
                                
                                while (alertList.children.length > 5) {
                                    alertList.removeChild(alertList.lastChild);
                                }
                            }
                        } catch (error) {
                            console.error('❌ 알림 추가 실패:', error);
                        }
                    }
                }
            }
        }
    };
    
    console.log('✅ 충돌 감지 시스템 활성화 완료!');
}, 3000);