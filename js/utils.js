// 유틸리티 함수 모음

/**
 * 두 지점 간의 거리 계산 (Haversine formula)
 * @param {Array} point1 - [위도, 경도]
 * @param {Array} point2 - [위도, 경도]
 * @returns {number} 거리 (km)
 */
function calculateDistance(point1, point2) {
    const R = 6371; // 지구 반지름 (km)
    const lat1 = point1[0] * Math.PI / 180;
    const lat2 = point2[0] * Math.PI / 180;
    const deltaLat = (point2[0] - point1[0]) * Math.PI / 180;
    const deltaLon = (point2[1] - point1[1]) * Math.PI / 180;

    const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
              Math.cos(lat1) * Math.cos(lat2) *
              Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;

    return distance;
}

/**
 * 거리를 포맷팅
 * @param {number} distanceKm - 거리 (km)
 * @returns {string} 포맷된 거리 문자열
 */
function formatDistance(distanceKm) {
    if (distanceKm < 1) {
        return `${(distanceKm * 1000).toFixed(0)} m`;
    }
    return `${distanceKm.toFixed(1)} km`;
}

/**
 * 두 지점 간의 방향 계산
 * @param {Array} from - 시작 지점 [위도, 경도]
 * @param {Array} to - 도착 지점 [위도, 경도]
 * @returns {number} 방위각 (도)
 */
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

/**
 * 도수를 방위로 변환
 * @param {number} degrees - 방위각 (0-360)
 * @returns {string} 방위 (N, NE, E, SE, S, SW, W, NW)
 */
function degreesToDirection(degrees) {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(degrees / 45) % 8;
    return directions[index];
}

/**
 * 속도를 다양한 단위로 변환
 * @param {number} knots - 속도 (knots)
 * @returns {Object} 다양한 단위의 속도
 */
function convertSpeed(knots) {
    return {
        knots: knots,
        kmh: knots * 1.852,
        mph: knots * 1.15078,
        ms: knots * 0.514444
    };
}

/**
 * 도착 예상 시간 계산
 * @param {number} distanceKm - 거리 (km)
 * @param {number} speedKnots - 속도 (knots)
 * @returns {Object} 예상 시간 정보
 */
function calculateETA(distanceKm, speedKnots) {
    const speedKmh = speedKnots * 1.852;
    const hours = distanceKm / speedKmh;
    const totalMinutes = Math.round(hours * 60);
    const displayHours = Math.floor(totalMinutes / 60);
    const displayMinutes = totalMinutes % 60;

    return {
        totalMinutes: totalMinutes,
        hours: displayHours,
        minutes: displayMinutes,
        formatted: `${displayHours}시간 ${displayMinutes}분`
    };
}

/**
 * 날짜/시간 포맷팅
 * @param {Date} date - 날짜 객체
 * @returns {Object} 포맷된 날짜/시간
 */
function formatDateTime(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return {
        date: `${year}-${month}-${day}`,
        time: `${hours}:${minutes}:${seconds}`,
        datetime: `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`,
        timestamp: date.getTime()
    };
}

/**
 * 상대 시간 표시 (몇 분 전, 몇 시간 전 등)
 * @param {Date|string} date - 날짜 객체 또는 ISO 문자열
 * @returns {string} 상대 시간 문자열
 */
function getRelativeTime(date) {
    const now = new Date();
    const then = typeof date === 'string' ? new Date(date) : date;
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '방금 전';
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays < 7) return `${diffDays}일 전`;
    
    return then.toLocaleDateString('ko-KR');
}

/**
 * 경로 간 총 거리 계산
 * @param {Array} waypoints - 경유지 배열 [[lat, lon], ...]
 * @returns {number} 총 거리 (km)
 */
function calculateTotalRouteDistance(waypoints) {
    let totalDistance = 0;
    for (let i = 0; i < waypoints.length - 1; i++) {
        totalDistance += calculateDistance(waypoints[i], waypoints[i + 1]);
    }
    return totalDistance;
}

/**
 * 풍속을 뷰포트 풍력 계급으로 변환
 * @param {number} speedMs - 풍속 (m/s)
 * @returns {Object} 풍력 계급 정보
 */
