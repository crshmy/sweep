# 🔑 API 키 설정 가이드

## 1. OpenWeatherMap API 키 발급

### 단계별 가이드

1. **회원가입**
   - https://openweathermap.org/ 접속
   - 우측 상단 "Sign In" 클릭
   - "Create an Account" 선택
   - 이메일, 비밀번호 입력 후 가입

2. **API 키 발급**
   - 로그인 후 상단 메뉴에서 "API keys" 클릭
   - 또는 직접 이동: https://home.openweathermap.org/api_keys
   - Default API key가 자동 생성되어 있음
   - 또는 "Generate" 버튼으로 새 키 생성

3. **API 키 복사**
   ```
   예시: 1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p
   ```

### 무료 플랜 제한사항
- ✅ 1,000 calls/day (충분함)
- ✅ 현재 날씨 데이터
- ✅ 5일 / 3시간 예보
- ✅ 풍향/풍속 데이터
- ❌ 과거 데이터 (유료)
- ❌ 1시간 예보 (유료)

---

## 2. 프로젝트에 API 키 적용

### 방법 1: 직접 코드 수정 (간단, 테스트용)

**파일**: `js/weather-layer.js`

```javascript
// 11번째 줄 찾기
this.OWM_API_KEY = 'YOUR_API_KEY'; 

// 발급받은 키로 교체
this.OWM_API_KEY = '1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p';
```

### 방법 2: 환경변수 사용 (권장, 보안)

**파일**: `js/config.js`

```javascript
// API 설정 부분 수정
api: {
    weather: {
        enabled: true,
        endpoint: 'https://api.openweathermap.org/data/2.5',
        apiKey: process.env.OWM_API_KEY || 'YOUR_API_KEY_HERE'
    }
}
```

**.env 파일 생성** (프로젝트 루트)
```bash
OWM_API_KEY=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p
```

---

## 3. API 키 테스트

### 브라우저 콘솔에서 테스트

```javascript
// 1. API 키 확인
console.log('API Key:', weatherLayer.OWM_API_KEY);

// 2. 테스트 요청
fetch('https://api.openweathermap.org/data/2.5/weather?lat=35.18&lon=129.08&appid=YOUR_KEY')
    .then(res => res.json())
    .then(data => console.log('성공:', data))
    .catch(err => console.error('실패:', err));
```

### 성공 응답 예시
```json
{
  "weather": [{"main": "Clear"}],
  "main": {"temp": 288.15},
  "wind": {
    "speed": 5.5,
    "deg": 120
  }
}
```

### 오류 응답
```json
// 401 Unauthorized
{
  "cod": 401,
  "message": "Invalid API key"
}
```

---

## 4. 문제 해결

### ❌ 401 Unauthorized
**원인**: API 키가 잘못됨

**해결**:
1. API 키 다시 복사 (공백 없이)
2. 키 활성화 대기 (최대 2시간)
3. 새 키 재발급

### ❌ 429 Too Many Requests
**원인**: 일일 호출 한도 초과 (1000회)

**해결**:
1. 캐싱 활성화 확인
2. 업데이트 주기 늘리기 (config.js)
```javascript
updateIntervals: {
    weather: 600000,  // 10분 → 30분으로 변경
}
```

### ❌ CORS 오류
**원인**: 로컬 파일로 열면 CORS 차단

**해결**:
```bash
# 로컬 서버 실행 필수
python -m http.server 8000
```

### ⚠️ 데이터가 안 나옴
**원인**: API 키 미설정 → 더미 데이터 사용 중

**확인**:
```javascript
// 콘솔 확인
> 🌐 기상 데이터 수집 중...
> ✅ 20개 지점 데이터 수집 완료

// 더미 데이터 사용 중이면:
> ❌ API 오류: 401
> 🎲 더미 데이터 사용
```

---

## 5. 보안 주의사항

### ⚠️ GitHub에 업로드 금지
```bash
# .gitignore에 추가
.env
**/config.js
```

### ✅ 키 노출 시 대처
1. OpenWeatherMap 사이트 접속
2. API Keys 페이지에서 해당 키 삭제
3. 새 키 재발급
4. 코드 업데이트

### 🔒 프로덕션 환경
- 백엔드에서 API 호출
- 프론트엔드는 자체 서버에만 요청
- API 키 직접 노출 금지

---

## 6. 대체 API (참고)

### Windy API (고급 시각화)
```javascript
// 무료 플랜: 20,000 calls/month
// 장점: 격자 데이터, 애니메이션 지원
// https://api.windy.com/
```

### 기상청 API (한국 특화)
```javascript
// 복구 대기중...
// 장점: 국내 해역 상세 데이터
// https://www.data.go.kr/
```

### Marine Weather API
```javascript
// 유료: 해양 전문 데이터
// 파고, 조류, 수온 등
// https://www.weatherapi.com/
```

---

## 7. 빠른 시작 체크리스트

- [ ] OpenWeatherMap 계정 생성
- [ ] API 키 발급 및 복사
- [ ] `js/weather-layer.js` 파일 수정
- [ ] 로컬 서버 실행
- [ ] 브라우저에서 `http://localhost:8000` 접속
- [ ] 🌬️ 버튼 클릭하여 기상 레이어 활성화
- [ ] 바람 화살표 확인
- [ ] 콘솔에 오류 없는지 확인

---

## 8. 유용한 링크

- OpenWeatherMap API Docs: https://openweathermap.org/api
- Leaflet Docs: https://leafletjs.com/reference.html
- 프로젝트 GitHub: [your-repo-url]

---

**문제가 계속되면?**
1. 콘솔 오류 메시지 복사
2. API 키 마스킹 (앞 4자리만)
3. Issue 등록 또는 이메일 문의
