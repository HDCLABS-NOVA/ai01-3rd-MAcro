# 🎯 티켓 오픈 시뮬레이션 가이드

## 📋 개요

이 기능은 **티켓 오픈 순간의 사용자 반응 시간을 측정**하여 **자동 호출 매크로**를 탐지하는 핵심 기능입니다.

---

## 🔍 **정상 vs 매크로 차이**

### **정상 사용자** 👤
```
오픈 전: 페이지에서 대기, F5 새로고침
    ↓
오픈: 버튼 활성화!
    ↓ (200-800ms 후 - 인간 반응 시간)
클릭!
```

**특징**:
- 반응 시간: **200-800ms** (평균 400ms)
- 마우스 이동: 자연스러운 궤적
- 떨림: 있음

### **자동 호출 매크로** 🤖
```
오픈 전: 자동 새로고침 대기
    ↓
오픈: 버튼 활성화!
    ↓ (5-50ms 후 - 비인간적!)
클릭! ← 탐지!
```

**특징**:
- 반응 시간: **5-50ms** (인간 불가능)
- 마우스 이동: 직선 또는 없음
- 떨림: 없음

---

## 🛠️ **현재 구현된 기능**

### **1. 반응 시간 측정** ⏱️

**로그 데이터 구조**:
```javascript
{
  "stages": {
    "perf": {
      "button_click_timing": {
        "page_load_time": 1738571234000,
        "button_enabled_time": 1738571240000,  // 버튼 활성화 시간
        "click_time": 1738571240350,            // 클릭 시간
        "reaction_time_from_enable_ms": 350,    // ⭐ 가장 중요!
        "reaction_time_from_load_ms": 6350,
        "has_open_time_simulation": true
      }
    }
  }
}
```

**판단 기준**:
```python
# ML 모델 Feature
if reaction_time_from_enable_ms is not None:
    if reaction_time < 100:
        # 매크로 의심도: 매우 높음
        macro_score += 0.9
    elif reaction_time < 200:
        # 매크로 의심도: 높음
        macro_score += 0.7
    elif reaction_time > 800:
        # 봇이 아님 (사람도 느릴 수 있음)
        macro_score += 0.0
    else:
        # 정상 범위 (200-800ms)
        macro_score += -0.2  # 정상 점수
```

---

## 🚀 **사용 방법**

### **방법 1: URL 파라미터 (권장)** 📍

Chrome Extension에서 자동으로 URL에 `openTime` 파라미터 추가:

```
일반 접속:
http://localhost:8000/html/performance_detail.html?id=perf001

오픈 시뮬레이션:
http://localhost:8000/html/performance_detail.html?id=perf001&openTime=10
                                                                     ↑
                                                             10초 후 버튼 활성화
```

**Extension이 자동으로 처리**:
```javascript
// Extension에서 URL 생성 시
const openDelay = 10; // 10초 후 오픈
const url = `/html/performance_detail.html?id=${perfId}&openTime=${openDelay}`;
chrome.tabs.update({ url });
```

### **방법 2: 수동 테스트** 🧪

브라우저에서 직접 접속:

```
# 5초 후 오픈
http://localhost:8000/html/performance_detail.html?id=perf001&openTime=5

# 30초 후 오픈
http://localhost:8000/html/performance_detail.html?id=perf001&openTime=30
```

---

## 📊 **로그 수집 시나리오**

### **시나리오 1: 정상 사용자 (다양한 반응 시간)** 👤

```javascript
// Extension 설정
{
  "Number of Seats": "Random",
  "Auto-Loop": 100,
  "openTime": 5  // 5초 후 버튼 활성화
}

// 결과 로그
reaction_time_from_enable_ms: [
  250, 380, 520, 410, 290, 650, 330, ...
  // 평균: 400ms, 분산: 크다
]
```

### **시나리오 2: 자동 호출 매크로 (빠른 반응)** 🤖

```javascript
// Extension 설정 (매크로 시뮬레이션)
{
  "Number of Seats": "Random",
  "Auto-Loop": 100,
  "openTime": 5,
  "macroMode": true  // ← 매크로 모드 활성화
}

// 결과 로그
reaction_time_from_enable_ms: [
  15, 22, 18, 25, 20, 17, 23, ...
  // 평균: 20ms, 분산: 작다 ← 명확한 패턴!
]
```

