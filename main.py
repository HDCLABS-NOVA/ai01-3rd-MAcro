"""
🎫 티켓 예매 시스템 - FastAPI 백엔드
봇/매크로 탐지를 위한 사용자 행동 데이터 수집 시스템
"""

import os
import json
import csv
import uuid
import hashlib
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import aiofiles

# ============== 앱 설정 ==============
app = FastAPI(title="티켓 예매 시스템", version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key="your-super-secret-key-change-in-production")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ============== 경로 설정 ==============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
CSV_LOG_FILE = os.path.join(BASE_DIR, "ai_03_action_logs.csv")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(LOGS_DIR, exist_ok=True)

# ============== 전역 상태 ==============
queue_states: Dict[str, Dict] = {}  # 대기열 상태
seat_states: Dict[str, Dict] = {}   # 좌석 상태
booking_count = 0                    # 예매 완료 수 (봇 로그 생성용)

# ============== 공연 데이터 ==============
PERFORMANCES = [
    {
        "id": "perf001",
        "title": "2026 아이유 콘서트 [The Golden Hour]",
        "artist": "아이유 (IU)",
        "venue": "잠실종합운동장 주경기장",
        "dates": ["2026-03-15", "2026-03-16"],
        "times": ["18:00", "19:00"],
        "price": {"VIP": 165000, "R": 143000, "S": 121000},
        "queue_size": 8000,
        "image": "/static/concert1.jpg",
        "mode": "A"
    },
    {
        "id": "perf002",
        "title": "뮤지컬 <웃는남자>",
        "artist": "수호, 규현",
        "venue": "예술의전당 오페라극장",
        "dates": ["2026-02-01", "2026-02-28"],
        "times": ["14:00", "19:30"],
        "price": {"VIP": 150000, "R": 130000, "S": 100000},
        "queue_size": 2000,
        "image": "/static/musical1.jpg",
        "mode": "A"
    },
    {
        "id": "perf003",
        "title": "2026 세븐틴 월드투어 [FOLLOW]",
        "artist": "세븐틴 (SEVENTEEN)",
        "venue": "고척스카이돔",
        "dates": ["2026-04-20", "2026-04-21"],
        "times": ["18:00"],
        "price": {"VIP": 176000, "R": 154000},
        "queue_size": 8000,
        "image": "/static/concert2.jpg",
        "mode": "B"
    },
    {
        "id": "perf004",
        "title": "2026 블랙핑크 앵콜 콘서트",
        "artist": "블랙핑크 (BLACKPINK)",
        "venue": "서울월드컵경기장",
        "dates": ["2026-05-10", "2026-05-11"],
        "times": ["19:00"],
        "price": {"VIP": 198000, "R": 165000, "S": 132000},
        "queue_size": 12000,
        "image": "/static/concert3.jpg",
        "mode": "A"
    },
    {
        "id": "perf005",
        "title": "뮤지컬 <오페라의 유령>",
        "artist": "조승우, 정선아",
        "venue": "블루스퀘어 신한카드홀",
        "dates": ["2026-03-01", "2026-05-31"],
        "times": ["14:00", "19:30"],
        "price": {"VIP": 170000, "R": 140000, "S": 110000},
        "queue_size": 3000,
        "image": "/static/musical2.jpg",
        "mode": "B"
    },
    {
        "id": "perf006",
        "title": "2026 BTS 단독 콘서트 [Yet To Come]",
        "artist": "방탄소년단 (BTS)",
        "venue": "부산아시아드주경기장",
        "dates": ["2026-06-15", "2026-06-16"],
        "times": ["18:00", "19:00"],
        "price": {"VIP": 220000, "R": 180000, "S": 150000},
        "queue_size": 15000,
        "image": "/static/concert4.jpg",
        "mode": "A"
    },
    {
        "id": "perf007",
        "title": "발레 <호두까기 인형>",
        "artist": "국립발레단",
        "venue": "예술의전당 오페라극장",
        "dates": ["2026-12-20", "2026-12-25"],
        "times": ["15:00", "19:00"],
        "price": {"VIP": 120000, "R": 90000, "S": 60000},
        "queue_size": 500,
        "image": "/static/ballet1.jpg",
        "mode": "C"
    },
    {
        "id": "perf008",
        "title": "2026 NCT 127 월드투어",
        "artist": "NCT 127",
        "venue": "KSPO돔",
        "dates": ["2026-07-05", "2026-07-06"],
        "times": ["18:00"],
        "price": {"VIP": 165000, "R": 143000},
        "queue_size": 6000,
        "image": "/static/concert5.jpg",
        "mode": "B"
    }
]

