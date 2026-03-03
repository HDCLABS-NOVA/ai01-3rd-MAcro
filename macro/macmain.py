"""
macmain.py - 티켓 매크로 메인 실행 파일

단축키 (pynput 글로벌 감지 — Chrome 포커스 상태에서도 동작):
  F2: 자동 좌석 탐색
  F3: 앞좌석 우선 탐색
  F4: 종료

사용법:
  1. 예매 페이지에서 좌석 선택 화면 진입
  2. python macro/macmain.py 실행
  3. F2 또는 F3 눌러 탐색 시작
"""

import sys
import os
import time
import threading
import logging

# pythonw 환경(터미널 없음)에서 stdout/stderr가 None일 경우 안전하게 처리
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
from pynput import keyboard as pynput_keyboard

# 경로 설정
sys.path.insert(0, os.path.dirname(__file__))

from macsearcher import search_and_click, search_front_priority
from mactray import create_tray

# 로그 설정
# 로그 파일 경로 (macmain.py 옆에 저장)
_log_file = os.path.join(os.path.dirname(__file__), "macro.log")
_handlers = [logging.FileHandler(_log_file, encoding="utf-8")]
try:
    if sys.stdout and sys.stdout.fileno() >= 0:
        _handlers.append(logging.StreamHandler(sys.stdout))
except Exception:
    pass
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    handlers=_handlers
)
log = logging.getLogger("main")

# 기본 탐색 이미지 파일명
DEFAULT_TEMPLATE = "ti.jpg"

# 상태
_running = [False]   # 현재 탐색 중 여부
_stop_flag = [False] # 탐색 중단 신호
_exit_flag = [False] # 프로그램 종료 신호


def on_exit():
    """종료 처리"""
    log.info("매크로 종료")
    _exit_flag[0] = True
    _stop_flag[0] = True
    sys.exit(0)


def run_search(mode: str = "auto"):
    """탐색 실행 (별도 스레드에서 호출)"""
    if _running[0]:
        log.warning("이미 탐색 중입니다. F4로 중단 후 재시도하세요.")
        return

    _running[0] = True
    _stop_flag[0] = False

    log.info(f"{'='*40}")
    log.info(f"▶ 탐색 시작 - 모드: {'자동(F2)' if mode == 'auto' else '앞좌석 우선(F3)'}")
    log.info(f"{'='*40}")

    try:
        success = False
        if mode == "auto":
            success = search_and_click("전체", max_retries=50, stop_flag=_stop_flag)
        elif mode == "front":
            success = search_front_priority(max_retries=50, stop_flag=_stop_flag)

        if success:
            log.info("✅ 좌석 선택 성공!")
        else:
            log.warning("❌ 탐색 실패 또는 중단됨")
    except Exception as e:
        log.error(f"탐색 중 오류: {e}")
    finally:
        _running[0] = False


def on_f2():
    """F2: 자동 좌석 탐색"""
    log.info("F2 입력 감지 → 자동 탐색 시작")
    t = threading.Thread(target=run_search, args=("auto",), daemon=True)
    t.start()


def on_f3():
    """F3: 앞좌석 우선 탐색"""
    log.info("F3 입력 감지 → 앞좌석 우선 탐색 시작")
    t = threading.Thread(target=run_search, args=("front",), daemon=True)
    t.start()


def on_f4():
    """F4: 종료"""
    log.info("F4 입력 감지 → 종료")
    on_exit()


def _on_key_press(key):
    """pynput 키 감지 콜백"""
    try:
        if key == pynput_keyboard.Key.f2:
            on_f2()
        elif key == pynput_keyboard.Key.f3:
            on_f3()
        elif key == pynput_keyboard.Key.f4:
            on_f4()
    except AttributeError:
        pass


def main():
    log.info("=" * 40)
    log.info("  🎯 티켓 매크로 시작")
    log.info("  F2 : 자동 좌석 탐색")
    log.info("  F3 : 앞좌석 우선 탐색")
    log.info("  F4 : 종료")
    log.info("=" * 40)

    # assets 폴더 확인 (선택사항, 색상 감지 방식이므로 필수 아님)
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    if os.path.isdir(assets_dir):
        files = [f for f in os.listdir(assets_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if files:
            log.info(f"📁 assets 이미지: {files}")
    log.info("🎨 색상 감지 모드로 동작합니다")

    # 트레이 아이콘 시작
    try:
        create_tray(on_exit_callback=on_exit)
        log.info("✅ 트레이 아이콘 활성화 (우하단 확인)")
    except Exception as e:
        log.warning(f"트레이 아이콘 실패 (무시하고 계속): {e}")

    log.info("대기 중... (F2/F3으로 탐색, F4로 종료)")

    # pynput 글로벌 키 리스너 시작 (Chrome 포커스 상태에서도 감지)
    with pynput_keyboard.Listener(on_press=_on_key_press) as listener:
        while not _exit_flag[0]:
            time.sleep(0.1)
        listener.stop()


if __name__ == "__main__":
    main()
