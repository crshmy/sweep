# 🌊 대한해협 부유쓰레기 수거 최적화 네비게이션

실시간 기상 데이터를 활용한 해양 부유쓰레기 효율적 수거 시스템

## ✨ 주요 기능

### 🎯 핵심 기능
- **실시간 선박 추적**: GPS 기반 위치 추적 및 경로 기록
- **🌬️ 실시간 기상 레이어**: OpenWeatherMap API 연동
  - 바람 화살표 시각화 (풍향/풍속)
  - 파도 높이 히트맵
  - 10분 단위 자동 갱신
- **🧭 기상 기반 경로 최적화**: A* 알고리즘 + 바람/파도 고려
  - 안전한 항로 자동 계산
  - 위험 기상 구역 회피
  - 쓰레기 밀집도 우선순위 반영
- **AIS 어선 회피 시스템**: 충돌 방지 알고리즘
- **쓰레기 밀집 예측**: 우선순위 기반 수거 계획

### 📊 데이터 시각화
- Leaflet 기반 인터랙티브 지도
- 실시간 애니메이션 (선박 이동, 펄스 효과)
- 다중 레이어 관리 (AIS, 핫스팟, 기상)
- 커스텀 마커 및 경로 표시

## 🛠️ 기술 스택

### Frontend
- **HTML5/CSS3**: 반응형 UI, 다크 테마
- **JavaScript (ES6+)**: 비동기 처리, 클래스 기반 아키텍처
- **Leaflet.js 1.9.4**: 지도 라이브러리
- **CSS Animations**: 부드러운 애니메이션 효과

### 데이터 소스
- **OpenWeatherMap API**: 실시간 기상 데이터
  - 풍향/풍속
  - 파고 추정
  - 가시거리
- **AI Hub AIS 데이터**: 어선 이동 패턴 학습 (예정)
- **기상청 API**: 국내 해역 상세 기상 (복구 대기)

### 알고리즘
- **A* 경로 탐색**: 기상 조건 가중치 적용
- **휴리스틱 최적화**: 거리 + 풍속 + 파고 복합 계산
- **충돌 회피**: 실시간 거리 계산 및 경고

## 📁 프로젝트 구조

```
marine_cleanup_nav/
├── index.html                 # 메인 HTML
├── css/
│   ├── styles.css            # 기본 스타일
│   └── animations.css        # 애니메이션 정의
├── js/
│   ├── app-animated.js       # 메인 애플리케이션
│   ├── weather-layer.js      # 🌬️ 기상 레이어 시스템 (NEW)
│   ├── route-optimizer.js    # 🧭 경로 최적화 엔진 (NEW)
│   ├── weather-integration.js # 통합 컨트롤러 (NEW)
│   ├── fishing-addon.js      # 어선 회피 시스템
│   ├── config.js             # 설정 파일
│   └── utils.js              # 유틸리티 함수
├── data/                      # 데이터 파일 (예정)
└── docs/                      # 문서
```

## 🚀 시작하기

### 1. 프로젝트 클론
```bash
git clone [repository-url]
cd marine_cleanup_nav
```

### 2. OpenWeatherMap API 키 발급
1. https://openweathermap.org/api 방문
2. 무료 계정 생성
3. API 키 발급 (1000 calls/day 무료)

### 3. API 키 설정
`js/weather-layer.js` 파일에서:
```javascript
this.OWM_API_KEY = 'YOUR_API_KEY_HERE'; // 여기에 키 입력
```

### 4. 실행
```bash
# 로컬 서버 실행 (Python)
python -m http.server 8000

# 또는 Node.js
npx http-server

# 브라우저에서 열기
http://localhost:8000
```

## 🎮 사용 방법

### 기본 조작
1. **지도 이동**: 드래그 또는 화살표 키
2. **줌**: 마우스 휠 또는 +/- 버튼
3. **선박 추적**: 📍 버튼 클릭
4. **레이어 관리**: 🗂️ 버튼 클릭

### 기상 레이어 사용
1. 🌬️ 버튼 클릭하여 기상 범례 표시
2. 레이어 패널에서 체크박스 토글:
   - **🌬️ 바람 화살표**: 풍향/풍속 표시
   - **🌊 파도 표시**: 파고 히트맵
3. 🔄 버튼으로 수동 갱신

### 경로 최적화
1. 우측 "🧭 기상 기반 경로 계산" 버튼 클릭
2. 시스템이 자동으로:
   - 현재 기상 데이터 수집
   - 핫스팟 우선순위 정렬
   - A* 알고리즘으로 최적 경로 계산
   - 지도에 경로 표시
3. 경로 정보 확인:
   - 총 거리
   - 예상 소요 시간
   - 경유지 개수

### 기상 경고
- **강풍 주의** (15+ m/s): 주황색 경고
- **높은 파도** (2.5+ m): 주황색 경고
- **작업 중단 권고** (20+ m/s 또는 3.5+ m 파고): 빨간색 위험

## 🧮 알고리즘 상세