# ============== 유틸리티 함수 ==============
def hash_password(password: str) -> str:
    """SHA-256 비밀번호 해싱"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users() -> dict:
    """사용자 데이터 로드"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users: dict):
    """사용자 데이터 저장"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_current_user(request: Request) -> Optional[dict]:
    """현재 로그인된 사용자 정보"""
    user_id = request.session.get("user_id")
    if user_id:
        users = load_users()
        return users.get(user_id)
    return None

def init_seat_state(perf_id: str) -> Dict:
    """좌석 상태 초기화 (VIP 150석, R석 450석 = 총 600석)"""
    seats = {}
    # VIP석 (A~C열, 1~50번)
    for row in ['A', 'B', 'C']:
        for num in range(1, 51):
            seats[f"VIP-{row}{num}"] = {"status": "available", "grade": "VIP"}
    
    # R석 (D~L열, 1~50번)
    for row in ['D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']:
        for num in range(1, 51):
            seats[f"R-{row}{num}"] = {"status": "available", "grade": "R"}
    
    return seats

async def save_csv_log(log_data: dict):
    """CSV 로그 저장 (비동기)"""
    file_exists = os.path.exists(CSV_LOG_FILE)
    
    async with aiofiles.open(CSV_LOG_FILE, 'a', encoding='utf-8', newline='') as f:
        fieldnames = ['timestamp', 'user_ip', 'session_id', 'user_id', 'action', 
                      'target_id', 'click_pos_x', 'click_pos_y', 'time_delta', 'extra']
        
        if not file_exists:
            header = ','.join(fieldnames) + '\n'
            await f.write(header)
        
        row = ','.join([str(log_data.get(field, '')) for field in fieldnames]) + '\n'
        await f.write(row)

async def save_session_log(session_data: dict):
    """JSON 세션 로그 저장 (비동기)"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    session_id = session_data.get('session_id', str(uuid.uuid4()))
    filename = f"{timestamp}_session_{session_id}.json"
    filepath = os.path.join(LOGS_DIR, filename)
    
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(session_data, ensure_ascii=False, indent=2))
    
    return filename

