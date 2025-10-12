// 전역 변수
let map;
let currentPosition = [35.1796, 129.0756]; // 부산 앞바다
let markers = {
    vessel: null,
    hotspots: [],
    aisVessels: []
};

// 모의 데이터 (실제 API 연동 시 교체)
const mockData = {
    hotspots: [
        {
            id: 1,
            name: "동해 핫스팟 A",
            lat: 35.2,
            lon: 129.15,
            priority: "high",
            estimatedWaste: "대량 (500kg 이상)",
            type: "플라스틱, 스티로폼",
            distance: "5.2 km"
        },
        {
            id: 2,
            name: "남해 핫스팟 B",
            lat: 35.15,
            lon: 129.0,
            priority: "medium",
            estimatedWaste: "중간 (200-500kg)",
            type: "어망, 부표",
            distance: "8.7 km"
        },
        {
            id: 3,
            name: "연안 핫스팟 C",
            lat: 35.1,
            lon: 129.1,
            priority: "low",
            estimatedWaste: "소량 (200kg 이하)",
            type: "생활쓰레기",
            distance: "12.3 km"
        },
        {
            id: 4,
            name: "외해 핫스팟 D",
            lat: 35.25,
            lon: 129.2,
            priority: "high",
            estimatedWaste: "대량 (500kg 이상)",
            type: "폐목재, 플라스틱",
            distance: "15.8 km"
        },
        {
            id: 5,
            name: "근해 핫스팟 E",
            lat: 35.12,
            lon: 129.05,
            priority: "medium",
            estimatedWaste: "중간 (200-500kg)",
            type: "폐타이어, 어구",
            distance: "3.4 km"
        }
    ],
    aisVessels: [
        {
            id: 1,
            name: "화물선 OCEAN-1",
            type: "화물선",
            lat: 35.19,
            lon: 129.08,
            speed: "14.2 knots",
            heading: "125°",
            distance: "2.3 km"
        },
        {
            id: 2,
            name: "어선 해풍호",
            type: "어선",
            lat: 35.17,
            lon: 129.1,
            speed: "8.5 knots",
            heading: "270°",
            distance: "3.1 km"
        },
        {
            id: 3,
            name: "여객선 부산스타",
            type: "여객선",
            lat: 35.21,
            lon: 129.12,
            speed: "18.0 knots",
            heading: "45°",
            distance: "5.7 km"
        }
    ],
    alerts: [
        {
            type: "warning",
            icon: "⚠️",
            title: "기상 주의보",
            message: "2시간 후 풍속 15m/s 이상 예상",
            time: "10분 전"
        },
        {
            type: "info",
            icon: "ℹ️",
            title: "새로운 핫스팟 감지",
            message: "35.25°N, 129.20°E 지역",
            time: "25분 전"
        },
        {
            type: "danger",
            icon: "🚨",
            title: "항해 주의",
            message: "전방 2km 어선 조업 중",
            time: "1시간 전"
        }
    ]
};

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initClock();
    initHotspots();
    initAISList();
    initAlerts();
    initEventListeners();
    startSimulation();
});

// 지도 초기화
function initMap() {
    map = L.map('map').setView(currentPosition, 11);

    // 기본 레이어 - OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    // 현재 선박 마커
    const vesselIcon = L.divIcon({
        className: 'vessel-marker',
        html: '<div style="background: #2196f3; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3);"></div>',
        iconSize: [26, 26],
        iconAnchor: [13, 13]
    });

    markers.vessel = L.marker(currentPosition, { icon: vesselIcon })
        .addTo(map)
        .bindPopup('<b>클린오션-1호</b><br>현재 위치');

    // 핫스팟 마커 추가
    addHotspotMarkers();

    // AIS 선박 마커 추가
    addAISMarkers();
}

