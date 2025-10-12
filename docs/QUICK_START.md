# 🚀 빠른 시작 가이드

## 📦 설치 및 실행

### 1단계: 파일 확인
다음 파일들이 `C:\ClaudeFolder\marine_cleanup_nav` 폴더에 있는지 확인하세요:

```
marine_cleanup_nav/
├── index.html                  # 메인 화면
├── styles.css                  # 스타일시트
├── app.js                      # 메인 로직
├── config.js                   # 설정 파일
├── utils.js                    # 유틸리티 함수
├── test.html                   # 테스트 페이지
├── README.md                   # 설명서
└── API_INTEGRATION_GUIDE.md    # API 연동 가이드
```

### 2단계: 실행 방법

#### 🌐 방법 A: 웹 브라우저로 직접 열기 (가장 간단)
1. `index.html` 파일을 더블클릭
2. 기본 웹 브라우저에서 자동 실행

#### 🖥️ 방법 B: 로컬 서버 실행 (권장)

**Python이 있는 경우:**
```bash
cd C:\ClaudeFolder\marine_cleanup_nav
python -m http.server 8000
```

**Node.js가 있는 경우:**
```bash
cd C:\ClaudeFolder\marine_cleanup_nav
npx http-server -p 8000
```

그 다음 브라우저에서 `http://localhost:8000` 접속

### 3단계: 시스템 테스트
1. 브라우저에서 `test.html` 파일 열기
2. 각 테스트 버튼 클릭하여 모든 기능 확인
3. 모든 테스트가 통과하면 정상 작동

---

## 🎮 기본 사용법

### 첫 화면 이해하기

#### 헤더 (상단)
- **선박명**: 현재 선박 이름
- **운항 상태**: 운항중/정박중/작업중
- **시계**: 현재 시간
- **긴급 버튼**: 긴급 상황 시 클릭

#### 좌측 패널
1. **현재 위치**: 위도, 경도, 속도, 방향
2. **기상 정보**: 기온, 풍향, 풍속, 파고
3. **쓰레기 핫스팟 목록**: 클릭하면 해당 위치로 이동

#### 중앙 지도
- **파란색 점**: 내 선박
- **빨간색/주황색/초록색 점**: 쓰레기 핫스팟 (우선순위)
- **하늘색 점**: 주변 선박 (AIS)
- **점선**: 최적화된 경로

#### 우측 패널
1. **경로 정보**: 거리, 시간, 핫스팟 수
2. **수거 현황**: 오늘 수거량, 완료 지점, 작업 시간
3. **주변 선박**: AIS 선박 목록
4. **알림**: 기상 경보, 새로운 핫스팟 등

### 주요 기능 사용하기

#### 🗺️ 지도 조작
- **확대/축소**: 마우스 휠
- **이동**: 드래그
- **현재 위치로**: 📍 버튼

#### 🎯 핫스팟 확인
1. 좌측 패널에서 핫스팟 항목 클릭
2. 지도가 자동으로 해당 위치 표시
3. 팝업에서 상세 정보 확인

#### 🛣️ 경로 최적화
1. 우측 패널에서 "경로 최적화" 버튼 클릭
2. 자동으로 최적 경로 계산
3. 파란색 점선으로 경로 표시

#### 🗂️ 레이어 토글
1. 지도 우측 상단 🗂️ 버튼 클릭
2. 원하는 레이어 체크/해제:
   - AIS 선박 위치
   - 쓰레기 핫스팟
   - 풍향/풍속 (향후 추가)
   - 해류 (향후 추가)

---

## ⚙️ 설정 변경하기

### 기본 위치 변경
`config.js` 파일 열기:
```javascript
map: {
    defaultCenter: [위도, 경도],  // 예: [35.1796, 129.0756]
    defaultZoom: 11
}
```

### 선박 이름 변경
`config.js` 파일:
```javascript
app: {
    defaultVesselName: '원하는 선박명'
}
```

### 색상 테마 변경
`config.js` 파일:
```javascript
colors: {
    vessel: '#원하는색상',
    hotspot: {
        high: '#빨간색',
        medium: '#주황색',
        low: '#초록색'
    }
}
```

---

## 🔌 실제 데이터 연동하기

현재는 **모의 데이터**로 작동합니다. 실제 데이터를 연동하려면:

### 1. API 키 준비
필요한 API 서비스:
- **AIS 데이터**: MarineTraffic, AISHub 등
- **기상 정보**: 기상청, OpenWeatherMap 등
- **해양 정보**: NOAA, Copernicus 등

### 2. config.js 수정
```javascript
api: {
    ais: {
        enabled: true,  // false를 true로 변경
        endpoint: 'https://your-ais-api.com/data',
        apiKey: 'YOUR_API_KEY_HERE'
    },
    weather: {
        enabled: true,
        endpoint: 'https://your-weather-api.com/data',
        apiKey: 'YOUR_API_KEY_HERE'
    }
    // ... 기타 API 설정
}
```

### 3. app.js의 API 함수 수정
`API_INTEGRATION_GUIDE.md` 문서를 참조하여 각 API 함수를 실제 엔드포인트로 수정

---

## 🐛 문제 해결