def generate_bot_log(bot_type: str) -> dict:
    """봇 로그 생성 - 기존 정상 로그 구조와 동일한 포맷"""
    flow_id = f"flow_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    now = datetime.now()
    
    # 봇 유형별 패턴 정의
    bot_patterns = {
        "fast_click": {
            "description": "빠른 클릭 봇",
            "avg_click_interval": 0.15,  # 매우 빠른 클릭
            "trajectory_smoothness": 0.3,  # 낮음 = 직선적
            "hover_duration": 0,
            "total_time": random.uniform(5, 10),
            "captcha_solve_time": random.uniform(0.1, 0.5),
            "queue_bypass": False
        },
        "linear_move": {
            "description": "직선 이동 봇",
            "avg_click_interval": 0.5,
            "trajectory_smoothness": 0.2,  # 매우 직선적
            "hover_duration": 0.1,
            "total_time": random.uniform(10, 15),
            "captcha_solve_time": random.uniform(0.3, 1.0),
            "queue_bypass": False
        },
        "repeat_pattern": {
            "description": "반복 패턴 봇",
            "avg_click_interval": 1.0,  # 정확히 1초
            "trajectory_smoothness": 0.4,
            "hover_duration": 0.2,
            "total_time": random.uniform(15, 25),
            "captcha_solve_time": random.uniform(0.5, 1.5),
            "queue_bypass": False
        },
        "slow_auto": {
            "description": "느린 자동화 봇 (탐지 회피)",
            "avg_click_interval": 2.5,
            "trajectory_smoothness": 0.6,  # 좀 더 자연스럽게
            "hover_duration": 0.5,
            "total_time": random.uniform(25, 45),
            "captcha_solve_time": random.uniform(2.0, 4.0),
            "queue_bypass": False
        },
        "fixed_coord": {
            "description": "좌표 고정 봇",
            "avg_click_interval": 0.3,
            "trajectory_smoothness": 0.1,  # 직선에 가까움
            "hover_duration": 0,
            "total_time": random.uniform(7, 12),
            "captcha_solve_time": random.uniform(0.2, 0.8),
            "queue_bypass": False,
            "fixed_positions": True  # 항상 같은 좌표
        },
        "queue_bypass": {
            "description": "대기열 우회 봇 (직접링크)",
            "avg_click_interval": 0.2,
            "trajectory_smoothness": 0.3,
            "hover_duration": 0,
            "total_time": random.uniform(3, 6),
            "captcha_solve_time": random.uniform(0.1, 0.3),
            "queue_bypass": True  # 대기열 건너뜀
        }
    }
    
    pattern = bot_patterns.get(bot_type, bot_patterns["fast_click"])
    
    # 공연 선택
    perf = random.choice(PERFORMANCES)
    selected_date = random.choice(perf["dates"])
    selected_time = random.choice(perf["times"])
    
    # 타임스탬프 생성
    flow_start = now
    perf_duration = random.uniform(2, 5)  # 공연 선택 단계
    queue_duration = 0 if pattern["queue_bypass"] else random.uniform(3, 8)
    captcha_duration = pattern["captcha_solve_time"]
    section_duration = random.uniform(1, 3)
    booking_duration = random.uniform(3, 8)
    
    perf_end = flow_start + timedelta(seconds=perf_duration)
    queue_end = perf_end + timedelta(seconds=queue_duration)
    captcha_end = queue_end + timedelta(seconds=captcha_duration)
    section_end = captcha_end + timedelta(seconds=section_duration)
    booking_end = section_end + timedelta(seconds=booking_duration)
    
    total_duration_ms = int((booking_end - flow_start).total_seconds() * 1000)
    
    # 좌석 선택 (봇은 빠르게 선택)
    final_seats = [f"R-{random.choice(['D','E','F','G','H'])}{random.randint(1,50)}" 
                   for _ in range(random.randint(1, 2))]
    
    # 마우스 궤적 생성 함수
    def generate_trajectory(start_x, start_y, end_x, end_y, duration_ms, smoothness):
        """마우스 궤적 생성 - smoothness가 낮을수록 직선적"""
        points = []
        num_points = max(5, int(duration_ms / 100))  # 100ms마다 1포인트
        
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            
            if smoothness < 0.3:  # 매우 직선적 (봇 특징)
                x = int(start_x + (end_x - start_x) * t)
                y = int(start_y + (end_y - start_y) * t)
            else:  # 약간의 노이즈 추가
                noise_x = random.randint(-5, 5) * smoothness
                noise_y = random.randint(-5, 5) * smoothness
                x = int(start_x + (end_x - start_x) * t + noise_x)
                y = int(start_y + (end_y - start_y) * t + noise_y)
            
            timestamp = int(i * 100)
            points.append([x, y, timestamp])
        
        return points
    
    # 클릭 생성 함수
    def generate_click(x, y, timestamp_iso, target="", is_integer_coord=True):
        """클릭 이벤트 생성"""
        return {
            "x": x,
            "y": y,
            "nx": round(x / 1920, 4),
            "ny": round(y / 953, 4),
            "viewport": {"w": 1920, "h": 953},
            "timestamp": timestamp_iso,
            "is_trusted": False,  # 봇이므로 False
            "click_duration": random.randint(50, 150) if pattern["hover_duration"] > 0 else 20,
            "is_integer": is_integer_coord
        }
    
    # Stages 데이터 생성
    stages = {}
    
    # 1. 공연 선택 단계 (perf)
    perf_trajectory = generate_trajectory(800, 400, 900, 600, int(perf_duration * 1000), pattern["trajectory_smoothness"])
    stages["perf"] = {
        "entry_time": flow_start.isoformat() + "Z",
        "exit_time": perf_end.isoformat() + "Z",
        "duration_ms": int(perf_duration * 1000),
        "card_clicks": [{
            "performance_id": perf["id"],
            "performance_title": perf["title"],
            "timestamp": (flow_start + timedelta(seconds=1)).isoformat() + "Z"
        }],
        "date_selections": [{
            "date": selected_date,
            "timestamp": (flow_start + timedelta(seconds=2)).isoformat() + "Z"
        }],
        "time_selections": [{
            "time": selected_time,
            "timestamp": (flow_start + timedelta(seconds=3)).isoformat() + "Z"
        }],
        "actions": [
            {"action": "card_click", "target": perf["id"], "timestamp": (flow_start + timedelta(seconds=1)).isoformat() + "Z"},
            {"action": "date_select", "target": selected_date, "timestamp": (flow_start + timedelta(seconds=2)).isoformat() + "Z"},
            {"action": "time_select", "target": selected_time, "timestamp": (flow_start + timedelta(seconds=3)).isoformat() + "Z"},
            {"action": "booking_start", "target": perf["id"], "date": selected_date, "time": selected_time, "timestamp": perf_end.isoformat() + "Z"}
        ],
        "mouse_trajectory": perf_trajectory
    }
    
    # 2. 대기열 단계 (queue) - 우회 봇은 건너뜀
    if not pattern["queue_bypass"]:
        queue_trajectory = generate_trajectory(900, 600, 1000, 800, int(queue_duration * 1000), pattern["trajectory_smoothness"])
        initial_pos = random.randint(500, perf.get("queue_size", 3000))
        stages["queue"] = {
            "entry_time": perf_end.isoformat() + "Z",
            "exit_time": queue_end.isoformat() + "Z",
            "duration_ms": int(queue_duration * 1000),
            "initial_position": initial_pos,
            "final_position": 0,
            "total_queue": perf.get("queue_size", 3000),
            "wait_duration_ms": int(queue_duration * 1000),
            "position_updates": [
                {"position": max(0, initial_pos - i * 100), "progress": min(99, int((i / 5) * 100)), 
                 "estimated_minutes": max(1, 5 - i), "timestamp": (perf_end + timedelta(seconds=i)).isoformat() + "Z"}
                for i in range(1, 6)
            ] + [{"position": 0, "status": "ready", "timestamp": queue_end.isoformat() + "Z"}],
            "mouse_trajectory": queue_trajectory
        }
    
    # 3. 캡챠 단계 (captcha)
    stages["captcha"] = {
        "entry_time": queue_end.isoformat() + "Z",
        "exit_time": captcha_end.isoformat() + "Z",
        "duration_ms": int(captcha_duration * 1000),
        "attempts": 1 if captcha_duration < 2 else random.randint(2, 3),  # 빠르면 의심
        "time_to_solve_ms": int(captcha_duration * 1000)
    }
    
    # 4. 구역 선택 단계 (section)
    section_traj = generate_trajectory(900, 700, 1110, 668, int(section_duration * 1000), pattern["trajectory_smoothness"])
    stages["section"] = {
        "entry_time": captcha_end.isoformat() + "Z",
        "exit_time": section_end.isoformat() + "Z",
        "duration_ms": int(section_duration * 1000),
        "final_section": "R-R",
        "final_grade": "R",
        "clicks": [
            {
                "section": "R-R",
                "grade": "R",
                "price": perf["price"].get("R", 140000),
                **generate_click(1110, 668, (captcha_end + timedelta(seconds=section_duration/2)).isoformat() + "Z", "R-R", 
                                pattern.get("fixed_positions", False))
            }
        ],
        "mouse_trajectory": section_traj
    }
    
    # 5. 좌석 선택 단계 (booking)
    booking_traj = generate_trajectory(1000, 650, 1200, 400, int(booking_duration * 1000), pattern["trajectory_smoothness"])
    
    # 봇은 클릭 간격이 일정함
    seat_clicks = []
    for i, seat in enumerate(final_seats):
        click_time = section_end + timedelta(seconds=i * pattern["avg_click_interval"])
        seat_clicks.append({
            "seat_id": seat,
            "grade": "R",
            "price": perf["price"].get("R", 140000),
            **generate_click(random.randint(800, 1200), random.randint(300, 600), 
                           click_time.isoformat() + "Z", seat,
                           pattern.get("fixed_positions", False))
        })
    
    stages["booking"] = {
        "entry_time": section_end.isoformat() + "Z",
        "exit_time": booking_end.isoformat() + "Z",
        "duration_ms": int(booking_duration * 1000),
        "selected_seats": final_seats,
        "seat_clicks": seat_clicks,
        "mouse_trajectory": booking_traj,
        "keyboard_events": [],  # 봇은 키보드 사용 없음
        "scroll_events": []      # 봇은 스크롤 거의 없음
    }
    
    # 메타데이터
    metadata = {
        "flow_id": flow_id,
        "session_id": session_id,
        "user_id": f"bot_{bot_type}_{random.randint(1000, 9999)}",
        "user_email": f"bot_{random.randint(1000, 9999)}@fake.com",
        "user_ip": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "created_at": flow_start.isoformat() + "Z",
        "performance_id": perf["id"],
        "performance_title": perf["title"],
        "selected_date": selected_date,
        "selected_time": selected_time,
        "flow_start_time": flow_start.isoformat() + "Z",
        "flow_end_time": booking_end.isoformat() + "Z",
        "total_duration_ms": total_duration_ms,
        "is_completed": True,
        "completion_status": "success",
        "final_seats": final_seats,
        "booking_id": f"M{random.randint(10000000, 99999999)}",
        "browser_info": {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "platform": "Win32",
            "cookieEnabled": True,
            "doNotTrack": None,
            "hardwareConcurrency": 16,
            "deviceMemory": 8,
            "maxTouchPoints": 0,
            "language": "ko-KR",
            "webdriver": True,  # 봇 탐지 포인트!
            "screen": {"width": 1920, "height": 1080, "colorDepth": 24, "pixelRatio": 1},
            "window": {"outerWidth": 1920, "outerHeight": 1040, "innerWidth": 1920, "innerHeight": 953},
            "timezone": "Asia/Seoul"
        }
    }
    
    # 봇 탐지 정보 (간단한 구조)
    bot_info = {
        "is_bot": True,
        "type": bot_type,
        "description": pattern["description"],
        "confidence": round(random.uniform(0.75, 0.98), 2),
        "detected_features": []
    }
    
    # 탐지된 특징들 추가
    features = []
    if pattern["avg_click_interval"] < 0.5:
        features.append("fast_clicking")
    if pattern["avg_click_interval"] == 1.0:
        features.append("uniform_intervals")
    if pattern["trajectory_smoothness"] < 0.4:
        features.append("linear_trajectory")
    if captcha_duration < 1.0:
        features.append("fast_captcha")
    if total_duration_ms < 15000:
        features.append("suspiciously_fast")
    if pattern["queue_bypass"]:
        features.append("queue_bypass")
    
    bot_info["detected_features"] = features
    
    return {
        "metadata": metadata,
        "stages": stages,
        "bot": bot_info  # 간단한 구조
    }


