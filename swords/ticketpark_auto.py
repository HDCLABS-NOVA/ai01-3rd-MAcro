"""
🎫 TicketPark VLM Automation
Standalone application to detect and solve CAPTCHAs, enter performances, and select date/time using VLM.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import pyautogui

# Add current directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.popup_watcher import PopupWatcher
from modules import vlm_handler
from modules.vlm_handler import encode_image_to_base64, call_vlm, capture_screen, click_and_restore, human_type

class TicketParkWatcher(PopupWatcher):
    """
    Watcher that handles:
    1. CAPTCHA (Always active if detected)
    2. Auto Enter Performance (Optional)
    3. Auto Date/Time Selection (Optional)
    """
    def __init__(self, callback):
        super().__init__(callback)
        self.enable_auto_enter = False
        self.enable_date_time = False
        
        # CAPTCHA retry tracking
        self.captcha_attempt_count = 0
        self.last_captcha_text = None

    def _detect_and_handle_popup(self):
        """Override to handle multiple tasks"""
        # Capture screen
        screenshot = capture_screen(self.mon_x, self.mon_y, self.mon_w, self.mon_h)
        width, height = screenshot.size
        base64_image = encode_image_to_base64(screenshot)
        
        # Comprehensive Prompt
        prompt = f"""Screenshot size: {width}x{height} pixels.

Analyze the screen for the following elements. Priority: CAPTCHA > Performance Icons > Date/Time Modal.

**IMPORTANT: ALL coordinates must be NORMALIZED (0.0-1.0 range), NOT pixel values!**
Example: If an element is at pixel (960, 540) on a 1920x1080 screen, return x=0.5, y=0.5

1. **CAPTCHA**: 
   - At the top: distorted/striped CAPTCHA image with 6 letters (like "MJTAFS")
   - To the RIGHT of CAPTCHA image: Blue circular refresh icon (회오리 아이콘) - can be clicked to get new CAPTCHA
   - In the middle: EMPTY WHITE INPUT BOX with gray placeholder "문자 입력" - THIS IS YOUR INPUT TARGET!
   - At the bottom: Purple "확인" button
   - The INPUT BOX is located DIRECTLY ABOVE the purple "확인" button (just a small gap between them)
   - DO NOT target the striped CAPTCHA image at the top!
   - READ the 6 letters from the CAPTCHA image, but return coordinates for BOTH the INPUT BOX and REFRESH BUTTON
   - Return input_x, input_y = CENTER of the WHITE INPUT BOX, NORMALIZED 0-1
   - Return refresh_x, refresh_y = CENTER of the BLUE REFRESH ICON (to the right of CAPTCHA image), NORMALIZED 0-1

2. **Performance Icons**: Colorful rectangular icons/cards for shows/concerts (like theater masks, music notes, emoji-style icons)
   - Return NORMALIZED coordinates (0-1) for ALL detected icons (up to 5)
   - These are usually on the main page before entering a specific show

3. **Date/Time Modal**: A popup/modal with title "뮤지컬 <숏는날자>" or similar at the top.
   - **Layout**: 
     * Top section: "날짜 선택" label with 2 date buttons (white rounded rectangles with dates like "2026-02-01")
     * Middle section: "시간 선택" label with 2 time buttons (white rounded rectangles with times like "14:00", "19:30")
     * Bottom section: Large gray button "예매하기" (Reserve button)
   - **What to detect**:
     * date_x, date_y: CENTER of the FIRST date button (under "날짜 선택")
     * time_x, time_y: CENTER of the FIRST time button (under "시간 선택")
     * reserve_x, reserve_y: CENTER of the large gray "예매하기" button at the bottom
   - **IMPORTANT**: Return NORMALIZED coordinates (0.0-1.0) with 3 decimal places
   - Be precise! The buttons are small, so accuracy is critical.

4. **Timeout Alert**: A popup/alert with message like "시간이 초과되었습니다" or "다시 시도해주세요"
   - Look for a "확인" (OK/Confirm) button
   - Return NORMALIZED coordinates (0-1) for the confirm button

RETURN JSON ONLY. Choose ONE best action.

Type "CAPTCHA":
{{"type":"CAPTCHA", "text":"6CHARS", "input_x":0.xxx, "input_y":0.xxx, "refresh_x":0.xxx, "refresh_y":0.xxx}} 

Type "PERFORMANCE_ICONS":
{{"type":"PERFORMANCE_ICONS", "icons":[{{"x":0.xxx, "y":0.xxx}}, {{"x":0.xxx, "y":0.xxx}}]}}

