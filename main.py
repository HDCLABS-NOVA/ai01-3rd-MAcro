from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
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
        flow_id = log_data.metadata.get("flow_id", f"flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        filename = f"booking_{flow_id}.json"
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

# 정적 파일 서빙 (HTML, CSS, JS)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