# ============== 페이지 라우트 ==============
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """홈 - 로그인 페이지로 리다이렉트"""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/performances", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인/회원가입 페이지"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, name: str = Form(...), password: str = Form(...)):
    """로그인 처리"""
    users = load_users()
    hashed = hash_password(password)
    
    for user_id, user_data in users.items():
        if user_data["name"] == name and user_data["password"] == hashed:
            request.session["user_id"] = user_id
            request.session["session_id"] = str(uuid.uuid4())
            return RedirectResponse(url="/performances", status_code=302)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "이메일 또는 비밀번호가 올바르지 않습니다."
    })

@app.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    birth: str = Form(...),
    password: str = Form(...)
):
    """회원가입 처리"""
    users = load_users()
    
    # 이메일 중복 체크
    for user_data in users.values():
        if user_data["email"] == email:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "이미 등록된 이메일입니다.",
                "tab": "register"
            })
    
    user_id = str(uuid.uuid4())
    users[user_id] = {
        "name": name,
        "email": email,
        "phone": phone,
        "birth": birth,
        "password": hash_password(password),
        "created_at": datetime.now().isoformat()
    }
    save_users(users)
    
    request.session["user_id"] = user_id
    request.session["session_id"] = str(uuid.uuid4())
    return RedirectResponse(url="/performances", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    """로그아웃"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

@app.get("/performances", response_class=HTMLResponse)
async def performances_page(request: Request):
    """공연 목록 페이지"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("perf_list.html", {
        "request": request,
        "user": user,
        "performances": PERFORMANCES
    })

