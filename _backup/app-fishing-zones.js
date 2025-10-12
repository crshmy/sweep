// 어선 회피 구역 시각화 추가 버전 (계속)

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

function initAISList() {
    const aisList = document.getElementById('aisList');
    aisList.innerHTML = '';

    aisVessels.forEach((vessel, index) => {
        const distance = calculateDistance(myVessel.position, vessel.position);
        const item = document.createElement('div');
        item.className = 'ais-item';
        item.innerHTML = `
            <div class="ais-header">
                <span class="ais-name">${vessel.name} ${vessel.isFishingVessel ? '🎣' : ''}</span>
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

function initAlerts() {
    const alerts = [
        {
            type: "warning",
            icon: "⚠️",
            title: "어선 조업 구역 근접",
            message: "1.5km 전방 조업 중",
            time: "방금 전"
        },
        {
            type: "info",
            icon: "🎣",
            title: "조업 구역 예측",
            message: "오후 2시 예상 조업 구역 표시됨",
            time: "5분 전"
        },
        {
            type: "info",
            icon: "✅",
            title: "경로 우회 완료",
            message: "어선 구역 회피 경로 적용",
            time: "10분 전"
        }
    ];

    const alertList = document.getElementById('alertList');
    alertList.innerHTML = '';

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

    // 어선 구역 레이어 토글
    const fishingZoneToggle = document.getElementById('fishingZoneLayer');
    if (fishingZoneToggle) {
        fishingZoneToggle.addEventListener('change', (e) => {
            fishingZoneCircles.forEach(({ circle, marker }) => {
                if (e.target.checked) {
                    circle.addTo(map);
                    marker.addTo(map);
                } else {
                    map.removeLayer(circle);
                    map.removeLayer(marker);
                }
            });
        });
    }
}

function showRouteInfo() {
    const totalDistance = myVessel.route.reduce((sum, point, i) => {
        if (i === 0) return 0;
        return sum + calculateDistance(myVessel.route[i-1], point);
    }, 0);
    
    const eta = totalDistance / (myVessel.speed * 1.852);
    const hours = Math.floor(eta);
    const minutes = Math.round((eta - hours) * 60);
    
    alert(`🛣️ 경로 정보\n\n총 거리: ${totalDistance.toFixed(1)} km\n예상 시간: ${hours}시간 ${minutes}분\n핫스팟: ${hotspots.length}개 지점\n현재 속도: ${myVessel.speed} knots\n\n🎣 어선 조업 구역:\n활성: ${fishingZoneData.filter(z => z.type === 'active').length}개\n예정: ${fishingZoneData.filter(z => z.type === 'predicted').length}개`);
}