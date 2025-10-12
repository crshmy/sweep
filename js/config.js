// 애플리케이션 설정 파일

const CONFIG = {
    // 기본 설정
    app: {
        name: '해양쓰레기 수거 네비게이션',
        version: '1.0.0',
        defaultVesselName: '클린오션-1호'
    },

    // 지도 설정
    map: {
        defaultCenter: [35.1796, 129.0756], // 부산 앞바다
        defaultZoom: 11,
        minZoom: 8,
        maxZoom: 18,
        tileLayer: {
            url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attribution: '© OpenStreetMap contributors'
        }
    },

    // 마커 색상
    colors: {
        vessel: '#2196f3',
        aisVessel: '#64b5f6',
        hotspot: {
            high: '#f44336',
            medium: '#ff9800',
            low: '#4caf50'
        },
        route: '#2196f3'
    },

    // 데이터 업데이트 주기 (밀리초)
    updateIntervals: {
        position: 3000,      // 3초 - 선박 위치
        ais: 30000,          // 30초 - AIS 데이터
        weather: 300000,     // 5분 - 기상 정보
        hotspots: 600000,    // 10분 - 핫스팟 정보
        currents: 3600000    // 1시간 - 해류 정보
    },

    // API 엔드포인트 (실제 API로 교체)
    api: {
        ais: {
            enabled: false,
            endpoint: 'https://your-api.com/ais',
            apiKey: '' // 환경 변수로 관리 권장
        },
        hotspots: {
            enabled: false,
            endpoint: 'https://your-api.com/hotspots',
            apiKey: ''
        },
        weather: {
            enabled: false,
            endpoint: 'https://your-api.com/weather',
            apiKey: ''
        },
        currents: {
            enabled: false,
            endpoint: 'https://your-api.com/currents',
            apiKey: ''
        },
        optimization: {
            enabled: false,
            endpoint: 'https://your-api.com/optimize',
            apiKey: ''
        }
    },

    // 경로 최적화 설정
    optimization: {
        algorithm: 'tsp', // tsp, greedy, genetic
        maxWaypoints: 20,
        considerWeather: true,
        considerFuel: true,
        considerPriority: true,
        safetyMargin: 1.2 // 거리에 곱할 안전 계수
    },

    // 알림 설정
    alerts: {
        weatherWarning: {
            enabled: true,
            windSpeedThreshold: 15, // m/s
            waveHeightThreshold: 2.5 // m
        },
        collisionWarning: {
            enabled: true,
            distanceThreshold: 2, // km
            checkInterval: 10000 // 10초
        },
        newHotspotAlert: {
            enabled: true,
            priorityFilter: ['high', 'medium'] // 알림 받을 우선순위
        }
    },

    // 작업 설정
    collection: {
        workingHoursStart: 6, // 06:00
        workingHoursEnd: 18,  // 18:00
        maxWorkingHours: 8,   // 하루 최대 작업 시간
        breakDuration: 60,    // 휴식 시간 (분)
        targetDailyCollection: 500 // 일일 목표 수거량 (kg)
    },

    // GPS 설정
    gps: {
        enabled: false, // 실제 GPS 사용 여부
        highAccuracy: true,
        timeout: 10000,
        maximumAge: 0
    },

    // 로깅 설정
    logging: {
        enabled: true,
        level: 'info', // debug, info, warn, error
        console: true,
        remote: false,
        remoteEndpoint: 'https://your-api.com/logs'
    },

    // 데이터 캐싱
    cache: {
        enabled: true,
        duration: {
            ais: 60000,      // 1분
            weather: 300000, // 5분
            hotspots: 600000 // 10분
        }
    },

    // UI 설정
    ui: {
        theme: 'dark', // dark, light
        language: 'ko', // ko, en
        showCoordinates: true,
        showSpeed: true,
        showDistance: true,
        animateMarkers: true,
        clusterMarkers: false // 마커 클러스터링 사용 여부
    },

    // 성능 설정
    performance: {
        maxMarkers: 100,
        maxAISVessels: 50,
        maxHotspots: 30,
        debounceDelay: 300,
        throttleDelay: 1000
    },

    // 안전 설정
    safety: {
        minSafeDistance: 0.5, // 다른 선박과의 최소 안전 거리 (km)
        maxWindSpeed: 25,     // 작업 가능한 최대 풍속 (m/s)
        maxWaveHeight: 3,     // 작업 가능한 최대 파고 (m)
        minVisibility: 5,     // 작업 가능한 최소 가시거리 (km)
        emergencyContacts: [
            { name: '해양경찰', phone: '122' },
            { name: '해양환경공단', phone: '1833-8682' }
        ]
    },

    // 데이터 내보내기 설정
    export: {
        formats: ['csv', 'json', 'xlsx'],
        defaultFormat: 'csv',
        includeMetadata: true
    }
};

// 설정 검증 함수
function validateConfig() {
    const errors = [];

    // 필수 설정 확인
    if (!CONFIG.map.defaultCenter || CONFIG.map.defaultCenter.length !== 2) {
        errors.push('올바른 기본 지도 중심 좌표가 필요합니다.');
    }

    // 좌표 유효성 확인
    const [lat, lon] = CONFIG.map.defaultCenter;
    if (!isValidCoordinate(lat, lon)) {
        errors.push('유효하지 않은 좌표입니다.');
    }

    // 업데이트 주기 확인
    for (const key in CONFIG.updateIntervals) {
        if (CONFIG.updateIntervals[key] < 1000) {
            errors.push(`${key} 업데이트 주기가 너무 짧습니다 (최소 1초).`);
        }
    }

    if (errors.length > 0) {
        console.error('설정 검증 실패:', errors);
        return false;
    }

    console.log('설정 검증 성공');
    return true;
}

// 설정 저장
function saveConfig() {
    try {
        localStorage.setItem('nav_config', JSON.stringify(CONFIG));
        console.log('설정이 저장되었습니다.');
        return true;
    } catch (error) {
        console.error('설정 저장 실패:', error);
        return false;
    }
}

// 설정 불러오기
function loadConfig() {
    try {
        const saved = localStorage.getItem('nav_config');
        if (saved) {
            const loadedConfig = JSON.parse(saved);
            // 저장된 설정을 현재 설정과 병합
            Object.assign(CONFIG, loadedConfig);
            console.log('저장된 설정을 불러왔습니다.');
            return true;
        }
    } catch (error) {
        console.error('설정 불러오기 실패:', error);
    }
    return false;
}

// 설정 초기화
function resetConfig() {
    localStorage.removeItem('nav_config');
    location.reload();
}

// 특정 API가 활성화되었는지 확인
function isAPIEnabled(apiName) {
    return CONFIG.api[apiName] && CONFIG.api[apiName].enabled;
}

// API 엔드포인트 가져오기
function getAPIEndpoint(apiName) {
    if (!isAPIEnabled(apiName)) {
        console.warn(`${apiName} API가 비활성화되어 있습니다.`);
        return null;
    }
    return CONFIG.api[apiName].endpoint;
}

// API 키 가져오기
function getAPIKey(apiName) {
    if (!isAPIEnabled(apiName)) {
        return null;
    }
    return CONFIG.api[apiName].apiKey;
}

// 초기화 시 설정 검증
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', () => {
        loadConfig();
        validateConfig();
    });
}

// 설정을 전역으로 export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}