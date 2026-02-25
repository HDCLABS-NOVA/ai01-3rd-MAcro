"""
tray.py - 시스템 트레이 아이콘 모듈
"""

import threading
import pystray
from PIL import Image, ImageDraw


def create_icon_image(color: str = "#4f46e5") -> Image.Image:
    """트레이 아이콘 이미지 생성 (64x64 원형)"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=color, outline="white", width=2)
    draw.text((20, 20), "M", fill="white")
    return img


def create_tray(on_exit_callback):
    """
    시스템 트레이 아이콘을 생성하고 백그라운드에서 실행합니다.
    on_exit_callback: 종료 버튼 클릭 시 호출될 함수
    """
    icon_image = create_icon_image()

    menu = pystray.Menu(
        pystray.MenuItem("🎯 매크로 실행 중", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("F2: 자동 탐색", None, enabled=False),
        pystray.MenuItem("F3: 앞좌석 우선", None, enabled=False),
        pystray.MenuItem("F4: 종료", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ 종료", lambda icon, item: _do_exit(icon, on_exit_callback)),
    )

    icon = pystray.Icon("macro", icon_image, "티켓 매크로", menu)

    # 백그라운드 스레드로 트레이 실행
    t = threading.Thread(target=icon.run, daemon=True)
    t.start()

    return icon


def _do_exit(icon, callback):
    icon.stop()
    callback()