### 지도가 표시되지 않음
- **원인**: 인터넷 연결 문제 또는 Leaflet 로드 실패
- **해결**: 
  1. 인터넷 연결 확인
  2. 브라우저 콘솔(F12) 확인
  3. 페이지 새로고침 (Ctrl + F5)

### 데이터가 업데이트되지 않음
- **원인**: API가 비활성화되어 있음 (정상)
- **해결**: 
  - 현재는 모의 데이터로 작동
  - 실제 API 연동 시 `config.js`에서 활성화

### 선박이 움직이지 않음
- **원인**: GPS가 비활성화되어 있음 (정상)
- **해결**: 
  - 3초마다 임의 위치 변경 (시뮬레이션)
  - 실제 GPS 연동 시 `config.js`에서 활성화

### 경로 최적화가 작동하지 않음
- **원인**: 최적화 알고리즘 미구현 (알림만 표시)
- **해결**: 
  - 실제 구현 필요
  - `API_INTEGRATION_GUIDE.md` 참조

---

## 📊 데이터 구조

### 핫스팟 데이터 형식
```javascript
{
    id: 1,
    name: "핫스팟 이름",
    lat: 35.2,
    lon: 129.15,
    priority: "high",  // high, medium, low
    estimatedWaste: "500kg 이상",
    type: "플라스틱, 스티로폼",
    distance: "5.2 km"
}
```

### AIS 데이터 형식
```javascript
{
    id: 1,
    name: "선박명",
    type: "화물선",
    lat: 35.19,
    lon: 129.08,
    speed: "14.2 knots",
    heading: "125°",
    distance: "2.3 km"
}
```

### 기상 데이터 형식
```javascript
{
    temperature: 23,
    windDirection: "북동 15°",
    windSpeed: "8.5 m/s",
    waveHeight: "1.2 m",
    visibility: "15 km"
}
```

---

## 🔐 보안 주의사항

### API 키 관리
❌ **하지 말 것:**
```javascript
// 클라이언트 코드에 API 키 직접 입력
const API_KEY = 'my-secret-key-12345';
```

✅ **올바른 방법:**
```javascript
// 백엔드 서버를 통해 API 호출
fetch('/api/proxy/weather')
```

### CORS 문제
- 직접 API 호출 시 CORS 에러 발생 가능
- 백엔드 프록시 서버 구축 권장
- `API_INTEGRATION_GUIDE.md` 참조

---

## 📱 브라우저 호환성

### 지원 브라우저
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### 권장 사양
- 화면 해상도: 1920x1080 이상
- RAM: 4GB 이상
- 인터넷: 상시 연결 (10Mbps 이상)

---

## 💡 팁 & 트릭

### 1. 핫스팟 빠르게 찾기
- 좌측 패널의 목록을 우선순위별로 정렬
- 빨간색(HIGH) > 주황색(MEDIUM) > 초록색(LOW)

### 2. 경로 효율적으로 계획하기
- 풍향과 해류를 고려
- 연료 소비량 계산
- 기상 예보 확인

### 3. 데이터 내보내기
- 브라우저 콘솔에서 실행:
```javascript
exportToCSV(mockData.hotspots, 'hotspots.csv');
```

### 4. 커스텀 마커 추가
`app.js`에서 마커 생성 코드 수정

### 5. 단축키 (향후 추가 예정)
- `C`: 현재 위치로 이동
- `L`: 레이어 패널 토글
- `R`: 경로 최적화

---

## 📞 도움말

### 추가 문서
- **상세 매뉴얼**: `README.md`
- **API 연동**: `API_INTEGRATION_GUIDE.md`
- **테스트**: `test.html`

### 문제 발생 시
1. `test.html`로 시스템 진단
2. 브라우저 콘솔(F12) 에러 확인
3. GitHub Issues 등록

---

## 🎯 다음 단계

### 초보자
1. ✅ `index.html` 실행하여 기본 UI 확인
2. ✅ `test.html`로 시스템 테스트
3. ✅ 지도 조작 및 핫스팟 클릭 연습
4. ✅ `config.js`에서 기본 설정 변경

### 중급자
1. ✅ 모의 데이터 수정하여 다양한 시나리오 테스트
2. ✅ `utils.js` 함수들을 활용한 커스터마이징
3. ✅ CSS 수정으로 디자인 변경
4. ✅ 새로운 기능 추가 (예: 날씨 위젯)

### 고급자
1. ✅ 실제 API 연동 (AIS, 기상청 등)
2. ✅ 경로 최적화 알고리즘 구현
3. ✅ 백엔드 서버 구축
4. ✅ 모바일 앱 버전 개발

---

## ✨ 주요 파일 설명

| 파일 | 역할 | 수정 빈도 |
|------|------|----------|
| `index.html` | 메인 UI 구조 | 낮음 |
| `styles.css` | 디자인/레이아웃 | 중간 |
| `app.js` | 핵심 로직 | 높음 |
| `config.js` | 설정 관리 | 높음 |
| `utils.js` | 유틸리티 함수 | 낮음 |
| `test.html` | 테스트 도구 | 낮음 |

---

## 🎉 완료!

이제 해양쓰레기 수거 네비게이션 시스템을 사용할 준비가 되었습니다!

**시작하기**: `index.html`을 열어보세요!

질문이나 문제가 있다면 언제든지 문의하세요.

**Made with 💙 for Ocean Conservation**