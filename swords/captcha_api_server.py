"""
🔐 CAPTCHA API Server
Provides HTTP API endpoint for CAPTCHA solving using VLM
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import base64
from io import BytesIO
from PIL import Image
import pyautogui
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.vlm_handler import call_vlm, encode_image_to_base64, human_click, human_type

app = FastAPI(title="CAPTCHA Solver API")

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CaptchaRequest(BaseModel):
    """Request to solve CAPTCHA from screenshot"""
    screenshot: str  # base64 encoded image (optional)
    use_screen_capture: bool = True  # If true, capture screen automatically

class CaptchaResponse(BaseModel):
    """Response with CAPTCHA solution"""
    success: bool
    text: str = ""
    message: str = ""

@app.get("/")
async def root():
    return {
        "service": "CAPTCHA Solver API",
        "status": "running",
        "endpoints": {
            "/solve": "POST - Solve CAPTCHA",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/solve", response_model=CaptchaResponse)
async def solve_captcha(request: CaptchaRequest):
    """
    Solve CAPTCHA using VLM
    
    If use_screen_capture=true: Captures current screen
    If screenshot provided: Uses provided base64 image
    """
    try:
        # Get screenshot
        if request.use_screen_capture:
            screenshot = pyautogui.screenshot()
        elif request.screenshot:
            # Decode base64 image
            img_data = base64.b64decode(request.screenshot)
            screenshot = Image.open(BytesIO(img_data))
        else:
            raise HTTPException(status_code=400, detail="No screenshot provided")
        
        width, height = screenshot.size
        base64_image = encode_image_to_base64(screenshot)
        
        # VLM Prompt for CAPTCHA detection
        prompt = f"""Screenshot size: {width}x{height} pixels.

Look for a CAPTCHA popup with:
- Distorted text/characters (usually 6 characters)
- Input field with placeholder "문자 입력" or similar
- Green/teal background typical of CAPTCHAs

Tasks:
1. Extract the CAPTCHA text
2. Find the center coordinates (normalized 0.0-1.0) of the input field

Return JSON only:
{{"type":"CAPTCHA", "text":"ABCDEF", "x":0.5, "y":0.6}}

If no CAPTCHA visible:
{{"type":"NONE"}}"""

        result = call_vlm(prompt, base64_image, max_tokens=100)
        
        if not result:
            return CaptchaResponse(
                success=False,
                message="VLM failed to process image"
            )
        
        p_type = result.get("type", "NONE").upper()
        
        if p_type == "NONE":
            return CaptchaResponse(
                success=False,
                message="No CAPTCHA detected"
            )
        
        if p_type == "CAPTCHA":
            captcha_text = result.get("text", "")
            raw_x = float(result.get("x", 0))
            raw_y = float(result.get("y", 0))
            
            # Normalize coordinates if needed
            if raw_x > 1.0:
                raw_x /= width
            if raw_y > 1.0:
                raw_y /= height
            
            # Calculate absolute coordinates
            abs_x = int(raw_x * width)
            abs_y = int(raw_y * height)
            
            # Clean CAPTCHA text
            captcha_clean = "".join(c for c in captcha_text if c.isalnum()).upper()
            
            if not captcha_clean:
                return CaptchaResponse(
                    success=False,
                    message="Invalid CAPTCHA text extracted"
                )
            
            # Auto-solve: Click and type
            print(f"[CAPTCHA API] Detected: {captcha_clean} at ({abs_x}, {abs_y})")
            
            # Use human-like movements
            human_click(abs_x, abs_y)
            time.sleep(0.2)
            
            # Type character by character
            human_type(captcha_clean)
            time.sleep(0.2)
            
            # Press Enter
            pyautogui.press('enter')
            
            return CaptchaResponse(
                success=True,
                text=captcha_clean,
                message=f"CAPTCHA '{captcha_clean}' solved successfully"
            )
        
        return CaptchaResponse(
            success=False,
            message=f"Unknown response type: {p_type}"
        )
        
    except Exception as e:
        print(f"[CAPTCHA API] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def start_server(port=5000):
    """Start the API server"""
    print("=" * 60)
    print("🔐 CAPTCHA API Server")
    print("=" * 60)
    print(f"Starting on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  POST http://localhost:{port}/solve - Solve CAPTCHA")
    print(f"  GET  http://localhost:{port}/health - Health check")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    start_server(port=5000)
