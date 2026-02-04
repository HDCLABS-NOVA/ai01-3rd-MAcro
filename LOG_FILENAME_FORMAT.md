# 로그 파일명 형식 가이드

## 📁 파일명 형식

```
[날짜]_[공연ID]_[flow_id]_[결제성공여부].json
```

### 예시
```
20260204_perf001_flow_20260204_abc123_success.json
20260204_perf001_flow_20260204_def456_abandoned.json
20260204_perf002_flow_20260204_ghi789_failed.json
```

---

## 🔑 파일명 구성 요소

### 1. **날짜** (YYYYMMDD)
- 형식: `20260204`
- 설명: 로그 저장 시점의 날짜

### 2. **공연ID** (performance_id)
- 형식: `perf001`, `perf002`, 등
- 설명: 예매 대상 공연의 고유 ID
- 기본값: `UNKNOWN` (공연 ID를 찾을 수 없는 경우)

### 3. **flow_id**
- 형식: `flow_20260204_abc123`
- 설명: 하나의 예매 시도를 나타내는 고유 ID
- 생성 규칙: `flow_[날짜]_[랜덤ID]`
- 기본값: `flow_[현재시간]` (flow_id가 없는 경우 자동 생성)

### 4. **결제성공여부** (completion_status)
- 가능한 값:
  - `success`: 예매 완료 및 결제 성공
  - `abandoned`: 사용자가 중간에 포기
  - `failed`: 예매 실패 (오류, 시간 초과 등)
  - `unknown`: 상태를 알 수 없음

---

## 🔄 로그 저장 프로세스

### 1. 클라이언트에서 로그 전송
```javascript
// finalizeLog 호출 시
await finalizeLog(isSuccess, bookingId);

// 서버로 전송
POST /api/logs
{
  "metadata": {
    "flow_id": "flow_20260204_abc123",
    "performance_id": "perf001",
    "is_completed": true,
    "completion_status": "success"
  },
  "stages": { ... }
}
```

### 2. 서버에서 파일명 생성
```python
# main.py의 save_log 함수
date_str = datetime.now().strftime('%Y%m%d')  # 20260204
performance_id = metadata.get("performance_id", "UNKNOWN")  # perf001
flow_id = metadata.get("flow_id", "flow_...")  # flow_20260204_abc123

# completion_status 결정
if is_completed and completion_status == "success":
    payment_status = "success"
elif completion_status == "abandoned":
    payment_status = "abandoned"
else:
    payment_status = "failed"

# 파일명 생성
filename = f"{date_str}_{performance_id}_{flow_id}_{payment_status}.json"
# 예: 20260204_perf001_flow_20260204_abc123_success.json
```

---

## 📊 ML 모델 학습을 위한 라벨링

### 방법 1: 파일명에 명시적 라벨 추가 (권장)

정상 사용자 로그를 수집한 후:
```bash
# 원본
20260204_perf001_flow_20260204_abc123_success.json

# 변경 (파일명 어딘가에 'normal' 키워드 추가)
20260204_perf001_flow_20260204_abc123_normal_success.json
또는
20260204_perf001_flow_20260204_abc123_success_normal.json
```

매크로 로그를 수집한 후:
```bash
# 원본
20260204_perf001_flow_20260204_def456_success.json

# 변경 (파일명 어딘가에 'macro' 키워드 추가)
20260204_perf001_flow_20260204_def456_macro_success.json
```

### 방법 2: 폴더로 분류

```
logs/
├── normal/
│   ├── 20260204_perf001_flow_20260204_abc123_success.json
│   ├── 20260204_perf001_flow_20260204_def456_success.json
│   └── ...
└── macro/
    ├── 20260204_perf001_flow_20260204_ghi789_success.json
    ├── 20260204_perf001_flow_20260204_jkl012_success.json
    └── ...
```

---

## 🤖 ML 학습 시 데이터 로드

### data_loader.py 사용

```python
from data_loader import load_logs

# 방법 1: 파일명으로 라벨 구분 (normal/macro 키워드)
logs = load_logs('../logs', label_by_filename=True)

# 방법 2: 폴더로 라벨 구분 (logs/normal/, logs/macro/)
logs = load_logs('../logs', label_by_filename=False)
```

### 라벨링 규칙

