// 🚨 충돌 알림 강제 수정 버전
// 이 파일이 가장 마지막에 로드되어 모든 것을 덮어씁니다

console.log('🔥 충돌 알림 강제 패치 시작...');

// 원본 showCollisionWarning 함수를 완전히 교체
window.originalShowCollisionWarning = window.showCollisionWarning;

let lastWarningTime = 0;

window.showCollisionWarning = function(vessel1, vessel2, distance) {
    const now = Date.now();
    if (now - lastWarningTime < 5000) {
        console.log('⏭️ 5초 이내 중복 경고 스킵');
        return;
    }
    
    lastWarningTime = now;
    
    console.log('🚨 showCollisionWarning 호출됨!');
    console.log(`   선박1: ${vessel1.name}`);
    console.log(`   선박2: ${vessel2.name}`);
    console.log(`   거리: ${distance.toFixed(2)}km`);
    
    // 마커 깜빡임
    if (vessel1.marker) {
        const el1 = vessel1.marker.getElement();
        if (el1) {
            el1.classList.add('collision-warning');
            setTimeout(() => el1.classList.remove('collision-warning'), 2000);
        }
    }
    
    if (vessel2.marker) {
        const el2 = vessel2.marker.getElement();
        if (el2) {
            el2.classList.add('collision-warning');
            setTimeout(() => el2.classList.remove('collision-warning'), 2000);
        }
    }
    
    // UI에 알림 추가
    const alertList = document.getElementById('alertList');
    
    if (!alertList) {
        console.error('❌ alertList 요소를 찾을 수 없습니다!');
        return;
    }
    
    console.log('✅ alertList 찾음, 알림 추가 중...');
    
    const item = document.createElement('div');
    item.className = 'alert-item warning';
    item.style.cssText = 'animation: alert-slide 0.3s ease-out; background: rgba(255, 152, 0, 0.2); border-left: 4px solid #ff9800; padding: 12px; margin-bottom: 10px; border-radius: 8px; display: flex; gap: 10px;';
    
    item.innerHTML = `
        <div style="font-size: 20px;">⚠️</div>
        <div style="flex: 1;">
            <div style="font-weight: bold; color: #fff; margin-bottom: 4px;">🔴 실시간 충돌 경고!</div>
            <div style="font-size: 13px; color: #b0bec5;">${vessel1.name}와 ${vessel2.name}<br>거리: ${distance.toFixed(2)}km</div>
            <div style="font-size: 11px; color: #78909c; margin-top: 4px;">방금 전</div>
        </div>
    `;
    
    // 맨 위에 추가
    if (alertList.firstChild) {
        alertList.insertBefore(item, alertList.firstChild);
    } else {
        alertList.appendChild(item);
    }
    
    // 스크롤 맨 위로
    alertList.scrollTop = 0;
    
    console.log('✅ 알림 추가 완료! 현재 알림 개수:', alertList.children.length);
    
    // 최대 5개만 유지
    while (alertList.children.length > 5) {
        alertList.removeChild(alertList.lastChild);
    }
    
    // 콘솔 경고도 출력
    console.warn(`⚠️ 충돌 주의! ${vessel1.name}와 ${vessel2.name} 거리: ${distance.toFixed(2)}km`);
};

console.log('✅ showCollisionWarning 함수 교체 완료!');

// 즉시 테스트
setTimeout(() => {
    console.log('🧪 3초 후 테스트 알림 발생...');
    
    // 가짜 선박 객체로 테스트
    const fakeVessel1 = { name: '테스트선박-A', marker: null };
    const fakeVessel2 = { name: '테스트선박-B', marker: null };
    
    showCollisionWarning(fakeVessel1, fakeVessel2, 0.8);
}, 3000);

console.log('🔥 충돌 알림 시스템 패치 완료!');
