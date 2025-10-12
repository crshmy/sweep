// 어선 회피 구역 추가 스크립트 (수정 버전)

// 어선 조업 구역 데이터
const fishingZonesData = [
    {
        center: [35.16, 129.05],
        radius: 2500, // 미터
        name: "어선 해풍호 조업 구역",
        active: true,
        color: '#f44336'
    },
    {
        center: [35.22, 129.08],
        radius: 3000,
        name: "단체 조업 구역",
        active: true,
        color: '#f44336'
    },
    {
        center: [35.11, 129.05],
        radius: 2000,
        name: "오후 예정 구역",
        active: false,
        color: '#ffa726'
    }
];

// 지도가 로드된 후 어선 구역 추가
window.addEventListener('load', () => {
    setTimeout(() => {
        if (typeof map !== 'undefined' && map) {
            fishingZonesData.forEach(zone => {
                const circle = L.circle(zone.center, {
                    radius: zone.radius,
                    color: zone.color,
                    fillColor: zone.color,
                    fillOpacity: zone.active ? 0.25 : 0.15,
                    weight: 2,
                    dashArray: zone.active ? null : '10, 10'
                }).addTo(map);
                
                circle.bindPopup(`
                    <b>${zone.name}</b><br>
                    상태: ${zone.active ? '🔴 조업중' : '🟡 예정'}<br>
                    반경: ${(zone.radius/1000).toFixed(1)} km
                `);
            });
            
            console.log('🎣 어선 조업 구역 3개 표시 완료!');
        }
    }, 1000); // 1초 대기 후 추가
});