@app.get("/queue/{perf_id}", response_class=HTMLResponse)
async def queue_page(request: Request, perf_id: str, date: str = "", time: str = ""):
    """대기열 페이지"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    perf = next((p for p in PERFORMANCES if p["id"] == perf_id), None)
    if not perf:
        raise HTTPException(status_code=404, detail="공연을 찾을 수 없습니다.")
    
    # 대기열 상태 초기화
    session_id = request.session.get("session_id", str(uuid.uuid4()))
    if session_id not in queue_states:
        queue_states[session_id] = {
            "position": random.randint(1, perf["queue_size"]),
            "total": perf["queue_size"],
            "start_time": datetime.now().isoformat()
        }
    
    return templates.TemplateResponse("queue.html", {
        "request": request,
        "user": user,
        "performance": perf,
        "selected_date": date,
        "selected_time": time,
        "queue_state": queue_states[session_id],
        "total_queue": queue_states[session_id]["total"],
        "initial_position": queue_states[session_id]["position"]
    })

@app.get("/api/queue/status")
async def queue_status(request: Request):
    """대기열 상태 API"""
    session_id = request.session.get("session_id")
    if session_id and session_id in queue_states:
        state = queue_states[session_id]
        # 테스트용: 초당 약 100~200명씩 감소 (빠른 진행)
        state["position"] = max(0, state["position"] - random.randint(100, 200))
        
        if state["position"] <= 0:
            return {"status": "ready", "position": 0}
        
        return {
            "status": "waiting",
            "position": state["position"],
            "total": state["total"],
            "estimated_minutes": max(1, state["position"] // 100)
        }
    return {"status": "error", "message": "세션을 찾을 수 없습니다."}

@app.get("/captcha/{perf_id}", response_class=HTMLResponse)
async def captcha_page(request: Request, perf_id: str, date: str = "", time: str = ""):
    """캡챠 페이지 (대기열 후, 구역선택 전)"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    perf = next((p for p in PERFORMANCES if p["id"] == perf_id), None)
    if not perf:
        raise HTTPException(status_code=404, detail="공연을 찾을 수 없습니다.")
    
    session_id = request.session.get("session_id", str(uuid.uuid4()))
    
    return templates.TemplateResponse("captcha.html", {
        "request": request,
        "user": user,
        "performance": perf,
        "selected_date": date,
        "selected_time": time,
        "session_id": session_id
    })

@app.get("/section/{perf_id}", response_class=HTMLResponse)
async def section_select_page(request: Request, perf_id: str, date: str = "", time: str = ""):
    """구역 선택 페이지"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    perf = next((p for p in PERFORMANCES if p["id"] == perf_id), None)
    if not perf:
        raise HTTPException(status_code=404, detail="공연을 찾을 수 없습니다.")
    
    # S석 가격 추가 (없으면 R석의 80%)
    if "S" not in perf["price"]:
        perf["price"]["S"] = int(perf["price"]["R"] * 0.8)
    
    return templates.TemplateResponse("section_select.html", {
        "request": request,
        "user": user,
        "performance": perf,
        "selected_date": date,
        "selected_time": time
    })

@app.get("/booking/{perf_id}", response_class=HTMLResponse)
async def booking_page(request: Request, perf_id: str, date: str = "", time: str = "", section: str = "", grade: str = ""):
    """예매 페이지 (좌석 선택)"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    perf = next((p for p in PERFORMANCES if p["id"] == perf_id), None)
    if not perf:
        raise HTTPException(status_code=404, detail="공연을 찾을 수 없습니다.")
    
    # 좌석 상태 초기화
    if perf_id not in seat_states:
        seat_states[perf_id] = init_seat_state(perf_id)
    
    session_id = request.session.get("session_id", str(uuid.uuid4()))
    
    # S석 가격 추가 (없으면 R석의 80%)
    if "S" not in perf["price"]:
        perf["price"]["S"] = int(perf["price"]["R"] * 0.8)
    
    return templates.TemplateResponse("seat_select.html", {
        "request": request,
        "user": user,
        "performance": perf,
        "selected_date": date,
        "selected_time": time,
        "seats": seat_states[perf_id],
        "session_id": session_id,
        "mode": perf["mode"],
        "selected_section": section,
        "selected_grade": grade
    })

@app.get("/step2/{perf_id}", response_class=HTMLResponse)
async def step2_discount(request: Request, perf_id: str, date: str = "", time: str = "", seats: str = ""):
    """Step 2: 할인권종 선택"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    perf = next((p for p in PERFORMANCES if p["id"] == perf_id), None)
    if not perf:
        raise HTTPException(status_code=404, detail="공연을 찾을 수 없습니다.")
    
    selected_seats = seats.split(",") if seats else []
    session_id = request.session.get("session_id", str(uuid.uuid4()))
    
    # 좌석 가격 계산
    total_price = 0
    for seat_id in selected_seats:
        if seat_id:
            grade = seat_id.split("-")[0] if "-" in seat_id else "R"
            total_price += perf["price"].get(grade, 0)
    
    return templates.TemplateResponse("discount_select.html", {
        "request": request,
        "user": user,
        "performance": perf,
        "selected_date": date,
        "selected_time": time,
        "selected_seats": selected_seats,
        "total_price": total_price,
        "session_id": session_id
    })

@app.get("/step3/{perf_id}", response_class=HTMLResponse)
async def step3_booker(request: Request, perf_id: str, date: str = "", time: str = "", seats: str = "", discount: str = "normal"):
    """Step 3: 예매자 정보 및 배송 선택"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    perf = next((p for p in PERFORMANCES if p["id"] == perf_id), None)
    if not perf:
        raise HTTPException(status_code=404, detail="공연을 찾을 수 없습니다.")
    
    selected_seats = seats.split(",") if seats else []
    session_id = request.session.get("session_id", str(uuid.uuid4()))
    
    # 가격 계산
    total_price = 0
    for seat_id in selected_seats:
        if seat_id:
            grade = seat_id.split("-")[0] if "-" in seat_id else "R"
            total_price += perf["price"].get(grade, 0)
    
    # 할인 적용
    discount_rates = {"normal": 0, "disabled": 0.5, "veteran": 0.3, "senior": 0.2}
    discount_rate = discount_rates.get(discount, 0)
    discount_amount = int(total_price * discount_rate)
    
    return templates.TemplateResponse("order_info.html", {
        "request": request,
        "user": user,
        "performance": perf,
        "selected_date": date,
        "selected_time": time,
        "selected_seats": selected_seats,
        "discount_type": discount,
        "total_price": total_price,
        "discount_amount": discount_amount,
        "final_price": total_price - discount_amount,
        "session_id": session_id
    })

