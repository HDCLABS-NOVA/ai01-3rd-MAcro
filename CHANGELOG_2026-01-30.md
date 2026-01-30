# 변경 로그 - 2026년 1월 30일

## 📊 통합 로그 뷰어 개발

### 1️⃣ 통합 뷰어 생성
**파일**: `viewer.html`

#### 주요 변경사항
- `viewer_performance.html`과 `viewer_booking.html`을 하나로 통합
- 탭 전환 방식으로 UI 개선
  - **🎭 공연창 탭**: 공연 선택 단계 (performance 페이지 → 대기열 입장 직전)
  - **🎫 예매창 탭**: 좌석 선택 → 결제 완료 (seat, discount, order_info, payment)

#### 기능
- 각 탭별 통계 표시
  - 공연창: 총 로그 수, 평균 소요시간, 평균 마우스 이동
  - 예매창: 총 로그 수, 평균 소요시간, 완료율
- 로그 목록 표시 및 클릭으로 상세 분석
- 예매창은 단계별 버튼으로 전환 가능

---

### 2️⃣ 캔버스 크기 조정
**변경 전**: 1400x900
**변경 후**: 1920x1080 (실제 브라우저 해상도)

#### 상세 변경
```html
<!-- 메인 캔버스 -->
<canvas id="perf-canvas" class="main-canvas" width="1920" height="1080"></canvas>
<canvas id="book-canvas" class="main-canvas" width="1920" height="1080"></canvas>

<!-- 떨림 분석 캔버스 -->
<canvas id="perf-tremor-canvas" width="800" height="800"></canvas>
<canvas id="book-tremor-canvas" width="800" height="800"></canvas>
```

#### CSS 추가
```css
.main-canvas {
    width: 100%;
    cursor: crosshair;
}

canvas {
    max-width: 100%;
    height: auto;
}
```

**효과**: 
- 실제 마우스 경로가 정확한 비율로 표시
- 반응형으로 다양한 화면 크기에 대응

---

### 3️⃣ 클릭 포인트 호버 툴팁 기능

#### 추가된 요소
```html
<div id="perf-tooltip" class="canvas-tooltip"></div>
<div id="book-tooltip" class="canvas-tooltip"></div>
```

#### CSS 스타일
```css
.canvas-tooltip {
    position: absolute;
    background: rgba(0, 0, 0, 0.9);
    color: white;
    padding: 12px;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.6;
    pointer-events: none;
    z-index: 1000;
    white-space: nowrap;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    display: none;
}

.canvas-tooltip strong {
    color: #FF3D7F;
}
```

#### 마우스 이벤트 핸들러
```javascript
canvas.onmousemove = function(e) {
    // 클릭 포인트, 시작점, 끝점 감지
    // 감지 반경: 클릭 15px, 시작/끝 10px
    // 툴팁 표시
};
```

#### 툴팁 표시 정보

