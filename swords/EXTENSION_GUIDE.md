# 🗡️ SWORD - Ticket Automation Extension

## 📊 UI 구성 요소 설명

### 1. **🚀 즉시 실행** 버튼
- Target Time 무시하고 **즉시 자동화 시작**
- 테스트나 빠른 실행에 사용

---

### 2. **⏰ Target Time** (예약 실행)

```
시간 입력: HH:MM:SS
예시: 20:00:00 (오후 8시)
```

**사용 시나리오:**
- 티켓 오픈 시간에 정확히 시작
- 설정한 시간까지 대기 상태
- 카운트다운 표시

**작동 방식:**
```
현재: 19:59:50
Target: 20:00:00
→ 10초 카운트다운
→ 20:00:00 정각에 자동 시작!
```

---

### 3. **🎫 Number of Seats** (좌석 수)

#### **고정 모드** (Random 체크 해제)
```
값: 1~10
→ 항상 지정한 개수만큼 좌석 선택
```

#### **랜덤 모드** (Random 체크 ✅)
```
범위: 1~4석 랜덤
→ 매 시도마다 다른 개수 선택
```

**랜덤 모드 장점:**
- 로그 데이터 다양성 확보
- 1석, 2석, 3석, 4석 케이스 자동 테스트
- 실제 사용자 패턴과 유사

**작동 예시:**
```
시도 1: 3석 선택 → 로그 저장
시도 2: 1석 선택 → 로그 저장
시도 3: 4석 선택 → 로그 저장
시도 4: 2석 선택 → 로그 저장
...
```

---

### 4. **🔄 Auto-Loop Count** (자동 반복 횟수)

```
값: 1 ~ 10000
```

**용도:**
- **1**: 단일 실행 (기본)
- **10**: 10번 반복
- **1000+**: 대량 로그 수집

**작동 방식:**
```
Auto-Loop: 10

시도 1 → 완료 → 로그 저장
       ↓
    3초 대기
       ↓
시도 2 → 완료 → 로그 저장
       ↓
    3초 대기
       ↓
...
       ↓
시도 10 → 완료 → 로그 저장
        ↓
      종료!
```

---

### 5. **🔄 Auto-refresh** (자동 새로고침)

```
체크 ✅: Target Time에 도달하면 페이지 새로고침
체크 ❌: 새로고침 없이 바로 시작
```

**용도:**
- 캐시 제거
- 최신 상태로 시작
- 메모리 정리

---

### 6. **🐛 Debug Mode** (디버그 오버레이)

```
체크 ✅: 화면 우측 상단에 FSM 상태 표시
체크 ❌: 오버레이 숨김
```

**표시 내용:**
```
┌─────────────────┐
│ SWORD DEBUG     │
│ State: CAPTCHA  │
│ Attempt: 3/10   │
│ Time: 00:02:15  │
└─────────────────┘
```

---

## 🎯 사용 시나리오

### **시나리오 1: 1000개 로그 자동 수집 (랜덤 좌석)**

```
Settings:
✅ Random Seats
🔢 Auto-Loop Count: 1000
❌ Auto-refresh: OFF (반복 실행이므로)
❌ Debug Mode: OFF (성능 최적화)

실행:
🚀 즉시 실행 클릭
```

**결과:**
```
logs/20260131_IU001_abc123_success.json  (3석)
logs/20260131_IU001_def456_success.json  (1석)
logs/20260131_IU001_ghi789_failed.json   (4석)
logs/20260131_IU001_jkl012_success.json  (2석)
...
```

---

### **시나리오 2: 티켓 오픈 시간 정확히 시작**

```
Settings:
⏰ Target Time: 20:00:00
🎫 Seats: 2 (고정)
🔢 Auto-Loop: 1
✅ Auto-refresh: ON
❌ Debug Mode: OFF

실행:
▶ START 클릭
```

**진행:**
```
19:59:50 → 카운트다운 시작
19:59:55 → "5초 후 시작..."
20:00:00 → 페이지 새로고침 → 자동 시작!
```

---

### **시나리오 3: 테스트/디버깅**

```
Settings:
🎫 Seats: 1
🔢 Auto-Loop: 1
❌ Auto-refresh: OFF
✅ Debug Mode: ON

실행:
🚀 즉시 실행
```

**결과:**
- 화면에 FSM 상태 실시간 표시
- 어떤 단계에서 멈췄는지 확인 가능

---

## 🔄 Auto-Loop 작동 원리

```javascript
for (attempt = 1; attempt <= Auto-Loop Count; attempt++) {
  // 1. 새로운 FlowID 생성
  flowId = generateID();
  
  // 2. 예매 시도
  - CAPTCHA 해결
  - 좌석 선택 (Random이면 1-4 중 랜덤)
  - 결제 진행
  
  // 3. 로그 저장
  filename = `${date}_${performanceId}_${flowId}_${result}.json`;
  save(filename);
  
  // 4. 다음 시도 준비
  sleep(3000);  // 3초 대기
  resetState();
}
```

---

## 📊 로그 데이터 구조

```json
{
  "metadata": {
    "flowId": "flow_1769846000_abc123",
    "performanceId": "IU001",
    "performanceName": "아이유 콘서트 <The Golden Hour>",
    "attemptNumber": 5,
    "totalAttempts": 1000,
    "status": "success",
    "seatCount": 3,        // 랜덤 모드면 1-4 중 랜덤
    "randomSeats": true,
    "duration": 45320,
    "completedAt": "2026-01-31T17:20:00.000Z"
  },
  "stages": {
    "IDLE": {...},
    "CLICK_START": {...},
    "HANDLE_CAPTCHA": {...},
    "SELECT_SEAT": {...},
    "PAYMENT": {...}
  }
}
```

---

## 🎲 Random Seats 통계

1000번 실행 시 예상 분포:

```
1석: ~250회 (25%)
2석: ~250회 (25%)  
3석: ~250회 (25%)
4석: ~250회 (25%)
```

→ 다양한 케이스의 로그 데이터 확보!

---

## ⚡ 빠른 시작

### **10개 로그 랜덤 수집:**

1. Extension 팝업 열기
2. ✅ Random Seats 체크
3. Auto-Loop Count: `10`
4. 🚀 즉시 실행 클릭
5. 완료! → `logs/` 폴더 확인

---

## 🛠️ 주의사항

1. **CAPTCHA API 서버 필수**
   - `captcha_api_server.py` 실행 중이어야 함
   - 안그러면 CAPTCHA에서 수동 대기

2. **메인 API 서버 필수**
   - `main.py` 실행 중이어야 로그 저장됨
   - 포트 8000 확인

3. **LM Studio 실행**
   - Vision 모델 로드
   - Local Server 시작 (포트 12345)

---

## 📌 요약

| 기능 | 용도 | 추천 값 |
|------|------|---------|
| Target Time | 티켓 오픈 시간 대기 | 20:00:00 |
| Seats (고정) | 특정 개수 선택 | 1 ~ 10 |
| Seats (랜덤) | 다양한 케이스 테스트 | ✅ Random |
| Auto-Loop | 로그 자동 수집 | 10 ~ 1000 |
| Auto-refresh | 캐시 제거 | ✅ ON |
| Debug Mode | 문제 해결 | 필요시만 ON |
