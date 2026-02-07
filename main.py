from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
import re
from datetime import datetime

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

# 사용자 파일이 없으면 초기화
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"users": []}, f, ensure_ascii=False, indent=2)

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
    birthdate: Optional[str] = None

class LoginData(BaseModel):
    email: str
    password: str

class LogData(BaseModel):
    metadata: Dict[str, Any]
    stages: Dict[str, Any]

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
            "birthdate": signup_data.birthdate,
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
        
        return {
            "success": True,
            "message": "로그인 성공",
            "user": {
                "email": user['email'],
                "name": user['name'],
                "phone": user['phone']
            }
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
        metadata = log_data.metadata
        
        # flow_id 추출 (필수)
        flow_id = metadata.get("flow_id", f"flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # 공연 ID 추출
        performance_id = metadata.get("performance_id", "UNKNOWN")
        
        # 날짜 형식: YYYYMMDD
        date_str = datetime.now().strftime('%Y%m%d')
        
        # 결제 성공 여부 판단
        # is_completed와 completion_status를 우선 사용
        is_completed = metadata.get("is_completed", False)
        completion_status = metadata.get("completion_status", "unknown")
        
        # 결제 성공 여부 결정 로직
        if is_completed and completion_status == "success":
            payment_status = "success"
        elif completion_status == "abandoned":
            payment_status = "abandoned"
        elif completion_status == "failed":
            payment_status = "failed"
        else:
            # 하위 호환성: payment_success 필드도 확인
            payment_success = metadata.get("payment_success", False)
            payment_status = "success" if payment_success else "failed"
        
        # 📂 분류 저장 로직 추가 (macro/human 등)
        bot_type = metadata.get("bot_type", "")
        current_logs_dir = os.path.join(LOGS_DIR, bot_type) if bot_type else LOGS_DIR
        os.makedirs(current_logs_dir, exist_ok=True)

        # 파일명 형식: [날짜]_[공연ID]_[flow_id]_[결제성공여부].json
        # 예: 20260204_perf001_flow_20260204_abc123_success.json
        
        # 파일명 안전하게 처리 (특수문자 제거)
        def sanitize_filename(s):
            return re.sub(r'[^a-zA-Z0-9_\-]', '', str(s))
            
        safe_perf_id = sanitize_filename(performance_id)
        safe_flow_id = sanitize_filename(flow_id)
        
        filename = f"{date_str}_{safe_perf_id}_{safe_flow_id}_{payment_status}.json"
        filepath = os.path.join(current_logs_dir, filename)
        
        # JSON 파일로 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data.dict(), f, ensure_ascii=False, indent=2)
        
        print(f"✅ 로그 저장 성공: {filename}")
        
        return {
            "success": True,
            "filename": filename,
            "message": "로그가 성공적으로 저장되었습니다."
        }
    except Exception as e:
        import traceback
        error_msg = f"로그 저장 실패: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        with open("server_error.txt", "a", encoding="utf-8") as err_file:
            err_file.write(f"[{datetime.now()}] {error_msg}\n")
        raise HTTPException(status_code=500, detail=f"로그 저장 실패: {str(e)}")

@app.get("/api/logs")
async def get_logs():
    """저장된 모든 로그 파일 목록을 반환합니다."""
    try:
        log_files = [f for f in os.listdir(LOGS_DIR) if f.endswith('.json')]
        log_files.sort(reverse=True)  # 최신순 정렬
        
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


# 정적 파일 서빙 (HTML, CSS, JS)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