### **시나리오 3: 즉시 오픈 (현재 방식)** ⚡

```javascript
// URL에 openTime 없음
http://localhost:8000/html/performance_detail.html?id=perf001

// 결과 로그
button_click_timing: {
  button_enabled_time: null,
  reaction_time_from_enable_ms: null,  // 측정 불가
  has_open_time_simulation: false
}
```

---

## 🎯 **Extension 자동화 설정**

### **Chrome Extension에 오픈 시뮬레이션 추가**

**popup.js 수정**:
```javascript
// Extension 설정에 openTime 추가
const settings = {
  seatCount: document.getElementById('seat-count').value,
  autoLoop: document.getElementById('auto-loop').value,
  openTimeDelay: document.getElementById('open-time-delay').value  // ← 새 설정
};

// URL 생성시 포함
if (settings.openTimeDelay > 0) {
  url += `&openTime=${settings.openTimeDelay}`;
}
```

**popup.html에 UI 추가**:
```html
<div class="form-group">
  <label>Open Time Delay (seconds)</label>
  <input type="number" id="open-time-delay" value="10" min="0" max="300">
  <small>Time until button becomes enabled (0 = immediate)</small>
</div>
```

---

## 📈 **ML 모델 Feature**

### **핵심 Feature: Reaction Time**

```python
# Feature Engineering
features = {
    # 반응 시간 (가장 중요!)
    'reaction_time_ms': log['stages']['perf']['button_click_timing']['reaction_time_from_enable_ms'],
    
    # 반응 시간 카테고리
    'is_superhuman': reaction_time < 100,  # 비인간적
    'is_fast': 100 <= reaction_time < 200,  # 빠름
    'is_normal': 200 <= reaction_time < 800,  # 정상
    'is_slow': reaction_time >= 800,  # 느림
    
    # 통계적 Feature
    'reaction_time_log': np.log(reaction_time + 1),
    'reaction_time_squared': reaction_time ** 2,
    
    # 조합 Feature
    'reaction_speed_ratio': reaction_time / total_duration,
}
```

### **탐지 규칙**

```python
# Rule-based Detection
def detect_macro_by_reaction_time(reaction_time):
    if reaction_time is None:
        return 0.0  # 측정 불가
    
    if reaction_time < 50:
        return 0.95  # 매크로 확률 95%
    elif reaction_time < 100:
        return 0.80  # 매크로 확률 80%
    elif reaction_time < 150:
        return 0.50  # 매크로 확률 50%
    elif reaction_time < 200:
        return 0.20  # 매크로 확률 20%
    else:
        return 0.0   # 정상
```

---

## 🔧 **현재 상태 및 TODO**

### ✅ **완료된 기능**
- [x] 페이지 로드 시간 측정
- [x] 버튼 클릭 시간 측정
- [x] 반응 시간 계산 및 로그 기록
- [x] 로그 데이터 구조 정의

### 🚧 **TODO (선택사항)**
- [ ] Extension에서 `openTime` 파라미터 자동 설정
- [ ] Extension UI에 오픈 시간 설정 추가
- [ ] 버튼 자동 활성화 로직 (`performance_detail.html`)
- [ ] 시각적 카운트다운 표시

---

## 💡 **핵심 요약**

### **왜 중요한가?**
티켓 오픈 순간의 **반응 시간**은 **자동 호출 매크로를 탐지하는 가장 강력한 지표**입니다.

### **정상 vs 매크로**
- **정상**: 200-800ms (평균 400ms)
- **매크로**: 5-50ms (인간 불가능!)

### **현재 로그에 기록됨**
```javascript
reaction_time_from_enable_ms: 350  // ← 이 값으로 매크로 탐지!
```

### **사용 방법**
1. Extension에서 Auto-Loop 활성화
2. `openTime` 파라미터 설정 (예: 10초)
3. 정상/매크로 모드로 각각 100개씩 로그 수집
4. ML 모델 학습

**이제 티켓 오픈 순간의 매크로 행동을 정확히 탐지할 수 있습니다!** 🎯✨
