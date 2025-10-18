/**
 * Leaflet 컨트롤 패널 드래그 기능
 * 마우스로 패널 위치 이동 가능
 */

class DraggableControl {
    constructor() {
        this.isDragging = false;
        this.currentX = 0;
        this.currentY = 0;
        this.initialX = 0;
        this.initialY = 0;
        this.xOffset = 0;
        this.yOffset = 0;
    }
    
    makeDraggable(element) {
        const header = element.querySelector('h4') || element.querySelector('div:first-child');
        
        if (!header) return;
        
        // 드래그 가능 표시
        header.style.cursor = 'move';
        header.style.userSelect = 'none';
        header.title = '드래그하여 이동';
        
        // 이벤트 리스너
        header.addEventListener('mousedown', this.dragStart.bind(this));
        document.addEventListener('mousemove', this.drag.bind(this));
        document.addEventListener('mouseup', this.dragEnd.bind(this));
        
        // 터치 이벤트도 지원
        header.addEventListener('touchstart', this.dragStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.drag.bind(this), { passive: false });
        document.addEventListener('touchend', this.dragEnd.bind(this));
        
        // 초기 위치 저장
        this.element = element;
        this.setTranslate(0, 0, element);
    }
    
    dragStart(e) {
        // Leaflet 지도 이벤트 차단
        e.stopPropagation();
        
        if (e.type === 'touchstart') {
            this.initialX = e.touches[0].clientX - this.xOffset;
            this.initialY = e.touches[0].clientY - this.yOffset;
        } else {
            this.initialX = e.clientX - this.xOffset;
            this.initialY = e.clientY - this.yOffset;
        }
        
        if (e.target.closest('h4') || e.target.closest('div:first-child')) {
            this.isDragging = true;
            this.element.style.transition = 'none';
            this.element.style.zIndex = '10000'; // 최상단으로
        }
    }
    
    drag(e) {
        if (this.isDragging) {
            e.preventDefault();
            e.stopPropagation(); // 지도 이벤트 차단
            
            if (e.type === 'touchmove') {
                this.currentX = e.touches[0].clientX - this.initialX;
                this.currentY = e.touches[0].clientY - this.initialY;
            } else {
                this.currentX = e.clientX - this.initialX;
                this.currentY = e.clientY - this.initialY;
            }
            
            this.xOffset = this.currentX;
            this.yOffset = this.currentY;
            
            this.setTranslate(this.currentX, this.currentY, this.element);
        }
    }
    
    dragEnd(e) {
        e.stopPropagation(); // 지도 이벤트 차단
        this.initialX = this.currentX;
        this.initialY = this.currentY;
        this.isDragging = false;
    }
    
    setTranslate(xPos, yPos, el) {
        el.style.transform = `translate(${xPos}px, ${yPos}px)`;
    }
}

// 패널들에 드래그 기능 추가
window.addEventListener('load', () => {
    setTimeout(() => {
        // 어선 위험도 패널
        const fishingPanel = document.querySelector('.fishing-risk-controls');
        if (fishingPanel) {
            const draggable1 = new DraggableControl();
            draggable1.makeDraggable(fishingPanel);
            console.log('✅ 어선 위험도 패널 드래그 가능');
        }
        
        // 어선 추적 패널
        const vesselPanel = document.querySelector('.vessel-animation-controls');
        if (vesselPanel) {
            const draggable2 = new DraggableControl();
            draggable2.makeDraggable(vesselPanel);
            console.log('✅ 어선 추적 패널 드래그 가능');
        }
    }, 3000);
});

window.DraggableControl = DraggableControl;
