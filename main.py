from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
from datetime import datetime, timedelta

app = FastAPI(title="Ticket Booking System")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# logs 디렉토리 생성
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# data 디렉토리 생성
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
RESTRICTED_FILE = os.path.join(DATA_DIR, "restricted_users.json")

# 사용자 파일이 없으면 초기화
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"users": []}, f, ensure_ascii=False, indent=2)

# 제한 사용자 파일이 없으면 초기화
if not os.path.exists(RESTRICTED_FILE):
    with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
        json.dump({"restricted_users": []}, f, ensure_ascii=False, indent=2)

# 기본 관리자 계정 생성
def init_admin_accounts():
    """서버 시작 시 기본 관리자 계정을 생성합니다."""
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 관리자 계정 정보
    admin_accounts = [
        {
            "email": "admin@ticket.com",
            "password": "admin1234",  # 실제 환경에서는 해시화 필요
            "name": "Administrator",
            "phone": "01000000000"
        },
        {
            "email": "manager@ticket.com",
            "password": "manager1234",
            "name": "Manager",
            "phone": "01000000001"
        }
    ]
    
    users_updated = False
    for admin in admin_accounts:
        # 이미 존재하는지 확인
        existing = any(user['email'] == admin['email'] for user in data['users'])
        if not existing:
            data['users'].append(admin)
            users_updated = True
            print(f"✅ 관리자 계정 생성: {admin['email']} (비밀번호: {admin['password']})")
    
    if users_updated:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# 관리자 계정 초기화 실행
init_admin_accounts()

# Pydantic 모델 정의
class SignupData(BaseModel):
    email: str
    password: str
    name: str
    phone: str

class LoginData(BaseModel):
    email: str
    password: str

class LogData(BaseModel):
    metadata: Dict[str, Any]
    stages: Dict[str, Any]

class RestrictUser(BaseModel):
    email: str
    level: int  # 1, 2, 3
    reason: str
    restricted_by: str = "admin@ticket.com"

class CancelBooking(BaseModel):
    filename: str
    reason: str = ""
    cancelled_by: str = "admin@ticket.com"

# API 엔드포인트

