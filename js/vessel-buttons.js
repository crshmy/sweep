// 우측 버튼에 어선 관련 버튼 추가 및 이벤트 연결

// 페이지 로드 후 실행
window.addEventListener('load', () => {
    setTimeout(() => {
        // 버튼 추가
        const controls = document.querySelector('.map-controls');
        if (controls) {
            // 어선 위험도 버튼
            const fishingBtn = document.createElement('button');
            fishingBtn.className = 'control-btn';
            fishingBtn.id = 'fishingRiskBtn';
            fishingBtn.title = '어선 위험도';
            fishingBtn.style.background = '#fff3e0';
            fishingBtn.innerHTML = '🎣';
            controls.appendChild(fishingBtn);
            
            // 어선 추적 버튼
            const vesselBtn = document.createElement('button');
            vesselBtn.className = 'control-btn';
            vesselBtn.id = 'vesselAnimationBtn';
            vesselBtn.title = '어선 추적';
            vesselBtn.style.background = '#e3f2fd';
            vesselBtn.innerHTML = '🚢';
            controls.appendChild(vesselBtn);
            
            // 어선 위험도 토글
            fishingBtn.addEventListener('click', () => {
                const panel = document.querySelector('.fishing-risk-controls');
                if (panel) {
                    const isHidden = panel.style.display === 'none';
                    panel.style.display = isHidden ? 'block' : 'none';
                    fishingBtn.style.opacity = isHidden ? '1' : '0.5';
                }
            });
            
            // 어선 추적 토글
            vesselBtn.addEventListener('click', () => {
                const panel = document.querySelector('.vessel-animation-controls');
                if (panel) {
                    const isHidden = panel.style.display === 'none';
                    panel.style.display = isHidden ? 'block' : 'none';
                    vesselBtn.style.opacity = isHidden ? '1' : '0.5';
                }
            });
            
            console.log('✅ 어선 관련 버튼 추가 완료');
        }
    }, 2000);
});