// 핫스팟 마커 추가
function addHotspotMarkers() {
    mockData.hotspots.forEach(hotspot => {
        let color;
        switch(hotspot.priority) {
            case 'high': color = '#f44336'; break;
            case 'medium': color = '#ff9800'; break;
            case 'low': color = '#4caf50'; break;
        }

        const hotspotIcon = L.divIcon({
            className: 'hotspot-marker',
            html: `<div style="background: ${color}; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 16px;">🗑️</div>`,
            iconSize: [36, 36],
            iconAnchor: [18, 18]
        });

        const marker = L.marker([hotspot.lat, hotspot.lon], { icon: hotspotIcon })
            .addTo(map)
            .bindPopup(`
                <b>${hotspot.name}</b><br>
                우선순위: ${hotspot.priority}<br>
                예상량: ${hotspot.estimatedWaste}<br>
                종류: ${hotspot.type}
            `);

        markers.hotspots.push(marker);
    });
}

// AIS 선박 마커 추가
function addAISMarkers() {
    mockData.aisVessels.forEach(vessel => {
        const aisIcon = L.divIcon({
            className: 'ais-marker',
            html: '<div style="background: #64b5f6; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);"></div>',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        const marker = L.marker([vessel.lat, vessel.lon], { icon: aisIcon })
            .addTo(map)
            .bindPopup(`
                <b>${vessel.name}</b><br>
                종류: ${vessel.type}<br>
                속도: ${vessel.speed}<br>
                방향: ${vessel.heading}
            `);

        markers.aisVessels.push(marker);
    });
}

// 시계 초기화
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

    mockData.hotspots.forEach(hotspot => {
        const item = document.createElement('div');
        item.className = 'hotspot-item';
        item.innerHTML = `
            <div class="hotspot-header">
                <span class="hotspot-name">${hotspot.name}</span>
                <span class="hotspot-priority priority-${hotspot.priority}">${hotspot.priority.toUpperCase()}</span>
            </div>
            <div class="hotspot-details">
                <div>📍 거리: ${hotspot.distance}</div>
                <div>⚖️ ${hotspot.estimatedWaste}</div>
                <div>🗑️ ${hotspot.type}</div>
            </div>
        `;
        
        item.addEventListener('click', () => {
            map.setView([hotspot.lat, hotspot.lon], 13);
            markers.hotspots[mockData.hotspots.indexOf(hotspot)].openPopup();
        });

        hotspotList.appendChild(item);
    });
}

// AIS 목록 초기화
function initAISList() {
    const aisList = document.getElementById('aisList');
    aisList.innerHTML = '';

    mockData.aisVessels.forEach(vessel => {
        const item = document.createElement('div');
        item.className = 'ais-item';
        item.innerHTML = `
            <div class="ais-header">
                <span class="ais-name">${vessel.name}</span>
                <span class="ais-distance">${vessel.distance}</span>
            </div>
            <div class="ais-details">
                ${vessel.type} | ${vessel.speed} | ${vessel.heading}
            </div>
        `;

        item.addEventListener('click', () => {
            map.setView([vessel.lat, vessel.lon], 13);
            markers.aisVessels[mockData.aisVessels.indexOf(vessel)].openPopup();
        });

        aisList.appendChild(item);
    });
}

// 알림 목록 초기화
function initAlerts() {
    const alertList = document.getElementById('alertList');
    alertList.innerHTML = '';

    mockData.alerts.forEach(alert => {
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
    // 현재 위치로 버튼
    document.getElementById('centerBtn').addEventListener('click', () => {
        map.setView(currentPosition, 11);
    });

    // 레이어 토글 버튼
    document.getElementById('layerBtn').addEventListener('click', () => {
        const layerPanel = document.getElementById('layerPanel');
        layerPanel.classList.toggle('active');
    });

    // 경로 최적화 버튼
    document.getElementById('routeBtn').addEventListener('click', optimizeRoute);
    document.getElementById('optimizeRoute').addEventListener('click', optimizeRoute);

    // 레이어 체크박스
    document.getElementById('aisLayer').addEventListener('change', toggleAISLayer);
    document.getElementById('hotspotLayer').addEventListener('change', toggleHotspotLayer);
}

// 레이어 토글
function toggleAISLayer(e) {
    markers.aisVessels.forEach(marker => {
        if (e.target.checked) {
            marker.addTo(map);
        } else {
            map.removeLayer(marker);
        }
    });
}

function toggleHotspotLayer(e) {
    markers.hotspots.forEach(marker => {
        if (e.target.checked) {
            marker.addTo(map);
        } else {
            map.removeLayer(marker);
        }
    });
}

// 경로 최적화
function optimizeRoute() {
    alert('경로 최적화 기능\n\n실제 구현 시:\n- TSP(외판원 문제) 알고리즘 적용\n- 기상 조건 고려\n- 연료 효율 계산\n- 실시간 해류/풍향 반영');
    
    // 모의 경로 그리기
    const routePoints = [
        currentPosition,
        [35.2, 129.15],
        [35.25, 129.2],
        [35.15, 129.0],
        [35.12, 129.05],
        [35.1, 129.1]
    ];

    // 기존 경로 제거
    map.eachLayer(layer => {
        if (layer instanceof L.Polyline) {
            map.removeLayer(layer);
        }
    });

    // 새 경로 그리기
    L.polyline(routePoints, {
        color: '#2196f3',
        weight: 4,
        opacity: 0.7,
        dashArray: '10, 10'
    }).addTo(map);
}

// 시뮬레이션 시작 (선박 이동 등)
function startSimulation() {
    setInterval(() => {
        // 선박 위치 약간 변경 (시뮬레이션)
        currentPosition[0] += (Math.random() - 0.5) * 0.001;
        currentPosition[1] += (Math.random() - 0.5) * 0.001;
        
        markers.vessel.setLatLng(currentPosition);
        
        // 위치 정보 업데이트
        document.getElementById('currentLat').textContent = `${currentPosition[0].toFixed(4)}° N`;
        document.getElementById('currentLon').textContent = `${currentPosition[1].toFixed(4)}° E`;
        
        // 속도 랜덤 변경
        const speed = (10 + Math.random() * 5).toFixed(1);
        document.getElementById('currentSpeed').textContent = `${speed} knots`;
        
        // 방향 랜덤 변경
        const heading = Math.floor(Math.random() * 360);
        const direction = getDirection(heading);
        document.getElementById('currentHeading').textContent = `${heading}° ${direction}`;
        
    }, 3000);
}

// 방향 변환
function getDirection(degrees) {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(degrees / 45) % 8;
    return directions[index];
}

// API 연동을 위한 함수들 (실제 데이터 연동 시 사용)
const API = {
    // AIS 데이터 가져오기
    fetchAISData: async () => {
        // TODO: 실제 AIS API 엔드포인트 연결
        // const response = await fetch('https://api.example.com/ais');
        // return await response.json();
        return mockData.aisVessels;
    },

    // 쓰레기 핫스팟 데이터 가져오기
    fetchHotspots: async () => {
        // TODO: 실제 쓰레기 예측 API 연결
        // const response = await fetch('https://api.example.com/hotspots');
        // return await response.json();
        return mockData.hotspots;
    },

    // 기상 데이터 가져오기
    fetchWeatherData: async () => {
        // TODO: 실제 기상 API 연결 (기상청 API 등)
        // const response = await fetch('https://api.weather.com/...');
        // return await response.json();
        return {
            temperature: 23,
            windDirection: '북동 15°',
            windSpeed: '8.5 m/s',
            waveHeight: '1.2 m',
            visibility: '15 km'
        };
    },

    // 해류 데이터 가져오기
    fetchOceanCurrents: async () => {
        // TODO: 해류 데이터 API 연결
        return null;
    },

    // 경로 최적화 요청
    optimizeRoute: async (waypoints, constraints) => {
        // TODO: 경로 최적화 알고리즘 서버 API 연결
        // const response = await fetch('https://api.example.com/optimize', {
        //     method: 'POST',
        //     body: JSON.stringify({ waypoints, constraints })
        // });
        // return await response.json();
        return null;
    }
};

// 데이터 업데이트 (주기적 호출)
async function updateAllData() {
    try {
        // 실제 구현 시 각 API 호출
        const aisData = await API.fetchAISData();
        const hotspots = await API.fetchHotspots();
        const weather = await API.fetchWeatherData();
        
        // UI 업데이트
        // updateAISMarkers(aisData);
        // updateHotspotMarkers(hotspots);
        // updateWeatherDisplay(weather);
    } catch (error) {
        console.error('데이터 업데이트 실패:', error);
    }
}

// 5분마다 데이터 업데이트
setInterval(updateAllData, 300000);