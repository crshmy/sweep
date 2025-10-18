// 🔥 충돌 알림 디버깅 버전
// 모든 단계마다 로그 출력

console.log('🔧 [DEBUG] 알림 시스템 로드 시작...');

// 1단계: DOM 확인
function checkDOM() {
    const alertList = document.getElementById('alertList');
    console.log('📋 [DEBUG] alertList 요소:', alertList);
    
    if (!alertList) {
        console.error('❌ [DEBUG] alertList를 찾을 수 없습니다!');
        return false;
    }
    
    console.log('✅ [DEBUG] alertList 발견! 현재 자식 개수:', alertList.children.length);
    return true;
}

// 2단계: 알림 추가 함수 (디버깅 버전)
window.addCollisionAlertDebug = function(vessel1Name, vessel2Name, distance) {
    console.log('🚀 [DEBUG] addCollisionAlertDebug 호출됨!');
    console.log('   - vessel1Name:', vessel1Name);
    console.log('   - vessel2Name:', vessel2Name);
    console.log('   - distance:', distance);
    
    const alertList = document.getElementById('alertList');
    
    if (!alertList) {
        console.error('❌ [DEBUG] alertList를 찾을 수 없습니다!');
        return;
    }
    
    console.log('✅ [DEBUG] alertList 확인 완료');
    
    const item = document.createElement('div');
    console.log('✅ [DEBUG] div 생성 완료');
    
    item.className = 'alert-item warning alert-slide-in';
    console.log('✅ [DEBUG] className 설정 완료');
    
    item.innerHTML = `
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
            <div class="alert-title">🔥 실시간 충돌 감지!</div>
            <div class="alert-message">${vessel1Name}와 ${vessel2Name}<br>거리: ${distance.toFixed(2)}km</div>
            <div class="alert-time">방금 전 (테스트)</div>
        </div>
    `;
    console.log('✅ [DEBUG] innerHTML 설정 완료');
    
    try {
        alertList.insertBefore(item, alertList.firstChild);
        console.log('✅ [DEBUG] DOM에 추가 완료!');
        console.log('📊 [DEBUG] 현재 알림 개수:', alertList.children.length);
    } catch (error) {
        console.error('❌ [DEBUG] DOM 추가 실패:', error);
    }
    
    // 최대 10개만 유지 (테스트용으로 더 많이)
    while (alertList.children.length > 10) {
        alertList.removeChild(alertList.lastChild);
        console.log('🗑️ [DEBUG] 오래된 알림 제거');
    }
    
    console.log('🎉 [DEBUG] 함수 실행 완료!');
};

// 3단계: 원본 함수 덮어쓰기
window.addCollisionAlert = window.addCollisionAlertDebug;

// 4단계: 자동 테스트
setTimeout(() => {
    console.log('⏰ [DEBUG] 3초 후 자동 테스트 시작...');
    
    if (checkDOM()) {
        console.log('🧪 [DEBUG] 테스트 알림 추가 시도...');
        addCollisionAlertDebug('테스트 선박 A', '테스트 선박 B', 1.5);
    }
}, 3000);

// 5단계: 수동 테스트 함수
window.testAlert = function() {
    console.log('🔧 [DEBUG] 수동 테스트 시작!');
    addCollisionAlertDebug('sweep-1호', '화물선 OCEAN-1', 1.23);
};

console.log('✅ [DEBUG] 디버깅 스크립트 로드 완료!');
console.log('💡 [사용법] 콘솔에서 testAlert() 실행하세요!');