**🖱️ 클릭 포인트 (핑크색)**
- 클릭 번호 (클릭 #1, #2, ...)
- 단계 (공연 선택, 좌석 선택, 할인, 배송 정보, 결제)
- 좌표 (x, y)
- 시간 (밀리초까지 정확한 한국 시간)
- 클릭 지속시간 (ms)
- 클릭한 요소 ID

**🟢 시작점 (초록색)**
- 단계
- 좌표
- 시작 시간

**🔴 끝점 (빨간색)**
- 단계
- 좌표
- 종료 시간

---

### 4️⃣ 시간 표시 수정

#### 문제
- 로그 데이터의 timestamp가 상대 시간(밀리초)과 절대 시간(ISO 8601)이 섞여 있음
- 브라우저 로컬 시간과 맞지 않음

#### 데이터 구조
```json
{
  "stages": {
    "perf": {
      "entry_time": "2026-01-30T07:03:07.452Z",  // UTC 절대 시간
      "mouse_trajectory": [
        [x, y, 7],      // 상대 시간 (밀리초)
        [x, y, 111],
        [x, y, 213]
      ]
    }
  }
}
```

#### 해결 방법
```javascript
// 시작/끝 점
const entryTime = new Date(stageData.entry_time);
const pointTime = new Date(entryTime.getTime() + point[2]);
const formattedTime = pointTime.toLocaleString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3
});

// 클릭 포인트
if (typeof click.timestamp === 'string' && click.timestamp.includes('T')) {
    // ISO 8601 형식
    clickTime = new Date(click.timestamp);
} else if (typeof click.timestamp === 'number') {
    // 상대 시간
    const entryTime = new Date(stageData.entry_time);
    clickTime = new Date(entryTime.getTime() + click.timestamp);
}
```

**결과**: UTC → KST 자동 변환 (+9시간), 밀리초까지 정확한 시간 표시

---

### 5️⃣ 호버 감지 개선

#### 변경 전
```javascript
if (speed < 100 && distance > 0) {
    currentHover.push(curr);
} else {
    if (currentHover.length > 5) {
        hovers.push([...currentHover]);
    }
}
```

#### 변경 후
```javascript
// 속도가 200px/s 미만이고 움직임이 있는 경우
if (speed < 200 && distance > 0) {
    currentHover.push(curr);
} else {
    if (currentHover.length >= 3) {  // 3개 이상이면 호버로 인정
        hovers.push([...currentHover]);
    }
}

// 마지막 호버 구간 처리
if (currentHover.length >= 3) {
    hovers.push([...currentHover]);
}

console.log(`${type} - 감지된 호버 구간: ${hovers.length}개`);
```

**조건 완화**:
- 속도 제한: 100px/s → 200px/s
- 최소 포인트: 6개 → 3개
- 마지막 구간도 처리

---

### 6️⃣ 호버 미감지 시 안내 메시지

#### 추가 기능
```javascript
if (hovers.length > 0) {
    // 호버 떨림 분석 표시
    analyzeHoverTremor(hovers[0], tremorCanvasId, tremorStatsId);
} else {
    // 안내 메시지 표시
    document.getElementById(tremorStatsId).innerHTML = `
        <div>
            <h4>⚠️ 호버 구간 미감지</h4>
            <p>마우스가 한 곳에 머물면서 느리게 움직이는 구간이 감지되지 않았습니다.</p>
            <small>호버 조건: 속도 < 200px/s, 연속 3개 이상의 포인트</small>
            <p>전체 마우스 포인트: ${trajectory.length}개</p>
            <p>평균 속도: ${calculateAverageSpeed(trajectory).toFixed(0)} px/s</p>
        </div>
    `;
}
```

#### 추가 헬퍼 함수
```javascript
function calculateAverageSpeed(trajectory) {
    // 전체 마우스 경로의 평균 속도 계산
    var totalSpeed = 0;
    var count = 0;
    
    for (var i = 1; i < trajectory.length; i++) {
        const distance = Math.sqrt(...);
        const timeDiff = (curr[2] - prev[2]) / 1000;
        if (timeDiff > 0) {
            totalSpeed += distance / timeDiff;
            count++;
        }
    }
    
    return count > 0 ? totalSpeed / count : 0;
}
```

---

## 📋 파일 목록

### 수정된 파일
- `viewer.html` - 통합 로그 뷰어 (전면 개편)

### 삭제 예정 파일 (더 이상 필요 없음)
- `viewer_performance.html` - 공연창 뷰어 (통합됨)
- `viewer_booking.html` - 예매창 뷰어 (통합됨)

---

## 🎯 사용 방법

### 1. 로그 뷰어 접속
```
http://127.0.0.1:8000/viewer.html
```

### 2. 탭 전환
- **공연창 탭**: 공연 선택 단계 분석
- **예매창 탭**: 좌석 선택 ~ 결제 단계 분석

### 3. 로그 분석
1. 로그 목록에서 원하는 로그 클릭
2. 마우스 경로 시각화 확인
3. 클릭/시작/끝 포인트에 마우스 올려 상세 정보 확인
4. 호버 구간 미세 떨림 분석 확인
5. 봇 탐지 점수 확인

### 4. 호버 구간 보는 법
- 마우스를 **천천히** 움직이세요 (< 200px/s)
- 선택 전에 **잠깐 머뭇거리세요**
- 빠르게만 움직이면 호버가 감지되지 않습니다

---

## 🔍 분석 지표

### 마우스 트래킹
- **파란색 선**: 전체 마우스 경로
- **주황색 강조**: 호버 구간 (속도 < 200px/s)
- **🟢 초록 점**: 시작점
- **🔴 빨간 점**: 끝점
- **🖱️ 핑크 원**: 클릭 위치

### 미세 떨림 분석 (호버 구간 10배 확대)
- **평균 떨림**: 호버 중 평균 이동 거리
- **최대 떨림**: 최대 이동 거리
- **표준편차**: 떨림의 일관성
  - **> 2px**: ✅ 자연스러운 떨림 (사람)
  - **< 2px**: ⚠️ 떨림 부족 (봇 의심)
- **포인트 수**: 호버 구간 마우스 샘플링 횟수

### 봇 탐지 분석
- **봇 점수**: 0~100 (높을수록 봇 의심)
  - **< 30**: ✅ 정상 사용자
  - **30~60**: ⚠️ 의심스러움
  - **> 60**: 🤖 봇 의심
- **속도 변동성**: 마우스 속도의 일관성
- **경로 곡선성**: 경로가 직선적인지 자연스러운지
- **호버 구간**: 느린 움직임 구간 수

**의심 요인**:
- 속도가 매우 일정함
- 경로가 거의 직선
- 비정상적으로 빠른 속도
- 클릭 좌표가 모두 정수값
- 호버 구간 없음

---

## 📝 참고사항

### 브라우저 콘솔 디버깅
```javascript
// 콘솔에 출력되는 정보
"perf - 감지된 호버 구간: 2개, 전체 포인트: 145개"
"book - 감지된 호버 구간: 0개, 전체 포인트: 67개"
```

### 로그 데이터 구조
```json
{
  "metadata": {
    "flow_id": "flow_20260130_xxx",
    "created_at": "2026-01-30T07:03:07.452Z",
    "performance_title": "...",
    "final_seats": ["..."],
    "is_completed": true
  },
  "stages": {
    "perf": {
      "entry_time": "2026-01-30T07:03:07.452Z",
      "exit_time": "2026-01-30T07:03:09.772Z",
      "duration_ms": 2320,
      "mouse_trajectory": [[x, y, relativeTime], ...],
      "clicks": [{x, y, timestamp, element_id, click_duration}, ...]
    }
  }
}
```

---

## ✅ 테스트 체크리스트

- [x] 공연창 탭에서 로그 표시
- [x] 예매창 탭에서 로그 표시
- [x] 단계별 버튼 전환
- [x] 클릭 포인트 호버 툴팁
- [x] 시작/끝 점 호버 툴팁
- [x] 정확한 한국 시간 표시
- [x] 호버 구간 감지 및 분석
- [x] 호버 미감지 시 안내 메시지
- [x] 봇 탐지 분석
- [x] 반응형 캔버스 크기

---

**작성일**: 2026년 1월 30일
**작성자**: AI Assistant
**버전**: 1.0.0
