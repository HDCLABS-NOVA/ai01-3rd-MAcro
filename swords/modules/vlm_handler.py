"""
VLM Handler Module
VLM(Vision Language Model) API 호출을 위한 공통 함수들
"""

import os
import re
import json
import base64
import requests
import pyautogui
from io import BytesIO
from PIL import ImageGrab


def human_click(x: int, y: int, delay: float = 0.0):
    """
    사람처럼 자연스러운 마우스 움직임으로 클릭
    
    Args:
        x: 클릭할 X 좌표
        y: 클릭할 Y 좌표
        delay: 클릭 전 대기 시간 (초)
    """
    import time
    import random
    
    try:
        # 클릭 전 약간의 랜덤 대기 (0.1~0.3초)
        if delay > 0:
            time.sleep(delay)
        else:
            time.sleep(random.uniform(0.1, 0.3))
        
        # 사람처럼 자연스러운 곡선 움직임으로 목표 위치로 이동
        # duration: 0.3~0.7초 (사람의 자연스러운 마우스 이동 시간)
        # tween: easeInOutQuad (가속-감속 곡선, 사람의 움직임과 유사)
        duration = random.uniform(0.3, 0.7)
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
        
        # 클릭 전 짧은 멈춤 (사람이 목표를 확인하는 시간)
        time.sleep(random.uniform(0.05, 0.15))
        
        # 클릭
        pyautogui.click()
        
        # 클릭 후 약간 대기 (페이지 반응 대기)
        time.sleep(random.uniform(0.1, 0.2))
        
    except Exception as e:
        print(f"Mouse movement error: {e}")


# Backward compatibility - click_and_restore is now just human_click
click_and_restore = human_click


def human_type(text: str):
    """
    사람처럼 자연스러운 타이핑 (각 글자마다 랜덤 딜레이)
    
    Args:
        text: 입력할 텍스트
    """
    import time
    import random
    
    for char in text:
        pyautogui.write(char)
        # 사람의 타이핑 속도는 보통 200-400ms per character
        # 빠른 타이퍼는 80-150ms, 느린 타이퍼는 250-400ms
        # 중간 정도의 타이핑 속도로 설정
        time.sleep(random.uniform(0.08, 0.25))

# -----------------------------------------------------------------------------
# VLM 설정
# -----------------------------------------------------------------------------
USE_PROVIDER = "LM_STUDIO"  # "LM_STUDIO" 또는 "GROQ"

LM_STUDIO_CONFIG = {
    "URL": "http://localhost:12345/v1/chat/completions",
    "MODEL": "local-model",
    "API_KEY": "lm-studio"
}

GROQ_CONFIG = {
    "URL": "https://api.groq.com/openai/v1/chat/completions",
    "MODEL": "meta-llama/llama-4-scout-17b-16e-instruct",
    "API_KEY": os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE").strip()
}


def encode_image_to_base64(image):
    """이미지를 base64 문자열로 인코딩"""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def get_vlm_config():
    """현재 설정된 VLM 제공자 정보 반환"""
    if USE_PROVIDER == "GROQ":
        return {
            "url": GROQ_CONFIG["URL"],
            "model": GROQ_CONFIG["MODEL"],
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_CONFIG['API_KEY']}"
            }
        }
    else:
        return {
            "url": LM_STUDIO_CONFIG["URL"],
            "model": LM_STUDIO_CONFIG["MODEL"],
            "headers": {"Content-Type": "application/json"}
        }


def call_vlm(prompt: str, base64_image: str, max_tokens: int = 150, temperature: float = 0.0) -> dict:
    """
    VLM API 호출
    
    Args:
        prompt: 텍스트 프롬프트
        base64_image: base64 인코딩된 이미지
        max_tokens: 최대 토큰 수
        temperature: 응답 다양성 (0.0 = 결정적)
    
    Returns:
        파싱된 JSON 응답 또는 빈 딕셔너리
    """
    config = get_vlm_config()
    
    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": "You are a JSON API. Output ONLY valid JSON. Never include explanations, markdown, or code blocks."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(config["url"], headers=config["headers"], json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"VLM Error: {response.status_code}")
            print(f"Response: {response.text}")
            return {}
        
        content = response.json()['choices'][0]['message']['content']
        print(f">> VLM Raw Response: {content[:300]}")
        
        # JSON 정리 및 파싱
        clean_content = re.sub(r'```json\s*', '', content)
        clean_content = re.sub(r'```', '', clean_content)
        return json.loads(clean_content)
        
    except Exception as e:
        print(f"VLM Error: {e}")
        return {}


def capture_screen(mon_x: int, mon_y: int, mon_w: int, mon_h: int):
    """화면 영역 캡처"""
    bbox = (mon_x, mon_y, mon_x + mon_w, mon_y + mon_h)
    return ImageGrab.grab(bbox)
