"""
macpicker.py - 마우스 커서 위치의 화면 색상 실시간 확인 도구

실행 후 마우스를 좌석 위에 올리면 실시간으로 RGB/HSV 값을 출력합니다.
브라우저에 마우스가 있어도 전역으로 키 감지됩니다.
  C : 현재 색상 저장
  Q : 종료
"""

import time
import threading
import pyautogui
import numpy as np
import cv2
from pynput import keyboard

print("=" * 50)
print("  🎨 색상 피커 - 마우스를 좌석 위에 올려주세요")
print("  C : 현재 색상 저장  |  Q : 종료")
print("=" * 50)

saved = []
running = True


def get_pixel_color(x, y):
    screenshot = pyautogui.screenshot(region=(x - 1, y - 1, 3, 3))
    img = np.array(screenshot)
    rgb = tuple(int(v) for v in img[1, 1])
    bgr = np.array([[list(reversed(rgb))]], dtype=np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0][0]
    hsv = tuple(int(v) for v in hsv)
    return rgb, hsv


def save_current():
    x, y = pyautogui.position()
    rgb, hsv = get_pixel_color(x, y)
    saved.append({"pos": (x, y), "rgb": rgb, "hsv": hsv})
    print(f"\n\n💾 저장! RGB={rgb}  HSV={hsv}")
    print(f"   ▶ lower: np.array([{max(0, hsv[0]-10)}, {max(0, hsv[1]-60)}, {max(0, hsv[2]-60)}])")
    print(f"   ▶ upper: np.array([{min(179, hsv[0]+10)}, 255, 255])\n")


def on_press(key):
    global running
    try:
        if key.char == 'c':
            save_current()
        elif key.char == 'q':
            running = False
            return False  # 리스너 종료
    except AttributeError:
        pass


# 전역 키 리스너 시작 (백그라운드)
listener = keyboard.Listener(on_press=on_press)
listener.start()

try:
    while running:
        x, y = pyautogui.position()
        try:
            rgb, hsv = get_pixel_color(x, y)
            print(f"\r  pos=({x:4d},{y:4d})  RGB={rgb}  HSV={hsv}   ", end="", flush=True)
        except Exception:
            pass
        time.sleep(0.05)
except KeyboardInterrupt:
    pass

listener.stop()
print("\n\n종료됨")
if saved:
    print(f"\n총 {len(saved)}개 저장:")
    for i, s in enumerate(saved, 1):
        print(f"  {i}. pos={s['pos']}  RGB={s['rgb']}  HSV={s['hsv']}")
else:
    print("저장된 색상 없음")