Type "DATE_TIME":
{{"type":"DATE_TIME", "date_x":0.xxx, "date_y":0.xxx, "time_x":0.xxx, "time_y":0.xxx, "reserve_x":0.xxx, "reserve_y":0.xxx}}

Type "TIMEOUT_ALERT":
{{"type":"TIMEOUT_ALERT", "confirm_x":0.xxx, "confirm_y":0.xxx}}

Type "NONE":
{{"type":"NONE"}}"""

        result = call_vlm(prompt, base64_image, max_tokens=300)
        
        if not result:
            return False
            
        p_type = result.get("type", "NONE").upper()
        
        # 1. CAPTCHA (Highest Priority) - with refresh and retry logic
        if p_type == "CAPTCHA":
             p_text = result.get("text", "")
             input_x = float(result.get("input_x", 0))
             input_y = float(result.get("input_y", 0))
             refresh_x = float(result.get("refresh_x", 0))
             refresh_y = float(result.get("refresh_y", 0))
             
             # Validate CAPTCHA format: exactly 6 uppercase letters
             captcha_str = "".join(e for e in p_text if e.isalnum()).upper()
             
             # Helper function to click refresh button
             def click_refresh():
                 if refresh_x > 0 and refresh_y > 0:
                     # Convert coordinates
                     ref_x = refresh_x if refresh_x <= 1.0 else refresh_x / width
                     ref_y = refresh_y if refresh_y <= 1.0 else refresh_y / height
                     abs_ref_x = self.mon_x + int(ref_x * width)
                     abs_ref_y = self.mon_y + int(ref_y * height)
                     
                     self.update_status(f"🔄 Clicking CAPTCHA refresh button ({abs_ref_x},{abs_ref_y})")
                     click_and_restore(abs_ref_x, abs_ref_y)
                     time.sleep(1.0)  # Wait for new CAPTCHA to load
                     self.captcha_attempt_count = 0
                     self.last_captcha_text = None
                     return True
                 return False
             
             # Case 1: Invalid length (< 6 or > 6) - refresh immediately
             if len(captcha_str) != 6:
                 self.update_status(f"⚠️ Invalid CAPTCHA length ({len(captcha_str)}): '{p_text}' -> '{captcha_str}'")
                 if click_refresh():
                     return True
                 else:
                     self.update_status("❌ No refresh button detected, skipping...")
                     return False
             
             # Case 2: Valid length but not alphabetic
             if not captcha_str.isalpha():
                 self.update_status(f"⚠️ CAPTCHA contains non-letters: '{captcha_str}'")
                 if click_refresh():
                     return True
                 return False
             
             # Case 3: Check retry counter for same CAPTCHA
             if captcha_str == self.last_captcha_text:
                 self.captcha_attempt_count += 1
                 self.update_status(f"⚠️ Same CAPTCHA '{captcha_str}' - Attempt {self.captcha_attempt_count}/3")
                 
                 if self.captcha_attempt_count >= 3:
                     self.update_status(f"❌ Failed 3 times on '{captcha_str}', refreshing...")
                     if click_refresh():
                         return True
                     return False
             else:
                 # New CAPTCHA text
                 self.captcha_attempt_count = 1
                 self.last_captcha_text = captcha_str
             
             # Case 4: Validate coordinates (DISABLED - using hardcoded position)
             # if not (0.1 < input_x < 0.9 and 0.1 < input_y < 0.9):
             #     self.update_status(f"⚠️ Invalid input coordinates: ({input_x:.3f},{input_y:.3f})")
             #     return False
             
             # Convert coordinates (DISABLED - using hardcoded position)
             # if input_x > 1.0: input_x /= width
             # if input_y > 1.0: input_y /= height
             # 
             # abs_x = self.mon_x + int(input_x * width)
             # abs_y = self.mon_y + int(input_y * height)
             
             # Hardcoded position for CAPTCHA input field
             abs_x = 755
             abs_y = 755
             
             self.update_status(f"🔐 CAPTCHA DETECTED: '{captcha_str}' (Hardcoded Click: {abs_x}, {abs_y})")
             
             click_and_restore(abs_x, abs_y)
             time.sleep(0.2)
             human_type(captcha_str)
             time.sleep(0.2)
             pyautogui.press('enter')
             return True
        elif p_type == "CAPTCHA":
             # Invalid CAPTCHA format, already handled above
             self.update_status(f"⚠️ Skipping invalid CAPTCHA")
             return False

        # 2. Date/Time Selection (If Enabled)
        elif p_type == "DATE_TIME" and self.enable_date_time:
            # Simple logic: Click Date -> Wait -> Click Time -> Wait -> Click Reserve
            try:
                d_x = float(result.get("date_x", 0))
                d_y = float(result.get("date_y", 0))
                t_x = float(result.get("time_x", 0))
                t_y = float(result.get("time_y", 0))
                r_x = float(result.get("reserve_x", 0))
                r_y = float(result.get("reserve_y", 0))

                if d_x > 0 and t_x > 0 and r_x > 0:
                     self.update_status("📅 Auto Date/Time Selection detected")
                     self.update_status(f"   Normalized: date=({d_x:.3f},{d_y:.3f}) time=({t_x:.3f},{t_y:.3f}) reserve=({r_x:.3f},{r_y:.3f})")
                     
                     if d_x > 1.0: d_x /= width
                     if d_y > 1.0: d_y /= height
                     abs_d_x = self.mon_x + int(d_x * width)
                     abs_d_y = self.mon_y + int(d_y * height)

                     if t_x > 1.0: t_x /= width
                     if t_y > 1.0: t_y /= height
                     abs_t_x = self.mon_x + int(t_x * width)
                     abs_t_y = self.mon_y + int(t_y * height)

                     if r_x > 1.0: r_x /= width
                     if r_y > 1.0: r_y /= height
                     abs_r_x = self.mon_x + int(r_x * width)
                     abs_r_y = self.mon_y + int(r_y * height)

                     # Sequence
                     self.update_status(f"  -> Selecting Date ({abs_d_x},{abs_d_y})")
                     click_and_restore(abs_d_x, abs_d_y)
                     time.sleep(0.5)

                     self.update_status(f"  -> Selecting Time ({abs_t_x},{abs_t_y})")
                     click_and_restore(abs_t_x, abs_t_y)
                     time.sleep(0.5)

                     self.update_status(f"  -> Clicking Reserve ({abs_r_x},{abs_r_y})")
                     click_and_restore(abs_r_x, abs_r_y)
                     return True
            except:
                pass


        # 3. Performance Icons (If Auto Enter Enabled)
        elif p_type == "PERFORMANCE_ICONS" and self.enable_auto_enter:
            try:
                import random
                icons = result.get("icons", [])
                if icons and len(icons) > 0:
                    # Pick random icon
                    selected_icon = random.choice(icons)
                    
                    raw_x = float(selected_icon.get("x", 0))
                    raw_y = float(selected_icon.get("y", 0))
                    
                    if raw_x > 1.0: raw_x /= width
                    if raw_y > 1.0: raw_y /= height
                    
                    abs_x = self.mon_x + int(raw_x * width)
                    abs_y = self.mon_y + int(raw_y * height)
                    
                    if raw_x > 0 and raw_y > 0:
                        idx = icons.index(selected_icon) + 1
                        self.update_status(f"🎭 Auto Enter: Clicking Icon {idx}/{len(icons)} at ({abs_x}, {abs_y})")
                        click_and_restore(abs_x, abs_y)
                        time.sleep(2.0)
                        return True
            except Exception as e:
                self.update_status(f"⚠️ Icon click error: {e}")
            
            return False

        # 4. Timeout Alert
        elif p_type == "TIMEOUT_ALERT":
            try:
                confirm_x = float(result.get("confirm_x", 0))
                confirm_y = float(result.get("confirm_y", 0))
                
                # Ignore if button is in lower half (likely CAPTCHA input, not timeout)
                if confirm_y > 0.4:
                    self.update_status(f"⚠️ Ignoring TIMEOUT_ALERT at y={confirm_y:.3f} (too low, likely CAPTCHA)")
                    return False
                
                if confirm_x > 0 and confirm_y > 0:
                    # Convert coordinates
                    if confirm_x > 1.0: confirm_x /= width
                    if confirm_y > 1.0: confirm_y /= height
                    
                    abs_x = self.mon_x + int(confirm_x * width)
                    abs_y = self.mon_y + int(confirm_y * height)
                    
                    self.update_status(f"⏱️ Timeout Alert - clicking OK ({abs_x},{abs_y})")
                    click_and_restore(abs_x, abs_y)
                    time.sleep(0.5)
                    return True
            except Exception as e:
                self.update_status(f"⚠️ Timeout alert error: {e}")
            
            return False

        return False


class TicketParkAutoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎫 TicketPark VLM Automation")
        self.root.geometry("600x550")
        self.root.resizable(False, False)
        
        # Dark theme colors
        self.colors = {
            'bg': '#1a1a2e',
            'card': '#16213e',
            'text': '#ffffff',
            'accent': '#e94560',
            'success': '#00ff88'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Initialize Custom Watcher
        self.watcher = TicketParkWatcher(callback=self.log_message)
        
        self._setup_ui()
        
    def _setup_ui(self):
        # Header
        header = tk.Label(self.root, 
            text="🎫 TicketPark VLM Auto",
            font=('Segoe UI', 18, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text'])
        header.pack(pady=15)
        
        # Controls Frame
        control_frame = tk.Frame(self.root, bg=self.colors['card'], padx=20, pady=20)
        control_frame.pack(fill='x', padx=20)
        
        # Options
        tk.Label(control_frame, text="Automation Options:", bg=self.colors['card'], fg=self.colors['text'], font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 10))

        self.var_auto_enter = tk.BooleanVar(value=False)
        self.cb_auto_enter = tk.Checkbutton(control_frame, 
            text="🎭 Auto Enter (Click Performance Icons)",
            variable=self.var_auto_enter,
            bg=self.colors['card'], fg=self.colors['text'], selectcolor='#000000',
            font=('Segoe UI', 10), activebackground=self.colors['card'], activeforeground=self.colors['text'],
            command=self._update_options)
        self.cb_auto_enter.pack(anchor='w')

        self.var_date_time = tk.BooleanVar(value=False)
        self.cb_date_time = tk.Checkbutton(control_frame, 
            text="📅 Auto Date/Time/Reserve (Modal)",
            variable=self.var_date_time,
            bg=self.colors['card'], fg=self.colors['text'], selectcolor='#000000',
            font=('Segoe UI', 10), activebackground=self.colors['card'], activeforeground=self.colors['text'],
            command=self._update_options)
        self.cb_date_time.pack(anchor='w', pady=(5, 15))


        # VLM Selector
        vlm_frame = tk.Frame(control_frame, bg=self.colors['card'])
        vlm_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(vlm_frame, text="Model:", bg=self.colors['card'], fg=self.colors['text']).pack(side='left')
        
        self.vlm_var = tk.StringVar(value="LM_STUDIO")
        self.vlm_combo = ttk.Combobox(vlm_frame, 
            textvariable=self.vlm_var, 
            values=["LM_STUDIO", "GROQ"],
            state="readonly",
            width=15)
        self.vlm_combo.pack(side='left', padx=10)
        self.vlm_combo.bind("<<ComboboxSelected>>", self._on_vlm_change)
        
        # Buttons
        self.start_btn = tk.Button(control_frame,
            text="▶ START Monitoring",
            command=self.toggle_monitoring,
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['success'],
            fg='#000000',
            width=20,
            relief='flat',
            cursor='hand2')
        self.start_btn.pack()
        
        # Log Area
        log_frame = tk.Frame(self.root, bg=self.colors['bg'])
        log_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(log_frame, text="Activity Log:", bg=self.colors['bg'], fg='#aaaaaa').pack(anchor='w')
        
        self.log_text = scrolledtext.ScrolledText(log_frame,
            height=12,
            bg='#000000',
            fg='#00ff00',
            font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True)
        
    def _update_options(self):
        self.watcher.enable_auto_enter = self.var_auto_enter.get()
        self.watcher.enable_date_time = self.var_date_time.get()
        self.log_message(f"Options Updated: Enter={self.watcher.enable_auto_enter}, DateTime={self.watcher.enable_date_time}")

    def _on_vlm_change(self, event=None):
        vlm_handler.USE_PROVIDER = self.vlm_var.get()
        self.log_message(f"Provider switched to: {self.vlm_var.get()}")

    def log_message(self, message):
        def _update():
            self.log_text.insert('end', f"> {message}\n")
            self.log_text.see('end')
        self.root.after(0, _update)
        
    def toggle_monitoring(self):
        if self.watcher.is_running:
            self.watcher.stop()
            self.start_btn.config(text="▶ START Monitoring", bg=self.colors['success'])
            self.log_message("Monitoring STOPPED.")
        else:
            # Sync options before starting
            self._update_options()
            vlm_handler.USE_PROVIDER = self.vlm_var.get()
            
            self.watcher.start()
            self.start_btn.config(text="⏹ STOP Monitoring", bg=self.colors['accent'])
            self.log_message("Monitoring STARTED...")
            self.log_message(f"Using Provider: {vlm_handler.USE_PROVIDER}")

def main():
    root = tk.Tk()
    app = TicketParkAutoApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