@app.get("/step4/{perf_id}", response_class=HTMLResponse)
async def step4_payment(request: Request, perf_id: str, date: str = "", time: str = "", seats: str = "", discount: str = "normal", delivery: str = "pickup"):
    """Step 4: 결제 수단 선택"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    perf = next((p for p in PERFORMANCES if p["id"] == perf_id), None)
    if not perf:
        raise HTTPException(status_code=404, detail="공연을 찾을 수 없습니다.")
    
    selected_seats = seats.split(",") if seats else []
    session_id = request.session.get("session_id", str(uuid.uuid4()))
    
    # 가격 계산
    total_price = 0
    for seat_id in selected_seats:
        if seat_id:
            grade = seat_id.split("-")[0] if "-" in seat_id else "R"
            total_price += perf["price"].get(grade, 0)
    
    discount_rates = {"normal": 0, "disabled": 0.5, "veteran": 0.3, "senior": 0.2}
    discount_rate = discount_rates.get(discount, 0)
    discount_amount = int(total_price * discount_rate)
    delivery_fee = 3000 if delivery == "delivery" else 0
    final_price = total_price - discount_amount + delivery_fee
    
    return templates.TemplateResponse("payment.html", {
        "request": request,
        "user": user,
        "performance": perf,
        "selected_date": date,
        "selected_time": time,
        "selected_seats": selected_seats,
        "discount_type": discount,
        "delivery_type": delivery,
        "total_price": total_price,
        "discount_amount": discount_amount,
        "delivery_fee": delivery_fee,
        "final_price": final_price,
        "session_id": session_id
    })

@app.get("/api/seats/{perf_id}")
async def get_seats(perf_id: str):
    """좌석 상태 API"""
    if perf_id not in seat_states:
        seat_states[perf_id] = init_seat_state(perf_id)
    
    return {"seats": seat_states[perf_id]}

@app.post("/api/seat/reserve")
async def reserve_seat(request: Request, seat_id: str = Form(...), perf_id: str = Form(...)):
    """좌석 예약 API"""
    if perf_id in seat_states and seat_id in seat_states[perf_id]:
        if seat_states[perf_id][seat_id]["status"] == "available":
            seat_states[perf_id][seat_id]["status"] = "selected"
            seat_states[perf_id][seat_id]["user"] = request.session.get("user_id")
            return {"success": True, "seat_id": seat_id}
    return {"success": False, "message": "좌석을 선택할 수 없습니다."}

@app.post("/api/auto-reserve")
async def auto_reserve(perf_id: str = Form(...)):
    """자동 예매 (백그라운드 시뮬레이션)"""
    if perf_id not in seat_states:
        return {"success": False}
    
    seats = seat_states[perf_id]
    available = [sid for sid, s in seats.items() if s["status"] == "available"]
    total = len(seats)
    reserved = total - len(available)
    
    # 30% 제한
    if reserved < total * 0.3 and available:
        seat_id = random.choice(available)
        seats[seat_id]["status"] = "sold"
        seats[seat_id]["user"] = "auto_system"
        return {"success": True, "seat_id": seat_id}
    
    return {"success": False, "message": "자동 예매 한도 도달"}

# ============== 로그 API ==============
@app.post("/api/log")
async def save_log(request: Request):
    """행동 로그 저장 API"""
    data = await request.json()
    client_ip = request.client.host if request.client else "unknown"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_ip": client_ip,
        "session_id": data.get("session_id", ""),
        "user_id": request.session.get("user_id", ""),
        "action": data.get("action", ""),
        "target_id": data.get("target_id", ""),
        "click_pos_x": data.get("x", ""),
        "click_pos_y": data.get("y", ""),
        "time_delta": data.get("time_delta", ""),
        "extra": json.dumps(data.get("extra", {}))
    }
    
    await save_csv_log(log_entry)
    return {"success": True}

# ============== LEGACY API: session-log (DISABLED) ==============
# Flow 기반 로그만 사용하므로 비활성화
# @app.post("/api/session-log")
# async def save_session_log_api(request: Request):
#     """세션 로그 저장 API (기존 방식)"""
#     data = await request.json()
#     client_ip = request.client.host if request.client else "unknown"
#     
#     session_data = {
#         **data,
#         "user_ip": client_ip,
#         "user_id": request.session.get("user_id", ""),
#         "saved_at": datetime.now().isoformat()
#     }
#     
#     filename = await save_session_log(session_data)
#     return {"success": True, "filename": filename}


# ============== LEGACY API: stage-log (DISABLED) ==============
# Flow 기반 로그만 사용하므로 비활성화
# @app.post("/api/stage-log")
# async def save_stage_log(request: Request):
#     """3단계 로그 저장 API (perf, que, book)"""
#     data = await request.json()
#     client_ip = request.client.host if request.client else "unknown"
#     
#     session_id = data.get("session_id", str(uuid.uuid4())[:8])
#     stage = data.get("stage", "unknown")  # perf, que, book
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     
#     # 사용자 정보 조회
#     user_id = request.session.get("user_id", "")
#     user_email = ""
#     if user_id:
#         users = load_users()
#         if user_id in users:
#             user_email = users[user_id].get("email", user_id)
#     
#     # 파일명: {세션ID}_{날짜시간}_{단계명}.json
#     filename = f"{session_id}_{timestamp}_{stage}.json"
#     filepath = os.path.join(LOGS_DIR, filename)
#     
#     log_data = {
#         "session_id": session_id,
#         "stage": stage,
#         "user_ip": client_ip,
#         "user_id": user_id,
#         "user_email": user_email,
#         "created_at": datetime.now().isoformat(),
#         **data
#     }
#     
#     async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
#         await f.write(json.dumps(log_data, ensure_ascii=False, indent=2))
#     
#     return {"success": True, "filename": filename, "stage": stage}


@app.post("/api/flow-log")
@app.post("/api/flow-log")
async def save_flow_log(request: Request):
    """Flow 로그 저장 API (누적 업데이트 지원)"""
    try:
        data = await request.json()
        client_ip = request.client.host if request.client else "unknown"
        
        # IP 주소 추가
        if 'metadata' in data:
            data['metadata']['user_ip'] = client_ip
        
        # 메타데이터 추출
        metadata = data.get('metadata', {})
        flow_id = metadata.get('flow_id', 'unknown')
        perf_id = metadata.get('performance_id', 'unknown')
        status = metadata.get('completion_status', 'ongoing') # 기본값 ongoing
        created_at = metadata.get('created_at', datetime.now().isoformat())
        
        if flow_id == 'unknown':
            return {"success": False, "error": "Missing flow_id"}

        # 날짜 추출 (YYYYMMDD)
        try:
            date_str = created_at[:10].replace('-', '')
        except:
            date_str = datetime.now().strftime('%Y%m%d')
            
        # 기존 파일 찾기 (동일한 flow_id를 가진 파일 검색)
        existing_filepath = None
        existing_filename = None
        
        if os.path.exists(LOGS_DIR):
            for f in os.listdir(LOGS_DIR):
                if flow_id in f and f.endswith('.json'):
                    existing_filename = f
                    existing_filepath = os.path.join(LOGS_DIR, f)
                    break
        
        final_data = data
        
        # 기존 파일이 있으면 병합 (Merge)
        if existing_filepath:
            try:
                async with aiofiles.open(existing_filepath, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    existing_data = json.loads(content)
                    
                # 메타데이터 업데이트 (최신 정보로 덮어쓰기)
                if 'metadata' in existing_data:
                    existing_data['metadata'].update(metadata)
                else:
                    existing_data['metadata'] = metadata
                    
                # 스테이지 데이터 병합 (기존 스테이지 유지하면서 새 스테이지 추가/업데이트)
                if 'stages' in data and 'stages' in existing_data:
                    existing_data['stages'].update(data['stages'])
                elif 'stages' in data:
                    existing_data['stages'] = data['stages']
                    
                final_data = existing_data
                print(f"🔄 Merging flow log for {flow_id}")
            except Exception as e:
                print(f"⚠️ Failed to read existing log, overwriting: {e}")
        
        # 새 파일명 생성
        new_filename = f"{date_str}_{perf_id}_{flow_id}_{status}.json"
        new_filepath = os.path.join(LOGS_DIR, new_filename)
        
        # 저장
        async with aiofiles.open(new_filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(final_data, ensure_ascii=False, indent=2))
            
        # 파일명이 변경되었고 기존 파일이 존재하면 기존 파일 삭제 (상태 변경 시)
        if existing_filepath and existing_filename != new_filename:
            try:
                os.remove(existing_filepath)
                print(f"🗑️ Removed old log file: {existing_filename}")
            except Exception as e:
                print(f"⚠️ Failed to remove old log file: {e}")
        
        print(f"✅ Flow log saved: {new_filename}")
        return {"success": True, "flow_id": flow_id, "filename": new_filename}
    
    except Exception as e:
        print(f"❌ Failed to save flow log: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/complete")
async def complete_booking(request: Request):
    """예매 완료 API"""
    global booking_count
    
    data = await request.json()
    client_ip = request.client.host if request.client else "unknown"
    
    # 예매번호 생성 (M + 8자리 숫자)
    booking_id = f"M{random.randint(10000000, 99999999)}"
    
    # 기존 book 로그 파일에 결제 완료 정보 추가
    user_id = request.session.get("user_id", "")
    session_id = data.get("session_id", "")
    
    # 가장 최근 book 로그 파일 찾기 (user_id 또는 session_id로 매칭)
    book_log_updated = False
    book_files = []
    
    for filename in os.listdir(LOGS_DIR):
        if "_book.json" in filename:
            filepath = os.path.join(LOGS_DIR, filename)
            book_files.append((filename, filepath, os.path.getmtime(filepath)))
    
    # 최신순 정렬
    book_files.sort(key=lambda x: x[2], reverse=True)
    
    for filename, filepath, _ in book_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                book_log = json.load(f)
            
            # session_id 또는 user_id로 매칭
            log_user_id = book_log.get("user_id", "")
            log_session_id = book_log.get("session_id", "")
            
            # 이미 결제 완료된 로그는 건너뛰기
            if book_log.get("payment_completed"):
                continue
            
            # 매칭 조건: session_id가 일치하거나, user_id가 일치하는 최신 로그
            if (session_id and log_session_id == session_id) or (user_id and log_user_id == user_id):
                # 결제 완료 정보 추가
                book_log["payment_completed"] = True
                book_log["booking_id"] = booking_id
                book_log["payment_completed_at"] = datetime.now().isoformat()
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(book_log, f, ensure_ascii=False, indent=2)
                
                book_log_updated = True
                print(f"book 로그 업데이트 완료: {filename}")
                break
        except Exception as e:
            print(f"book 로그 처리 실패 ({filename}): {e}")
            continue
    
    
    # Legacy 로그 생성 비활성화 - Flow 기반 로그만 사용
    # session_data = {
    #     **data,
    #     "user_ip": client_ip,
    #     "user_id": request.session.get("user_id", ""),
    #     "is_bot": False,
    #     "booking_id": booking_id,
    #     "completed_at": datetime.now().isoformat()
    # }
    # await save_session_log(session_data)
    
    booking_count += 1
    
    # 봇 로그 생성도 비활성화 - Flow 기반 로그만 사용
    # if booking_count % 6 == 0:
    #     bot_types = ["fast_click", "linear_move", "repeat_pattern", "slow_auto", "fixed_coord"]
    #     for _ in range(2):
    #         bot_type = random.choice(bot_types)
    #         bot_log = generate_bot_log(bot_type)
    #         await save_session_log(bot_log)
    #     
    #     # 대기열 봇 1개
    #     queue_bot = generate_bot_log("queue_bypass")
    #     await save_session_log(queue_bot)
    
    return {"success": True, "booking_id": booking_id}

# ============== 로그 뷰어 ==============
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """로그 뷰어 페이지"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # 로그 파일 목록
    log_files = []
    if os.path.exists(LOGS_DIR):
        for f in sorted(os.listdir(LOGS_DIR), reverse=True)[:50]:
            if f.endswith('.json'):
                filepath = os.path.join(LOGS_DIR, f)
                with open(filepath, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    
                    # duration 계산 (새로운 형식 지원)
                    duration = data.get("total_duration_ms", 0)
                    if duration == 0:
                        # page_entry_time / page_exit_time에서 계산
                        if data.get("page_entry_time") and data.get("page_exit_time"):
                            try:
                                start = datetime.fromisoformat(data["page_entry_time"].replace("Z", "+00:00"))
                                end = datetime.fromisoformat(data["page_exit_time"].replace("Z", "+00:00"))
                                duration = (end - start).total_seconds() * 1000
                            except:
                                pass
                        # queue_start_time / queue_end_time에서 계산
                        elif data.get("queue_start_time") and data.get("queue_end_time"):
                            try:
                                start = datetime.fromisoformat(data["queue_start_time"].replace("Z", "+00:00"))
                                end = datetime.fromisoformat(data["queue_end_time"].replace("Z", "+00:00"))
                                duration = (end - start).total_seconds() * 1000
                            except:
                                pass
                        # booking_start_time / booking_end_time에서 계산
                        elif data.get("booking_start_time") and data.get("booking_end_time"):
                            try:
                                start = datetime.fromisoformat(data["booking_start_time"].replace("Z", "+00:00"))
                                end = datetime.fromisoformat(data["booking_end_time"].replace("Z", "+00:00"))
                                duration = (end - start).total_seconds() * 1000
                            except:
                                pass
                        # wait_duration_ms 사용
                        elif data.get("wait_duration_ms"):
                            duration = data["wait_duration_ms"]
                    
                    # 단계별 표시명
                    stage_names = {'perf': '🎭 공연창', 'que': '⏳ 대기열', 'book': '🎫 예매창'}
                    stage = data.get("stage", "")
                    display_stage = stage_names.get(stage, stage)
                    
                    # 생성 시간
                    created_at = data.get("created_at", "")
                    
                    log_files.append({
                        "filename": f,
                        "is_bot": data.get("is_bot", False),
                        "session_id": data.get("session_id", ""),
                        "user_id": data.get("user_id", ""),
                        "user_email": data.get("user_email", ""),
                        "duration": duration,
                        "stage": stage,
                        "display_stage": display_stage,
                        "created_at": created_at
                    })
    
    # 정렬: 생성시간 최신순 → 세션ID 순
    log_files.sort(key=lambda x: (x.get("created_at", "") or "", x.get("session_id", "")), reverse=True)
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "log_files": log_files
    })