### A* 경로 탐색 (기상 반영)
```
비용 함수: f(n) = g(n) + h(n) + w(n)

g(n): 시작점에서 n까지의 실제 거리
h(n): n에서 목표까지의 추정 거리 (휴리스틱)
w(n): 기상 비용
  - 풍속 비용: (wind_speed / 10)² × 0.3
  - 파고 비용: (wave_height / 2)² × 0.4
  - 위험 구역: +9999 (거의 통과 불가)
```

### 파고 추정식
```
H ≈ 0.21 × V^1.5 / 9.8
(H: 파고(m), V: 풍속(m/s))
```

### 핫스팟 우선순위 점수
```
score = priority_weight - distance × 2

priority_weight:
  - high: 100점
  - medium: 50점
  - low: 20점
```

## 📊 데이터 흐름

```
1. [OpenWeatherMap API]
   ↓ 10분마다
2. [WeatherLayer.fetchWeatherData()]
   ↓ 격자(0.1°) 샘플링
3. [gridData Map 저장]
   ↓ 캐싱 (10분 유효)
4. [UI 업데이트 + 레이어 생성]
   ↓ 사용자 요청 시
5. [WeatherAwareRouter.calculateOptimalRoute()]
   ↓ A* 알고리즘
6. [최적 경로 반환 + 지도 표시]
```

## ⚙️ 설정

### config.js 주요 설정
```javascript
// 업데이트 주기
updateIntervals: {
    weather: 600000,     // 10분 - 기상
    ais: 30000,          // 30초 - AIS
    position: 3000       // 3초 - 위치
}

// 경로 최적화
optimization: {
    considerWeather: true,
    maxWindSpeed: 20,    // 최대 허용 풍속
    maxWaveHeight: 3.0   // 최대 허용 파고
}
```

## 🐛 문제 해결

### API 호출 실패
```javascript
// 콘솔 확인
> ❌ API 오류: 401

// 해결: API 키 확인
// js/weather-layer.js에서 올바른 키 입력
```

### 기상 레이어 안 보임
```javascript
// 레이어 패널에서 체크박스 활성화
// 또는 콘솔에서 수동 활성화:
weatherLayer.toggleWindLayer();
```

### 경로 계산 느림
```javascript
// A* 탐색 제한 확인
// js/route-optimizer.js:
if (closedSet.size > 500) {
    // 500 → 더 큰 값으로 증가 (더 정확하지만 느림)
}
```

## 🔄 향후 개발 계획

### Phase 1: 데이터 통합 (진행중)
- [x] OpenWeatherMap API 연동
- [x] 기상 기반 경로 최적화
- [ ] AI Hub AIS 데이터 전처리
- [ ] 기상청 API 복구 대기

### Phase 2: 머신러닝 (예정)
- [ ] TensorFlow.js 어선 패턴 예측
- [ ] 쓰레기 밀집도 예측 모델
- [ ] 최적 수거 시간 추천

### Phase 3: 고도화 (예정)
- [ ] 실시간 AIS 수신 (VHF)
- [ ] 오프라인 모드 (IndexedDB)
- [ ] 작업 일지 자동 생성
- [ ] 다중 선박 동시 관리

## 📈 성능 최적화

### 현재 최적화
- **레이어 캐싱**: 10분 유효기간
- **격자 샘플링**: 최대 20개 지점 (API 호출 제한)
- **A* 탐색 제한**: 500개 노드 (무한루프 방지)
- **애니메이션 최적화**: requestAnimationFrame + GPU 가속

### 메모리 사용
- 기상 데이터 캐시: ~50KB
- 지도 타일: ~2MB (캐시 자동 관리)
- 선박 경로: ~10KB (50개 포인트)

## 🤝 기여 가이드

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

MIT License - 자유롭게 사용 가능

## 🙏 크레딧

- **Leaflet**: BSD 2-Clause License
- **OpenWeatherMap**: API 무료 플랜
- **AI Hub**: 한국지능정보사회진흥원
- **기상청**: 공공데이터포털 (복구 대기)

## 📧 문의

프로젝트 관련 문의: [your-email]

---

## 🎓 보고서용 요약

### 시스템 특징
1. **실시간 기상 데이터 통합**: OpenWeatherMap API를 활용한 풍향/풍속/파고 실시간 모니터링
2. **기상 기반 경로 최적화**: A* 알고리즘에 기상 비용 함수를 적용하여 안전하고 효율적인 항로 계산
3. **시각화 시스템**: Leaflet 기반 인터랙티브 지도에 바람 화살표, 파도 히트맵, 선박 애니메이션 통합
4. **위험 경고 시스템**: 풍속 15m/s 이상, 파고 2.5m 이상 시 자동 경고 발생

### 기술적 성과
- 비동기 API 통합으로 끊김없는 사용자 경험 제공
- 격자 기반 샘플링으로 API 호출 최소화 (비용 절감)
- 캐싱 전략으로 오프라인 환경 대응 준비
- 모듈화된 아키텍처로 확장성 확보

### 실용성
- 실제 선박 운항 시 기상 조건을 고려한 의사결정 지원
- 위험 구역 사전 회피로 안전성 향상
- 효율적 경로로 연료 소비 감소 및 작업 시간 단축

---

**Made with 🌊 for cleaner oceans**
