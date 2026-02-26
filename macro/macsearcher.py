"""
macsearcher.py - 색상 기반 좌석 감지 & 자동 클릭 모듈

좌석맵의 '선택가능' 도트를 색상(HSV)으로 찾아 자동 클릭합니다.
이미지 템플릿 방식 대신 픽셀 색상 스캔을 사용합니다.
"""

import time
import logging
import pyautogui
import numpy as np
import cv2

# ─────────────────────────────────────────────
# 탐색할 좌석 색상 정의 (HSV 범위)
# 아래 값을 실제 화면 색상에 맞게 조정하세요
# ─────────────────────────────────────────────
SEAT_COLORS = {
    "프리미엄": {  # 보라/핑크 계열
        "lower": np.array([136, 139, 116]),
        "upper": np.array([156, 255, 255]),
    },
    "지정석": {   # 청록/민트 계열
        "lower": np.array([77, 195, 90]),
        "upper": np.array([97, 255, 255]),
    },
    "자유석": {   # 노란/주황 계열
        "lower": np.array([7, 162, 187]),
        "upper": np.array([27, 255, 255]),
    },
    "전체": {     # 위 3가지 합쳐서 모든 선택가능 좌석 탐색
    
        "lower": None,
        "upper": None,
    },
}

# 클릭할 대상 (기본: 전체 선택가능 좌석)
TARGET_GRADES = ["프리미엄", "지정석", "자유석"]

# 설정
RETRY_INTERVAL = 0.3     # 재시도 간격 (초)
CLICK_DELAY    = 0.03    # 클릭 후 대기 (초) — 최소값
MIN_DOT_AREA   = 50      # 픽셀 면적 최솟값 (너무 작은 노이즈 제거)
MAX_DOT_AREA   = 600     # 픽셀 면적 최댓값 (좌석 도트 크기 기준)
SCREEN_Y_MIN   = 250     # 화면 상단 제외 (브라우저 탭바 + 페이지 헤더/내비게이션)
SCREEN_X_MIN   = 50      # 화면 좌측 하단 제외 (수직 스크롤바 외)

pyautogui.FAILSAFE = True

log = logging.getLogger("macsearcher")


def capture_screen() -> np.ndarray:
    """현재 화면을 캡처해 BGR numpy 배열로 반환"""
    screenshot = pyautogui.screenshot()
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)


def _get_dpi_scale() -> tuple[float, float]:
    """
    Windows DPI 스케일 팩터 반환.
    pyautogui.screenshot() → 물리적 픽셀
    pydirectinput.moveTo() → 논리적(OS) 좌표
    125% DPI에서 예) 물리 1920×1080 → 논리 1536×864 → scale=(0.8, 0.8)
    """
    logical_w, logical_h = pyautogui.size()           # 논리 해상도
    screenshot = pyautogui.screenshot()
    phys_w, phys_h = screenshot.size                  # 물리 해상도
    sx = logical_w / phys_w if phys_w > 0 else 1.0
    sy = logical_h / phys_h if phys_h > 0 else 1.0
    return sx, sy


def find_seats_by_color(screen_bgr: np.ndarray, grade: str = "전체") -> list[tuple]:
    """
    화면에서 특정 등급의 선택가능 좌석 도트를 찾아 중심좌표 목록 반환.
    반환: [(x, y), ...] — 위쪽(앞줄)부터 정렬
    """
    hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)
    combined_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)

    grades_to_check = TARGET_GRADES if grade == "전체" else [grade]

    for g in grades_to_check:
        info = SEAT_COLORS.get(g)
        if info is None or info["lower"] is None:
            continue
        mask = cv2.inRange(hsv, info["lower"], info["upper"])
        combined_mask = cv2.bitwise_or(combined_mask, mask)

    # 노이즈 제거
    kernel = np.ones((3, 3), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)

    # 컨투어로 개별 도트 감지
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    seats = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if MIN_DOT_AREA <= area <= MAX_DOT_AREA:
            # 원형도 필터: 좌석 도트는 원형 또는 사각형(border-radius)
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            if circularity < 0.3:  # 직사각형 UI 요소 제외
                continue

            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                # 화면 상단/좌측 (Chrome 탭바·툴바) 영역 제외
                if cy >= SCREEN_Y_MIN and cx >= SCREEN_X_MIN:
                    seats.append((cx, cy))

    # 위쪽(앞줄) → 아래쪽, 같은 줄이면 왼쪽 우선 정렬
    seats.sort(key=lambda p: (p[1], p[0]))

    log.debug(f"'{grade}' 좌석 감지: {len(seats)}개")
    return seats


def click_at(x: int, y: int):
    """좌석 클릭 — pydirectinput (Chrome에서도 동작하는 DirectInput)"""
    import pydirectinput
    ox = np.random.randint(-1, 2)
    oy = np.random.randint(-1, 2)
    tx, ty = x + ox, y + oy
    pydirectinput.moveTo(tx, ty)
    time.sleep(0.01)
    pydirectinput.click()
    time.sleep(CLICK_DELAY)
    log.info(f"클릭: ({tx}, {ty})")


