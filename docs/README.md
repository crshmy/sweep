# 🌊 해양쓰레기 수거 최적화 네비게이션 시스템

해양쓰레기 수거 작업을 위한 실시간 네비게이션 시스템입니다. AIS 선박 위치 추적, 쓰레기 핫스팟 예측, 기상/해류 정보, 최적 경로 계산 기능을 제공합니다.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ 주요 기능

### 📍 실시간 위치 추적
- 선박의 현재 위치, 속도, 방향 표시
- GPS 기반 정확한 위치 정보
- 자동 화면 중심 이동

### 🚢 AIS 선박 정보
- 주변 선박의 실시간 위치
- 선박명, 종류, 속도, 방향 정보
- 충돌 위험 경고 시스템

### 🎯 쓰레기 핫스팟 표시
- AI 기반 쓰레기 집중 구역 예측
- 우선순위 기반 색상 코딩 (고/중/저)
- 예상 쓰레기 양 및 종류 정보
- 클릭으로 상세 정보 확인

### 🌤️ 기상 정보
- 실시간 기온, 풍향, 풍속
- 파고 및 가시거리 정보
- 작업 안전성 평가

### 🛣️ 경로 최적화
- TSP 알고리즘 기반 최적 경로 계산
- 기상 조건 고려한 안전 경로
- 연료 효율 최적화
- 실시간 경로 재계산

### 📊 작업 현황 대시보드
- 오늘 수거량 통계
- 완료/미완료 지점 추적
- 작업 소요 시간 기록

### ⚠️ 알림 시스템
- 기상 주의보 알림
- 새로운 핫스팟 감지 알림
- 항해 위험 경고

## 🖥️ 시스템 요구사항

- 모던 웹 브라우저 (Chrome, Firefox, Safari, Edge)
- 인터넷 연결
- GPS 장치 (실제 선박 위치 추적 시)

## 🚀 시작하기

### 1. 파일 구조
```
marine_cleanup_nav/
├── index.html              # 메인 HTML 파일
├── styles.css              # 스타일시트
├── app.js                  # JavaScript 로직
├── API_INTEGRATION_GUIDE.md # API 연동 가이드
└── README.md               # 이 문서
```

### 2. 실행 방법

#### 방법 A: 로컬 서버 사용 (권장)
```bash
# Python이 설치되어 있는 경우
cd C:\ClaudeFolder\marine_cleanup_nav
python -m http.server 8000

# 또는 Node.js를 사용하는 경우
npx http-server -p 8000
```

그 다음 브라우저에서 `http://localhost:8000` 접속

#### 방법 B: 직접 HTML 파일 열기
`index.html` 파일을 더블클릭하여 브라우저에서 열기

### 3. 초기 설정

현재는 모의 데이터로 작동합니다. 실제 데이터 연동을 위해서는 `API_INTEGRATION_GUIDE.md`를 참조하세요.

## 📖 사용 방법

### 기본 조작

#### 지도 조작
- **확대/축소**: 마우스 휠 또는 +/- 버튼
- **이동**: 드래그
- **현재 위치로**: 📍 버튼 클릭

#### 레이어 토글
1. 🗂️ 버튼 클릭
2. 원하는 레이어 체크/체크 해제
   - AIS 선박 위치
   - 쓰레기 핫스팟
   - 풍향/풍속
   - 해류
   - 파고

#### 경로 최적화
1. 🛣️ 버튼 클릭 또는
2. 우측 사이드바의 "경로 최적화" 버튼 클릭
3. 자동으로 최적 경로 계산 및 표시

#### 핫스팟 확인
- 좌측 사이드바의 핫스팟 목록에서 항목 클릭
- 지도가 해당 위치로 이동하며 상세 정보 표시

#### 주변 선박 확인
- 우측 사이드바의 AIS 목록에서 선박 클릭
- 해당 선박 위치로 지도 이동

## 🎨 화면 구성

### 헤더
- 선박명 및 운항 상태
- 현재 시각
- 긴급 버튼

### 좌측 사이드바
- 현재 위치 정보 (위도/경도/속도/방향)
- 기상 정보
- 쓰레기 핫스팟 목록