```python
# data_loader.py의 내부 로직:

if 'normal' in filename:
    log['label'] = 0  # 정상 사용자
elif 'macro' in filename:
    log['label'] = 1  # 매크로
else:
    log['label'] = 0  # 기본값: 정상 (경고 메시지 출력)
```

---

## ✅ 체크리스트

### 로그 수집 시
```
□ 서버 실행 (python main.py)
□ 예매 진행 (정상 또는 매크로)
□ 자동으로 로그 파일 저장됨
   → logs/ 폴더 확인
   → 파일명 형식: [날짜]_[공연ID]_[flow_id]_[상태].json
```

### ML 학습 시
```
□ 정상 로그 파일명에 'normal' 키워드 추가
   예: 20260204_perf001_flow_20260204_abc123_normal_success.json

□ 매크로 로그 파일명에 'macro' 키워드 추가
   예: 20260204_perf001_flow_20260204_def456_macro_success.json

□ 또는 logs/normal/, logs/macro/ 폴더로 분류

□ train_model.py 실행
```

---

## 🔍 파일명 파싱 예제

### Python으로 파일명 분석
```python
import re
from pathlib import Path

def parse_log_filename(filename):
    """
    로그 파일명을 파싱하여 정보 추출
    
    형식: [날짜]_[공연ID]_[flow_id]_[상태].json
    """
    # 확장자 제거
    name = Path(filename).stem
    
    # '_'로 분리
    parts = name.split('_')
    
    # 최소 4개 파트가 있어야 함
    if len(parts) < 4:
        return None
    
    # 날짜 (첫 번째)
    date = parts[0]
    
    # 공연ID (두 번째)
    performance_id = parts[1]
    
    # flow_id (세 번째부터 끝에서 두 번째까지)
    # 예: flow_20260204_abc123 또는 flow_20260204_abc123_normal
    flow_parts = parts[2:-1]
    flow_id = '_'.join(flow_parts)
    
    # 상태 (마지막)
    status = parts[-1]
    
    # 라벨 판별
    filename_lower = filename.lower()
    if 'normal' in filename_lower:
        label = 'normal'
    elif 'macro' in filename_lower:
        label = 'macro'
    else:
        label = 'unknown'
    
    return {
        'date': date,
        'performance_id': performance_id,
        'flow_id': flow_id,
        'status': status,
        'label': label,
        'filename': filename
    }

# 사용 예시
filename = "20260204_perf001_flow_20260204_abc123_normal_success.json"
info = parse_log_filename(filename)
print(info)
# {
#     'date': '20260204',
#     'performance_id': 'perf001',
#     'flow_id': 'flow_20260204_abc123_normal',
#     'status': 'success',
#     'label': 'normal',
#     'filename': '20260204_perf001_flow_20260204_abc123_normal_success.json'
# }
```

---

## 📚 관련 파일

- **`main.py`** (163-207번 라인): 로그 저장 API
- **`ml/data_loader.py`**: 로그 파일 읽기 및 라벨링
- **`js/logger.js`**: 클라이언트 로그 수집
- **`js/flow-manager.js`**: flow_id 관리

---

## 💡 팁

### 1. 대량 파일명 변경 (Windows PowerShell)
```powershell
# logs 폴더의 모든 success 파일에 'normal' 추가
cd logs
Get-ChildItem -Filter "*_success.json" | ForEach-Object {
    $newName = $_.Name -replace "_success.json", "_normal_success.json"
    Rename-Item $_.FullName $newName
}
```

### 2. 정상/매크로 로그 분리
```bash
# 정상 로그만 복사
mkdir logs/normal
copy logs/*normal*.json logs/normal/

# 매크로 로그만 복사
mkdir logs/macro
copy logs/*macro*.json logs/macro/
```

### 3. 로그 파일 통계
```python
from pathlib import Path

logs_dir = Path('logs')
log_files = list(logs_dir.glob('*.json'))

# 상태별 카운트
status_count = {}
for file in log_files:
    parts = file.stem.split('_')
    status = parts[-1] if len(parts) >= 4 else 'unknown'
    status_count[status] = status_count.get(status, 0) + 1

print(f"총 로그: {len(log_files)}개")
print(f"상태별 분포: {status_count}")
```

---

**Happy Logging! 📊✨**
