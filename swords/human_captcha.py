"""
Human-like CAPTCHA Solver for New Site
Uses physical mouse and keyboard movements
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.vlm_handler import encode_image_to_base64, call_vlm, human_click, human_type
import pyautogui
import time
from PIL import ImageGrab

def solve_captcha_human():
    """Solve CAPTCHA using human-like mouse/keyboard movements"""
    print("=" * 60)
    print("👤 Human-like CAPTCHA Solver")
    print("=" * 60)
    
    print("\n📸 Capturing screen in 2 seconds...")
    print("   Switch to browser with CAPTCHA!")
    time.sleep(2)
    
    # Capture screen
    screenshot = pyautogui.screenshot()
    width, height = screenshot.size
    print(f"🖥️  Screen: {width}x{height}")
    
    base64_image = encode_image_to_base64(screenshot)
    
    # Ask VLM to read CAPTCHA
    prompt = """Look at this screenshot of a browser.

Find the CAPTCHA popup with:
- Green/teal background
- 6 white capital letters

Read the 6 letters exactly.

Return JSON:
{"text":"ABCDEF"}

If no CAPTCHA:
{"text":"NONE"}"""
    
    print("🔍 Analyzing with VLM...")
    result = call_vlm(prompt, base64_image, max_tokens=50)
    
    if not result:
        print("❌ VLM failed")
        return False
    
    text = result.get("text", "NONE")
    print(f"📝 VLM found: {text}")
    
    if text == "NONE" or len(text) != 6:
        print("❌ No valid CAPTCHA detected")
        return False
    
    captcha_text = text.upper()
    print(f"\n✅ CAPTCHA: {captcha_text}")
    
    # Calculate input field position (center of screen, slightly above middle)
    input_x = width // 2
    input_y = int(height * 0.55)
    
    print(f"\n🖱️  Moving mouse to input field...")
    print(f"   Target: ({input_x}, {input_y})")
    
    # Use human_click - physically moves mouse with curve!
    human_click(input_x, input_y)
    
    print(f"\n⌨️  Typing CAPTCHA character by character...")
    
    # Type each character with human-like delays
    for i, char in enumerate(captcha_text, 1):
        print(f"   [{i}/6] Typing: {char}")
        pyautogui.write(char)
        # Random delay between characters (80-250ms)
        import random
        time.sleep(random.uniform(0.08, 0.25))
    
    # Small pause before pressing Enter
    time.sleep(random.uniform(0.2, 0.4))
    
    print(f"\n↩️  Pressing Enter...")
    pyautogui.press('enter')
    
    print(f"\n🎉 CAPTCHA solved with human-like behavior!")
    print(f"   - Mouse moved smoothly with curve")
    print(f"   - Typed one character at a time")
    print(f"   - Random delays between actions")
    
    return True

if __name__ == "__main__":
    print("\n⚠️  준비사항:")
    print("  1. 브라우저에서 localhost 페이지 열기")
    print("  2. CAPTCHA 팝업이 보이도록 하기")
    print("  3. 마우스를 움직일 수 있도록 화면 끄지 않기")
    
    input("\n✅ 준비되면 Enter를 누르세요...")
    
    success = solve_captcha_human()
    
    if success:
        print("\n✨ 성공! 마우스가 움직이는 것을 보셨나요?")
    else:
        print("\n❌ 실패")
    
    input("\nEnter to exit...")