function windSpeedToBeaufort(speedMs) {
    const beaufortScale = [
        { scale: 0, max: 0.3, name: '고요', description: '연기가 수직으로 올라감' },
        { scale: 1, max: 1.5, name: '실바람', description: '풍향을 연기로 알 수 있음' },
        { scale: 2, max: 3.3, name: '남실바람', description: '얼굴에 바람이 느껴짐' },
        { scale: 3, max: 5.4, name: '산들바람', description: '나뭇잎과 가는 가지가 흔들림' },
        { scale: 4, max: 7.9, name: '건들바람', description: '먼지가 일고 작은 가지가 흔들림' },
        { scale: 5, max: 10.7, name: '흔들바람', description: '작은 나무가 흔들림' },
        { scale: 6, max: 13.8, name: '된바람', description: '큰 나뭇가지가 흔들림' },
        { scale: 7, max: 17.1, name: '센바람', description: '나무 전체가 흔들림' },
        { scale: 8, max: 20.7, name: '큰바람', description: '나뭇가지가 꺾임' },
        { scale: 9, max: 24.4, name: '큰센바람', description: '건물에 약간 피해' },
        { scale: 10, max: 28.4, name: '노대바람', description: '나무가 뿌리째 뽑힐 수 있음' },
        { scale: 11, max: 32.6, name: '왕바람', description: '큰 피해' },
        { scale: 12, max: Infinity, name: '싹쓸바람', description: '막대한 피해' }
    ];

    for (const level of beaufortScale) {
        if (speedMs <= level.max) {
            return level;
        }
    }
}

/**
 * 좌표가 유효한지 확인
 * @param {number} lat - 위도
 * @param {number} lon - 경도
 * @returns {boolean} 유효 여부
 */
function isValidCoordinate(lat, lon) {
    return lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
}

/**
 * 에러 메시지 표시
 * @param {string} message - 에러 메시지
 */
function showErrorAlert(message) {
    // 실제 구현 시 더 나은 UI로 교체 가능
    const alertDiv = document.createElement('div');
    alertDiv.className = 'error-alert';
    alertDiv.textContent = message;
    alertDiv.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: #f44336;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
}

/**
 * 성공 메시지 표시
 * @param {string} message - 성공 메시지
 */
function showSuccessAlert(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'success-alert';
    alertDiv.textContent = message;
    alertDiv.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: #4caf50;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => alertDiv.remove(), 300);
    }, 3000);
}

/**
 * 로딩 스피너 표시/숨김
 * @param {boolean} show - 표시 여부
 */
function toggleLoadingSpinner(show) {
    let spinner = document.getElementById('loading-spinner');
    
    if (show) {
        if (!spinner) {
            spinner = document.createElement('div');
            spinner.id = 'loading-spinner';
            spinner.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 60px;
                height: 60px;
                border: 5px solid #f3f3f3;
                border-top: 5px solid #2196f3;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                z-index: 10001;
            `;
            document.body.appendChild(spinner);
        }
        spinner.style.display = 'block';
    } else {
        if (spinner) {
            spinner.style.display = 'none';
        }
    }
}

/**
 * 로컬 스토리지에 데이터 저장
 * @param {string} key - 키
 * @param {*} data - 저장할 데이터
 */
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('로컬 스토리지 저장 실패:', error);
        return false;
    }
}

/**
 * 로컬 스토리지에서 데이터 가져오기
 * @param {string} key - 키
 * @returns {*} 저장된 데이터 또는 null
 */
function loadFromLocalStorage(key) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    } catch (error) {
        console.error('로컬 스토리지 로드 실패:', error);
        return null;
    }
}

/**
 * 데이터를 CSV로 내보내기
 * @param {Array} data - 데이터 배열
 * @param {string} filename - 파일명
 */
function exportToCSV(data, filename = 'export.csv') {
    if (!data || data.length === 0) {
        showErrorAlert('내보낼 데이터가 없습니다.');
        return;
    }

    const headers = Object.keys(data[0]);
    const csvContent = [
        headers.join(','),
        ...data.map(row => headers.map(header => 
            JSON.stringify(row[header] || '')
        ).join(','))
    ].join('\n');

    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    
    showSuccessAlert('CSV 파일이 다운로드되었습니다.');
}

/**
 * 디바운스 함수
 * @param {Function} func - 실행할 함수
 * @param {number} wait - 대기 시간 (ms)
 * @returns {Function} 디바운스된 함수
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 쓰로틀 함수
 * @param {Function} func - 실행할 함수
 * @param {number} limit - 제한 시간 (ms)
 * @returns {Function} 쓰로틀된 함수
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
    
    @keyframes spin {
        0% { transform: translate(-50%, -50%) rotate(0deg); }
        100% { transform: translate(-50%, -50%) rotate(360deg); }
    }
`;
document.head.appendChild(style);