### 중앙 지도
- 인터랙티브 해상 지도
- 선박 마커 (파란색 점)
- 핫스팟 마커 (색상별 우선순위)
- AIS 선박 마커 (하늘색 점)
- 경로 라인 (파선)

### 우측 사이드바
- 경로 정보 (거리/시간/핫스팟 수)
- 수거 현황 통계
- AIS 선박 목록
- 알림/경고

## 🔧 커스터마이징

### 색상 테마 변경
`styles.css` 파일에서 색상 변수 수정:

```css
/* 헤더 배경 */
.nav-header {
    background: linear-gradient(135deg, #YOUR_COLOR1 0%, #YOUR_COLOR2 100%);
}

/* 패널 배경 */
.info-panel {
    background: linear-gradient(135deg, #YOUR_COLOR1 0%, #YOUR_COLOR2 100%);
}
```

### 초기 위치 변경
`app.js` 파일에서 `currentPosition` 수정:

```javascript
let currentPosition = [위도, 경도]; // 예: [35.1796, 129.0756]
```

### 데이터 업데이트 주기 변경
`app.js` 파일 하단:

```javascript
// 기본값: 5분 (300000ms)
setInterval(updateAllData, 300000);

// 1분으로 변경하려면:
setInterval(updateAllData, 60000);
```

## 🔌 API 연동

실제 데이터 소스 연동을 위해서는 `API_INTEGRATION_GUIDE.md`를 참조하세요.

연동이 필요한 데이터:
1. **AIS 데이터**: MarineTraffic, AISHub 등
2. **쓰레기 핫스팟**: 자체 AI 모델 또는 위성 이미지 분석
3. **기상 정보**: 기상청 API, OpenWeatherMap 등
4. **해류 데이터**: HYCOM, Copernicus Marine Service
5. **파도 정보**: NOAA WaveWatch III

## 🐛 문제 해결

### 지도가 표시되지 않는 경우
- 인터넷 연결 확인
- 브라우저 콘솔에서 에러 메시지 확인
- Leaflet 라이브러리 로드 확인

### 데이터가 업데이트되지 않는 경우
- API 연동 상태 확인
- 브라우저 콘솔에서 네트워크 요청 확인
- CORS 정책 확인

### 성능이 느린 경우
- 마커 수 줄이기 (마커 클러스터링 적용)
- 데이터 업데이트 주기 늘리기
- 불필요한 레이어 비활성화

## 📱 모바일 지원

현재 버전은 데스크톱에 최적화되어 있습니다. 
모바일 버전은 향후 업데이트 예정입니다.

## 🤝 기여 방법

1. 이 저장소를 Fork
2. 기능 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 연락처

프로젝트 관련 문의사항이나 제안사항이 있으시면 Issue를 등록해주세요.

## 🙏 감사의 말

- [Leaflet](https://leafletjs.com/) - 오픈소스 지도 라이브러리
- [OpenStreetMap](https://www.openstreetmap.org/) - 지도 타일 제공
- 해양 환경 보호에 힘쓰시는 모든 분들께 감사드립니다

## 🔮 향후 계획

### v1.1 (단기)
- [ ] GPS 실시간 위치 연동
- [ ] AIS 데이터 API 연동
- [ ] 기상청 API 연동
- [ ] 데이터 저장 기능

### v1.2 (중기)
- [ ] AI 기반 쓰레기 예측 모델 통합
- [ ] 실시간 해류 시각화
- [ ] 경로 최적화 알고리즘 고도화
- [ ] 다국어 지원

### v2.0 (장기)
- [ ] 모바일 앱 버전 (iOS/Android)
- [ ] 오프라인 모드 지원
- [ ] 팀 협업 기능
- [ ] 상세 수거 이력 보고서
- [ ] 드론 연동 기능

## 📚 추가 자료

- [사용자 매뉴얼](./docs/USER_MANUAL.md) (작성 예정)
- [개발자 가이드](./docs/DEVELOPER_GUIDE.md) (작성 예정)
- [API 문서](./API_INTEGRATION_GUIDE.md)

## 🌟 스타를 눌러주세요!

이 프로젝트가 도움이 되셨다면 ⭐️ 를 눌러주세요!

---

**Made with 💙 for Ocean Conservation**