@app.get("/api/logs/{filename}")
async def get_log_file(filename: str):
    """로그 파일 조회 API"""
    filepath = os.path.join(LOGS_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다.")

# ============== 매크로 시뮬레이터 ==============
@app.get("/macro-simulator", response_class=HTMLResponse)
async def macro_simulator_page(request: Request):
    """매크로 시뮬레이터 페이지 (교육용)"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("macro_simulator.html", {
        "request": request,
        "user": user
    })

@app.post("/api/generate-macro-log")
async def generate_macro_log_api(request: Request):
    """매크로 로그 생성 API"""
    try:
        data = await request.json()
        bot_type = data.get("bot_type", "fast_click")
        index = data.get("index", 1)
        
        # 봇 로그 생성
        log_data = generate_bot_log(bot_type)
        
        # 파일명 생성: 정상 로그와 완전히 동일한 형식
        # 예: 20260129_perf005_flow_20260129_abc123_success.json
        date_str = datetime.now().strftime("%Y%m%d")
        perf_id = log_data["metadata"]["performance_id"]
        flow_id = log_data["metadata"]["flow_id"]
        completion = log_data["metadata"]["completion_status"]  # success
        
        filename = f"{date_str}_{perf_id}_{flow_id}_{completion}.json"
        filepath = os.path.join(LOGS_DIR, filename)
        
        # 로그 파일 저장 (bot 필드 포함)
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(log_data, ensure_ascii=False, indent=2))
        
        return {
            "success": True,
            "filename": filename,
            "bot_info": log_data["bot"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============== 서버 시작 ==============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)
