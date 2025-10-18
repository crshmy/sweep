// 🚨 간단한 알림 테스트 함수
// 콘솔에서 바로 사용 가능

// 충돌 알림 테스트
window.testCollision = function() {
    addCollisionAlert('sweep-1호', '화물선 OCEAN-1', 1.22);
    console.log('✅ 충돌 알림 테스트 완료!');
};

// 기상 경고 테스트
window.testWeatherAlert = function() {
    if (typeof addAlert === 'function') {
        addAlert('warning', '⚠️ 강풍 주의', '현재 풍속 15.5 m/s');
    } else {
        // addAlert 함수가 없으면 직접 추가
        const alertList = document.getElementById('alertList');
        if (!alertList) return;
        
        const item = document.createElement('div');
        item.className = 'alert-item warning alert-slide-in';
        item.innerHTML = `
            <div class="alert-icon">⚠️</div>
            <div class="alert-content">
                <div class="alert-title">강풍 주의</div>
                <div class="alert-message">현재 풍속 15.5 m/s</div>
                <div class="alert-time">방금 전</div>
            </div>
        `;
        alertList.insertBefore(item, alertList.firstChild);
    }
    console.log('✅ 기상 경고 테스트 완료!');
};

// 알림 초기화 (하드코딩 제거)
window.clearAlerts = function() {
    const alertList = document.getElementById('alertList');
    if (alertList) {
        alertList.innerHTML = '';
        console.log('✅ 알림 목록 초기화 완료!');
    }
};

console.log('🔧 테스트 함수 로드 완료!');
console.log('사용법:');
console.log('  testCollision()    - 충돌 알림 테스트');
console.log('  testWeatherAlert() - 기상 경고 테스트');
console.log('  clearAlerts()      - 알림 전체 삭제');