# 회원가입
@app.post("/api/auth/signup")
async def signup(signup_data: SignupData):
    """새 사용자를 등록합니다."""
    try:
        # 사용자 파일 읽기
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_db = json.load(f)
        
        # 이메일 중복 체크
        if any(user['email'] == signup_data.email for user in users_db['users']):
            raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
        
        # 새 사용자 추가
        new_user = {
            "email": signup_data.email,
            "password": signup_data.password,  # 실제로는 해시 처리 필요
            "name": signup_data.name,
            "phone": signup_data.phone,
            "created_at": datetime.now().isoformat()
        }
        users_db['users'].append(new_user)
        
        # 파일에 저장
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_db, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": "회원가입이 완료되었습니다.",
            "user": {
                "email": new_user['email'],
                "name": new_user['name']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 실패: {str(e)}")

# 로그인
@app.post("/api/auth/login")
async def login(login_data: LoginData):
    """사용자 로그인을 처리합니다."""
    try:
        # 사용자 파일 읽기
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_db = json.load(f)
        
        # 사용자 찾기
        user = next((u for u in users_db['users'] if u['email'] == login_data.email), None)
        
        if not user:
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
        
        if user['password'] != login_data.password:  # 실제로는 해시 비교 필요
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
        
        # 제한 상태 확인
        restriction = None
        try:
            with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
                restricted_db = json.load(f)
            restricted_user = next((r for r in restricted_db['restricted_users'] if r['email'] == user['email']), None)
            if restricted_user:
                # 만료 체크 (영구 제한은 expires_at이 null)
                if restricted_user.get('expires_at'):
                    expires_at = datetime.fromisoformat(restricted_user['expires_at'])
                    if datetime.now().astimezone() > expires_at:
                        # 만료됨 - 자동 해제
                        restricted_db['restricted_users'] = [r for r in restricted_db['restricted_users'] if r['email'] != user['email']]
                        with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
                            json.dump(restricted_db, f, ensure_ascii=False, indent=2)
                    else:
                        restriction = {
                            "level": restricted_user['level'],
                            "reason": restricted_user['reason'],
                            "expires_at": restricted_user['expires_at'],
                            "restricted_at": restricted_user['restricted_at']
                        }
                else:
                    # 영구 제한
                    restriction = {
                        "level": restricted_user['level'],
                        "reason": restricted_user['reason'],
                        "expires_at": None,
                        "restricted_at": restricted_user['restricted_at']
                    }
        except:
            pass

        return {
            "success": True,
            "message": "로그인 성공",
            "user": {
                "email": user['email'],
                "name": user['name'],
                "phone": user['phone']
            },
            "restriction": restriction
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 실패: {str(e)}")

@app.post("/api/logs")
async def save_log(log_data: LogData):
    """예매 로그 데이터를 저장합니다."""
    try:
        # 메타데이터에서 필요한 정보 추출
        flow_id = log_data.metadata.get("flow_id", f"flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        performance_id = log_data.metadata.get("performance_id", "unknown")
        payment_success = log_data.metadata.get("payment_success", False)
        
        # 날짜 형식: YYYYMMDD
        date_str = datetime.now().strftime('%Y%m%d')
        
        # 결제 성공 여부: success 또는 fail
        payment_status = "success" if payment_success else "fail"
        
        # 파일명 형식: [날짜]_[공연ID]_[flow_id]_[결제성공여부].json
        filename = f"{date_str}_{performance_id}_{flow_id}_{payment_status}.json"
        filepath = os.path.join(LOGS_DIR, filename)
        
        # JSON 파일로 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data.dict(), f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "filename": filename,
            "message": "로그가 성공적으로 저장되었습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 저장 실패: {str(e)}")

@app.get("/api/logs")
async def get_logs():
    """저장된 모든 로그 파일 목록을 반환합니다."""
    try:
        log_files = [f for f in os.listdir(LOGS_DIR) if f.endswith('.json')]
        # 파일 수정 시간 기준 내림차순 정렬 (최신 로그가 위로 오게)
        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(LOGS_DIR, x)), reverse=True)
        
        return {
            "success": True,
            "count": len(log_files),
            "files": log_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 목록 조회 실패: {str(e)}")

@app.get("/api/logs/{filename}")
async def get_log_file(filename: str):
    """특정 로그 파일의 내용을 반환합니다."""
    try:
        filepath = os.path.join(LOGS_DIR, filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다.")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        return {
            "success": True,
            "filename": filename,
            "data": log_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 파일 조회 실패: {str(e)}")

# ============================================
# 공연 오픈 시간 관리 API (새로 추가)
# ============================================

PERFORMANCES_FILE = os.path.join(DATA_DIR, "performances.json")

class PerformanceUpdate(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    venue: Optional[str] = None
    dates: Optional[List[str]] = None
    times: Optional[List[str]] = None
    description: Optional[str] = None
    open_time: Optional[str] = None
    status: Optional[str] = None



class PerformanceCreate(BaseModel):
    id: str
    title: str
    category: str
    venue: str
    dates: List[str]
    times: List[str]
    grades: List[Dict[str, Any]]
    image: str
    description: str
    open_time: str
    status: str = "upcoming"

@app.get("/api/performances")
async def get_performances():
    """모든 공연 목록을 반환합니다."""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            return {"success": True, "performances": []}
        
        with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {
            "success": True,
            "count": len(data.get("performances", [])),
            "performances": data.get("performances", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 목록 조회 실패: {str(e)}")

@app.get("/api/performances/{performance_id}")
async def get_performance(performance_id: str):
    """특정 공연의 정보를 반환합니다."""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            raise HTTPException(status_code=404, detail="공연 데이터를 찾을 수 없습니다.")
        
        with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        performance = next((p for p in data.get("performances", []) if p["id"] == performance_id), None)
        
        if not performance:
            raise HTTPException(status_code=404, detail="해당 공연을 찾을 수 없습니다.")
        
        return {
            "success": True,
            "performance": performance
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 조회 실패: {str(e)}")

@app.put("/api/admin/performances/{performance_id}")
async def update_performance(performance_id: str, update_data: PerformanceUpdate):
    """공연 정보를 업데이트합니다. (ID 변경 포함)"""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            raise HTTPException(status_code=404, detail="공연 데이터를 찾을 수 없습니다.")
        
        with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 대상 공연 찾기
        target_idx = -1
        for idx, p in enumerate(data.get("performances", [])):
            if p["id"] == performance_id:
                target_idx = idx
                break
        
        if target_idx == -1:
            raise HTTPException(status_code=404, detail="해당 공연을 찾을 수 없습니다.")
        
        performance = data["performances"][target_idx]
        
        # ID는 수정 불가 (코드 제거)

        # 나머지 필드 업데이트

        # 나머지 필드 업데이트
        if update_data.title is not None:
            performance["title"] = update_data.title
        if update_data.category is not None:
            performance["category"] = update_data.category
        if update_data.venue is not None:
            performance["venue"] = update_data.venue
        if update_data.dates is not None:
            performance["dates"] = update_data.dates
        if update_data.times is not None:
            performance["times"] = update_data.times
        if update_data.description is not None:
            performance["description"] = update_data.description
        if update_data.open_time is not None:
            performance["open_time"] = update_data.open_time
        if update_data.status is not None:
            performance["status"] = update_data.status
        
        # 파일 저장
        with open(PERFORMANCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return {
            "success": True,
            "message": "공연 정보가 업데이트되었습니다.",
            "performance": performance
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 업데이트 실패: {str(e)}")

@app.post("/api/admin/performances")
async def create_performance(performance_data: PerformanceCreate):
    """새 공연을 추가합니다."""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            data = {"performances": []}
        else:
            with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # ID 중복 체크
        if any(p["id"] == performance_data.id for p in data.get("performances", [])):
            raise HTTPException(status_code=400, detail="이미 존재하는 공연 ID입니다.")
        
        # 새 공연 추가
        new_performance = performance_data.dict()
        data.setdefault("performances", []).append(new_performance)
        
        # 파일 저장
        with open(PERFORMANCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return {
            "success": True,
            "message": "새 공연이 추가되었습니다.",
            "performance": new_performance
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 추가 실패: {str(e)}")

@app.delete("/api/admin/performances/{performance_id}")
async def delete_performance(performance_id: str):
    """공연을 삭제합니다."""
    try:
        if not os.path.exists(PERFORMANCES_FILE):
            raise HTTPException(status_code=404, detail="공연 데이터를 찾을 수 없습니다.")
        
        with open(PERFORMANCES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_count = len(data.get("performances", []))
        data["performances"] = [p for p in data.get("performances", []) if p["id"] != performance_id]
        
        if len(data["performances"]) == original_count:
            raise HTTPException(status_code=404, detail="해당 공연을 찾을 수 없습니다.")
        
        # 파일 저장
        with open(PERFORMANCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return {
            "success": True,
            "message": "공연이 삭제되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공연 삭제 실패: {str(e)}")


# ============================================
# 예매 제한 관리 API
# ============================================

RESTRICTION_DURATIONS = {
    1: timedelta(days=90),    # 1차: 3개월
    2: timedelta(days=180),   # 2차: 6개월
    3: None                   # 3차: 영구
}

@app.post("/api/admin/restrict-user")
async def restrict_user(data: RestrictUser):
    """사용자에게 예매 제한을 부여합니다."""
    try:
        if data.level not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="제한 단계는 1, 2, 3 중 하나여야 합니다.")

        with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
            restricted_db = json.load(f)

        # 이미 제한된 사용자인지 확인
        existing = next((r for r in restricted_db['restricted_users'] if r['email'] == data.email), None)
        if existing:
            # 단계 업데이트
            existing['level'] = data.level
            existing['reason'] = data.reason
            existing['restricted_at'] = datetime.now().astimezone().isoformat()
            existing['restricted_by'] = data.restricted_by
            duration = RESTRICTION_DURATIONS.get(data.level)
            existing['expires_at'] = (datetime.now().astimezone() + duration).isoformat() if duration else None
        else:
            # 새로 제한
            now = datetime.now().astimezone()
            duration = RESTRICTION_DURATIONS.get(data.level)
            restricted_db['restricted_users'].append({
                "email": data.email,
                "level": data.level,
                "reason": data.reason,
                "restricted_at": now.isoformat(),
                "expires_at": (now + duration).isoformat() if duration else None,
                "restricted_by": data.restricted_by
            })

        with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
            json.dump(restricted_db, f, ensure_ascii=False, indent=2)

        level_names = {1: "1차 (3개월)", 2: "2차 (6개월)", 3: "3차 (영구)"}
        return {
            "success": True,
            "message": f"{data.email}에게 {level_names[data.level]} 예매 제한이 적용되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"제한 적용 실패: {str(e)}")


@app.post("/api/admin/unrestrict-user")
async def unrestrict_user(data: dict):
    """사용자의 예매 제한을 해제합니다."""
    try:
        email = data.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="이메일이 필요합니다.")

        with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
            restricted_db = json.load(f)

        original_len = len(restricted_db['restricted_users'])
        restricted_db['restricted_users'] = [r for r in restricted_db['restricted_users'] if r['email'] != email]

        if len(restricted_db['restricted_users']) == original_len:
            raise HTTPException(status_code=404, detail="해당 사용자는 제한 목록에 없습니다.")

        with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
            json.dump(restricted_db, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": f"{email}의 예매 제한이 해제되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"제한 해제 실패: {str(e)}")


@app.get("/api/admin/restricted-users")
async def get_restricted_users():
    """제한된 사용자 목록을 반환합니다."""
    try:
        with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
            restricted_db = json.load(f)

        # 만료된 제한 자동 제거
        now = datetime.now().astimezone()
        active = []
        for r in restricted_db['restricted_users']:
            if r.get('expires_at'):
                if datetime.fromisoformat(r['expires_at']) > now:
                    active.append(r)
            else:
                active.append(r)  # 영구 제한

        # 변경사항 저장
        if len(active) != len(restricted_db['restricted_users']):
            restricted_db['restricted_users'] = active
            with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
                json.dump(restricted_db, f, ensure_ascii=False, indent=2)

        return {"restricted_users": active}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"제한 목록 조회 실패: {str(e)}")


@app.get("/api/admin/check-restriction/{email}")
async def check_restriction(email: str):
    """특정 사용자의 제한 상태를 확인합니다."""
    try:
        with open(RESTRICTED_FILE, 'r', encoding='utf-8') as f:
            restricted_db = json.load(f)

        restricted_user = next((r for r in restricted_db['restricted_users'] if r['email'] == email), None)

        if not restricted_user:
            return {"restricted": False}

        # 만료 체크
        if restricted_user.get('expires_at'):
            if datetime.now().astimezone() > datetime.fromisoformat(restricted_user['expires_at']):
                # 만료됨 - 자동 해제
                restricted_db['restricted_users'] = [r for r in restricted_db['restricted_users'] if r['email'] != email]
                with open(RESTRICTED_FILE, 'w', encoding='utf-8') as f:
                    json.dump(restricted_db, f, ensure_ascii=False, indent=2)
                return {"restricted": False}

        return {
            "restricted": True,
            "level": restricted_user['level'],
            "reason": restricted_user['reason'],
            "restricted_at": restricted_user['restricted_at'],
            "expires_at": restricted_user.get('expires_at')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"제한 확인 실패: {str(e)}")


@app.post("/api/admin/cancel-booking")
async def cancel_booking(data: CancelBooking):
    """예매를 취소합니다 (로그 파일의 status를 cancelled로 변경)."""
    try:
        filepath = os.path.join(LOGS_DIR, data.filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다.")

        with open(filepath, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        # metadata에 취소 정보 추가
        log_data['metadata']['cancelled'] = True
        log_data['metadata']['cancelled_at'] = datetime.now().astimezone().isoformat()
        log_data['metadata']['cancel_reason'] = data.reason
        log_data['metadata']['cancelled_by'] = data.cancelled_by

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": f"예매가 취소되었습니다: {data.filename}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예매 취소 실패: {str(e)}")


# 정적 파일 서빙 (HTML, CSS, JS)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