def _move_to_confirm_button():
    """좌석 선택 후 [선택 완료] 또는 팝업 [확인] 버튼으로 마우스를 이동한다.
    - [선택 완료] : 우측 패널 (화면 X 65% 이후)
    - 팝업 [확인] : 화면 중앙 (알림 모달)
    두 버튼 모두 #667eea (파란색) — 화면 어디에 있든 파란 직사각형을 찾음.
    최대 8회 × 0.4초 = 3.2초 재시도
    """
    import pydirectinput
    import os

    # ── DPI 스케일 보정 ────────────────────────────────────────────────
    # pyautogui.screenshot() = 물리적 픽셀 기준
    # pydirectinput.moveTo() = 논리적(OS) 좌표 기준
    # Windows 125% DPI면 물리→논리 비율 = 0.8
    sx, sy = _get_dpi_scale()
    log.debug(f"DPI 스케일: sx={sx:.3f}, sy={sy:.3f}")

    # #667eea HSV: H=114, S=144, V=234
    # V 하한을 80으로 낮춰서 팝업 오버레이 dimming 상황에도 대응
    LOWER = np.array([ 95, 40,  80])
    UPPER = np.array([140, 255, 255])

    MAX_TRIES = 20   # 20 × 0.05s = 최대 1초 탐색
    WAIT_EACH = 0.0  # 즉시 캡처 (딜레이 없음)

    def _find_button_in_region(hsv_img, x_min_r, x_max_r, y_min_r, lower_hsv, upper_hsv):
        """지정 영역에서 파란 직사각형 버튼 탐색 → (cx_phys, cy_phys) or None"""
        h_img, w_img = hsv_img.shape[:2]
        msk = cv2.inRange(hsv_img, lower_hsv, upper_hsv)
        msk[:y_min_r, :]    = 0
        msk[:, :x_min_r]    = 0
        msk[:, x_max_r:]    = 0
        k = np.ones((15, 15), np.uint8)
        msk = cv2.morphologyEx(msk, cv2.MORPH_CLOSE, k)
        cnts, _ = cv2.findContours(msk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_c, best_a = None, 0
        for c in cnts:
            a = cv2.contourArea(c)
            if a < 2000:
                continue
            xr, yr, w, h = cv2.boundingRect(c)
            cx = xr + w // 2
            cy = yr + h // 2
            asp = w / h if h > 0 else 0
            # 버튼 조건: 가로>세로, 너비>=60, 높이>=30 (좌석 도트 클러스터 제거)
            if asp > 1.5 and w >= 60 and h >= 30 and a > best_a:
                best_c = (cx, cy)
                best_a = a
        return best_c, best_a

    for attempt in range(1, MAX_TRIES + 1):
        time.sleep(WAIT_EACH)

        screen = capture_screen()
        h_sc, w_sc = screen.shape[:2]
        hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

        y_nav = int(h_sc * 0.15)   # 상단 네비 제외

        # ── 1차: 우측 패널 [선택 완료] 버튼 (x > 65%) ───────────────────
        # 좌석맵은 x < 65%이므로 도트 오인식 없음
        x_panel = int(w_sc * 0.65)
        LO_PANEL = np.array([ 95, 40,  80])
        HI_PANEL = np.array([140, 255, 255])
        pos, area = _find_button_in_region(
            hsv, x_panel, int(w_sc * 0.98), y_nav, LO_PANEL, HI_PANEL
        )

        if pos:
            bx = int(pos[0] * sx)
            by = int(pos[1] * sy)
            log.info(f"🖱️ [선택 완료] 발견! phys=({pos[0]},{pos[1]}) → 논리=({bx},{by}) [{attempt}/{MAX_TRIES}회]")
            pydirectinput.moveTo(bx, by)
            return

        # ── 2차: 팝업 [확인] 버튼 (화면 중앙, V>=150) ────────────────────
        # 팝업 overlay(rgba 0,0,0,0.7)가 배경을 어둡게 함 → 배경 V<80
        # 팝업 버튼은 밝은 파란색 V≈234 → V>=150 조건으로 팝업만 잡음
        x_pop_l = int(w_sc * 0.25)
        x_pop_r = int(w_sc * 0.75)
        LO_POP  = np.array([ 95, 60, 150])
        HI_POP  = np.array([140, 255, 255])
        pos2, area2 = _find_button_in_region(
            hsv, x_pop_l, x_pop_r, y_nav, LO_POP, HI_POP
        )

        if pos2:
            bx = int(pos2[0] * sx)
            by = int(pos2[1] * sy)
            log.info(f"🖱️ 팝업 [확인] 발견! phys=({pos2[0]},{pos2[1]}) → 논리=({bx},{by}) [{attempt}/{MAX_TRIES}회]")
            pydirectinput.moveTo(bx, by)
            return

        log.info(f"[{attempt}/{MAX_TRIES}] 버튼 미발견 (화면 {w_sc}×{h_sc})")

    # ── 전부 실패 → 상세 디버그 이미지 2종 저장 ─────────────────────
    log.warning("⚠️ 버튼 끝내 못 찾음 → debug_confirm_btn.png / debug_mask.png 저장")
    out_dir = os.path.dirname(__file__)

    dbg = screen.copy()
    cv2.line(dbg, (x_left,  0),    (x_left,  h_sc), (0, 255, 0), 2)
    cv2.line(dbg, (x_right, 0),    (x_right, h_sc), (0, 255, 0), 2)
    cv2.line(dbg, (0, y_top), (w_sc, y_top),        (0, 255, 0), 2)
    cv2.imwrite(os.path.join(out_dir, "debug_confirm_btn.png"), dbg)

    # 색상 마스크 (흰 픽셀 = 파란색 감지됨)
    raw_mask = cv2.inRange(hsv, LOWER, UPPER)
    raw_mask[:y_top, :]   = 0
    raw_mask[:, :x_left]  = 0
    raw_mask[:, x_right:] = 0
    cv2.imwrite(os.path.join(out_dir, "debug_mask.png"), raw_mask)
    log.warning(f"   저장 완료: {out_dir}")



def search_and_click(grade: str = "전체", max_retries: int = 50, stop_flag: list = None) -> bool:
    """
    F2 모드: 선택가능한 첫 번째 좌석을 찾아 클릭.
    grade: "프리미엄" / "지정석" / "자유석" / "전체"
    """
    log.info(f"▶ 자동 탐색 시작 [대상: {grade}] (최대 {max_retries}회)")

    for attempt in range(1, max_retries + 1):
        if stop_flag and stop_flag[0]:
            log.info("탐색 중단")
            return False

        screen = capture_screen()
        seats = find_seats_by_color(screen, grade)

        if seats:
            x, y = seats[0]  # 가장 앞줄 왼쪽 좌석
            log.info(f"✅ 좌석 발견! ({x}, {y}) — {len(seats)}개 중 첫 번째 [{attempt}회 시도]")
            click_at(x, y)
            # 좌석 선택 후 [선택 완료] 버튼으로 마우스 이동
            _move_to_confirm_button()
            return True

        log.info(f"[{attempt}/{max_retries}] 미발견, {RETRY_INTERVAL}초 후 재시도...")
        time.sleep(RETRY_INTERVAL)

    log.warning("탐색 실패 (재시도 초과)")
    return False


def search_front_priority(max_retries: int = 50, stop_flag: list = None) -> bool:
    """
    F3 모드: 앞좌석 우선 탐색.
    프리미엄 → 지정석 → 자유석 순으로, 각 등급에서도 앞줄부터 탐색.
    """
    log.info(f"▶ 앞좌석 우선 탐색 시작 (최대 {max_retries}회)")

    for attempt in range(1, max_retries + 1):
        if stop_flag and stop_flag[0]:
            log.info("탐색 중단")
            return False

        screen = capture_screen()

        for grade in TARGET_GRADES:  # 프리미엄 → 지정석 → 자유석
            seats = find_seats_by_color(screen, grade)
            if seats:
                x, y = seats[0]
                log.info(f"✅ [{grade}] 앞좌석 발견! ({x}, {y}) [{attempt}회 시도]")
                click_at(x, y)
                _move_to_confirm_button()
                return True

        log.info(f"[{attempt}/{max_retries}] 미발견, {RETRY_INTERVAL}초 후 재시도...")
        time.sleep(RETRY_INTERVAL)

    log.warning("앞좌석 탐색 실패")
    return False


# ─────────────────────────────────────────────
# 디버그 모드: python macro/macsearcher.py 로 직접 실행
# → 감지된 좌석 위치를 빨간 원으로 표시한 이미지 저장
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import os
    import logging
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")

    print("📸 3초 후 화면 캡처... 이 시간 안에 예매 좌석 화면으로 이동하세요!")
    time.sleep(3)

    screen = capture_screen()
    all_seats = []

    for grade in TARGET_GRADES:
        seats = find_seats_by_color(screen, grade)
        print(f"  [{grade}] 감지: {len(seats)}개")
        all_seats.extend([(s, grade) for s in seats])

    # 감지된 좌석을 원으로 표시
    debug_img = screen.copy()
    colors_bgr = {
        "프리미엄": (0, 0, 255),   # 빨강
        "지정석":   (0, 165, 255), # 주황
        "자유석":   (0, 255, 0),   # 초록
    }
    for (x, y), grade in all_seats:
        color = colors_bgr.get(grade, (255, 0, 255))
        cv2.circle(debug_img, (x, y), 10, color, 2)
        cv2.putText(debug_img, grade[0], (x-4, y+4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # Y 제한선 표시
    cv2.line(debug_img, (0, SCREEN_Y_MIN), (debug_img.shape[1], SCREEN_Y_MIN), (255, 255, 0), 1)

    out_path = os.path.join(os.path.dirname(__file__), "debug_seats.png")
    cv2.imwrite(out_path, debug_img)
    print(f"\n✅ 디버그 이미지 저장: {out_path}")
    print(f"   총 감지: {len(all_seats)}개")
    if all_seats:
        first_x, first_y = all_seats[0][0]
        print(f"   첫 번째 클릭 예정 좌표: ({first_x}, {first_y})")
