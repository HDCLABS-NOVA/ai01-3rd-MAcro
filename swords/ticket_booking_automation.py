"""
티켓 예매 자동화 스크립트 (Playwright)
http://localhost:5000에서 티켓을 자동으로 예매합니다.

사용법:
    python ticket_booking_automation.py
    python ticket_booking_automation.py --headless
    python ticket_booking_automation.py --email user@test.com --password 12345678
    python ticket_booking_automation.py --once  # 1회만 실행

필요 패키지:
    pip install playwright
    playwright install chromium

종료:
    Ctrl+C 로 종료
"""

from playwright.sync_api import (
    sync_playwright,
    Page,
    expect,
    TimeoutError as PlaywrightTimeoutError,
)
import time
from typing import Optional, Dict, Any
import signal
import sys
import random
import argparse
import re
import json
import logging
from pathlib import Path
import os
from datetime import datetime


def setup_logger(log_dir: str = "logs") -> logging.Logger:
    """로깅 설정

    Args:
        log_dir: 로그 파일 저장 디렉토리

    Returns:
        설정된 로거
    """
    # 로그 디렉토리 생성
    Path(log_dir).mkdir(exist_ok=True)

    # 로거 생성
    logger = logging.getLogger("TicketBot")
    logger.setLevel(logging.INFO)

    # 이미 핸들러가 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()

    # 파일 핸들러 (JSON 형식)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"booking_log_{timestamp}.json"

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)

    # 로그 파일 경로 저장
    logger.log_file = log_file
    logger.session_logs = []  # JSON 로그 저장용

    return logger


class TicketBookingBot:
    """티켓 예매 자동화 봇"""

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        headless: bool = False,
        login_email: str = "test1@email.com",
        login_password: str = "11111111",
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            base_url: 티켓 예매 사이트 URL
            headless: 헤드리스 모드 실행 여부
            login_email: 로그인 이메일
            login_password: 로그인 비밀번호
            logger: 로거 인스턴스 (없으면 기본 로거 생성)
        """
        self.base_url = base_url
        self.headless = headless
        self.login_email = login_email
        self.login_password = login_password
        self.max_retries = 3
        self.default_timeout = 30000  # 30초
        self.logger = logger or setup_logger()

        # 통계 데이터
        self.stats = {
            "total_attempts": 0,
            "success_count": 0,
            "failure_count": 0,
            "errors": [],
        }

    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """이벤트 로그 기록

        Args:
            event_type: 이벤트 타입 (start, success, failure, error)
            data: 로그 데이터
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **data,
        }

        # 세션 로그에 추가
        if hasattr(self.logger, "session_logs"):
            self.logger.session_logs.append(log_entry)

        # JSON 파일에 저장
        if hasattr(self.logger, "log_file"):
            try:
                with open(self.logger.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception as e:
                self.logger.warning(f"로그 파일 저장 실패: {e}")

    def run_once(self, page: Page, browser_context, url: Optional[str] = None) -> bool:
        """티켓 예매 프로세스 1회 실행

        Args:
            page: Playwright 페이지 객체
            browser_context: 브라우저 컨텍스트
            url: 접속할 URL (생략 시 self.base_url 사용)

        Returns:
            성공 여부
        """
        start_time = time.time()
        booking_data = {}
        
        # 호출 시점의 URL이 있으면 그것을 사용, 없으면 초기화 시의 base_url 사용
        target_url = url or self.base_url

        try:
            self._log_event("attempt_start", {"url": target_url})

            # 1. 메인 페이지 접속
            # URL 뒤에 /html/index.html이 필요한지 판단
            main_url = f"{target_url.rstrip('/')}/html/index.html"
            print(f"📍 Step 1: 메인 페이지 접속 ({main_url})...")
            
            try:
                # 먼저 /html/index.html 시도
                response = page.goto(main_url, timeout=10000)
                if not response or response.status >= 400:
                    # 실패 시 /index.html로 재시도 (ngrok 등 환경 대응)
                    main_url = f"{target_url.rstrip('/')}/index.html"
                    print(f"ℹ️  경로 조정: {main_url} 로 접속 시도...")
                    page.goto(main_url, timeout=self.default_timeout)
                
                self._safe_wait_for_load(page)
            except PlaywrightTimeoutError:
                self.logger.error("❌ 메인 페이지 접속 타임아웃")
                self._log_event("error", {"step": 1, "error": "main_page_timeout"})
                return False
            except Exception as e:
                self.logger.error(f"❌ 메인 페이지 접속 실패: {e}")
                self._log_event("error", {"step": 1, "error": str(e)})
                return False

            # 2. 로그인 상태 확인 및 로그인 (최초 1회)
            print("📍 Step 2: 로그인 상태 확인...")
            is_logged_in = page.evaluate("""
                () => {
                    const user = sessionStorage.getItem('currentUser');
                    return user !== null;
                }
            """)

            if not is_logged_in:
                print("📍 Step 2-1: 로그인 필요 - 로그인 페이지로 이동...")
                # 현재 페이지 URL을 기반으로 로그인 페이지 경로 결정
                current_url = page.url
                if "/html/" in current_url:
                    login_url = f"{target_url.rstrip('/')}/html/login.html"
                else:
                    login_url = f"{target_url.rstrip('/')}/login.html"
                
                page.goto(login_url, timeout=self.default_timeout)
                self._safe_wait_for_load(page)

                if not self._login(page):
                    print("❌ 로그인 실패")
                    return False

                # 로그인 후 다시 메인 페이지로
                print("📍 Step 2-2: 로그인 완료 - 메인 페이지로 복귀...")
                if "/html/" in login_url:
                    page.goto(f"{target_url.rstrip('/')}/html/index.html", timeout=self.default_timeout)
                else:
                    page.goto(f"{target_url.rstrip('/')}/index.html", timeout=self.default_timeout)
                self._safe_wait_for_load(page)
            else:
                print("✅ 이미 로그인됨 - 계속 진행")

            # 3. 공연 선택 (랜덤 선택)
            print("📍 Step 3: 공연 선택...")
            try:
                page.wait_for_selector(".performance-card", state="visible", timeout=10000)
                cards = page.locator(".performance-card")
                cards_count = cards.count()
                
                if cards_count > 0:
                    random_idx = random.randint(0, cards_count - 1)
                    selector = f".performance-card:nth-child({random_idx + 1})"
                    
                    self._human_delay(0.8, 1.5)
                    self._human_move_and_click(page, selector, f"공연 #{random_idx + 1}")
                else:
                    return False
            except Exception as e:
                if "closed" not in str(e).lower():
                    print(f"❌ 공연 선택 중 오류: {e}")
                    return False
            
            self._human_delay(1.0, 2.0)
            self._safe_wait_for_load(page)

            # 4. 날짜 선택 (첫 번째 날짜)
            print("📍 Step 4: 날짜 선택...")
            self._human_delay(0.5, 1.0)
            if not self._human_move_and_click(page, ".date-btn", "날짜 버튼"):
                return False
            self._human_delay(0.5, 1.2)

            # 5. 시간 선택 (첫 번째 시간)
            print("📍 Step 5: 시간 선택...")
            if not self._human_move_and_click(page, ".time-btn", "시간 버튼"):
                return False
            self._human_delay(0.5, 1.0)

            # 6. 예매 시작 버튼 클릭
            print("📍 Step 6: 예매 시작...")
            # 실제 ID는 #start-booking-btn 임이 확인됨
            booking_selectors = ["#start-booking-btn", "button:has-text('예매 시작')", "text='예매 시작'"]
            success = False
            for sel in booking_selectors:
                if self._human_move_and_click(page, sel, "예매 시작 버튼"):
                    success = True
                    break
            
            if not success:
                print("❌ 예매 시작 버튼을 클릭할 수 없습니다.")
                return False
                
            self._human_delay(1.0, 2.0)
            self._safe_wait_for_load(page)

            # 7. 대기열 대기 (3-5초 자동 통과)
            print("📍 Step 7: 대기열 통과 대기...")
            time.sleep(6)  # 대기열 통과 대기

            # 8. 좌석 선택 페이지 진입 대기
            print("📍 Step 8: 좌석 선택 페이지 로딩...")
            time.sleep(2)  # 페이지 로드 및 CAPTCHA 팝업 대기

            # 9. CAPTCHA 처리 (좌석 선택 페이지의 팝업)
            print("📍 Step 9: CAPTCHA 처리...")
            self._handle_captcha(page)

            # 10. 좌석 선택 (VIP석 중 첫 번째 가능한 좌석)
            print("📍 Step 10: 좌석 선택...")
            seat_result = self._select_seat(page)
            if not seat_result:
                self.logger.error("❌ 좌석 선택 실패 - 가능한 좌석이 없습니다")
                self._log_event("error", {"step": 10, "error": "no_available_seats"})
                return False
            
            # 리스타트 신호 확인 (Undefined 등급 등)
            if seat_result.get("status") == "RESTART":
                print("🔄 유효하지 않은 좌석 상태로 인해 처음 화면으로 이동합니다.")
                return False

            # 선택된 좌석 정보 저장
            booking_data["selected_seat"] = seat_result

            # 11. 다음 단계 (좌석 선택 완료)
            print("📍 Step 11: 좌석 선택 완료...")
            self._human_delay(0.5, 1.5)
            if not self._click_next_button(page, "선택 완료"):
                return False
            self._safe_wait_for_load(page)

            # 12. 할인 선택 페이지에서 다음 단계
            print("📍 Step 12: 할인 단계 진행...")
            self._human_delay(1.0, 2.0)
            if not self._click_next_button(page, "다음 단계"):
                return False
            self._safe_wait_for_load(page)

            # 13. 예매자 정보 입력 및 결제하기
            print("📍 Step 13: 예매자 정보 입력...")
            self._human_delay(1.5, 3.0) # 정보 입력 전 생각하는 시간
            self._fill_booker_info(page)

            # 페이지 하단의 "결제하기" 버튼 클릭 (order_info.html)
            print("📍 Step 14: 결제하기 버튼 클릭 (예매자 정보 페이지)...")
            time.sleep(2)

            # 여러 방법으로 버튼 찾기 시도
            payment_btn_found = False

            # 방법 1: 텍스트로 찾기 (결제하기 또는 예매하기)
            try:
                # "결제하기" 또는 "예매하기" 텍스트를 포함하는 버튼 찾기
                payment_btn = page.get_by_role("button").filter(has_text=re.compile(r"결제하기|예매하기"))
                
                if payment_btn.count() > 0:
                    target_btn = payment_btn.first
                    if target_btn.is_visible(timeout=5000):
                        # 버튼으로 스크롤 (화면 하단에 있을 수 있음)
                        target_btn.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        target_btn.click(timeout=10000)
                        payment_btn_found = True
                        btn_text = target_btn.inner_text()
                        print(f"✅ '{btn_text}' 버튼 클릭 성공 (텍스트 매칭)")
            except Exception as e:
                print(f"⚠️  방법 1 실패: {e}")

            # 방법 2: CSS 셀렉터로 찾기
            if not payment_btn_found:
                try:
                    payment_btn = page.locator("button.btn-primary.btn-lg.btn-block")
                    if payment_btn.is_visible(timeout=5000):
                        payment_btn.click(timeout=10000)
                        payment_btn_found = True
                        print("✅ '결제하기' 버튼 클릭 성공 (CSS 셀렉터)")
                except Exception as e:
                    print(f"⚠️  방법 2 실패: {e}")

            # 방법 3: onclick 속성으로 찾기
            if not payment_btn_found:
                try:
                    payment_btn = page.locator("button[onclick='confirmOrderInfo()']")
                    if payment_btn.is_visible(timeout=5000):
                        payment_btn.click(timeout=10000)
                        payment_btn_found = True
                        print("✅ '결제하기' 버튼 클릭 성공 (onclick 속성)")
                except Exception as e:
                    print(f"⚠️  방법 3 실패: {e}")

            if not payment_btn_found:
                print("❌ '결제하기' 버튼을 찾을 수 없습니다.")
                return False

            self._safe_wait_for_load(page)

            # 14. 최종 결제 확인 (payment.html)
            print("📍 Step 15: 최종 결제 페이지...")
            time.sleep(2)

            # payment.html의 "결제하기" 버튼 클릭
            try:
                final_payment_btn = page.locator("button[onclick='processPayment()']")
                if final_payment_btn.is_visible(timeout=5000):
                    print("📍 Step 15-1: 최종 결제 버튼 클릭...")
                    final_payment_btn.click(timeout=10000)
                    self._safe_wait_for_load(page)
                else:
                    print("⚠️  최종 결제 버튼 없음 (이미 완료 페이지일 수 있음)")
            except Exception as e:
                print(f"⚠️  최종 결제 버튼 처리: {e}")

            # 15. 예매 완료 확인
            print("📍 Step 16: 예매 완료 확인...")
            time.sleep(3)  # 예매 완료 페이지 로딩 대기

            # URL 확인 (booking_complete.html인지)
            current_url = page.url
            if "booking_complete.html" not in current_url:
                self.logger.warning(f"⚠️ 예매 완료 페이지가 아님: {current_url}")
                self._log_event(
                    "error", {"step": 16, "error": "wrong_page", "url": current_url}
                )

            booking_number = self._get_booking_confirmation(page)

            if booking_number:
                elapsed_time = time.time() - start_time
                booking_data["booking_number"] = booking_number
                booking_data["elapsed_time"] = f"{elapsed_time:.2f}s"

                print(f"\n✅ 예매 완료! 예매 번호: {booking_number}")
                print(f"⏱️  소요 시간: {elapsed_time:.2f}초")

                # 스크린샷 저장
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                os.makedirs("tmp", exist_ok=True)
                screenshot_path = f"tmp/booking_success_{timestamp}_{booking_number}.png"
                page.screenshot(path=screenshot_path)
                print(f"📸 스크린샷 저장: {screenshot_path}")

                # 성공 로그
                self._log_event("success", booking_data)
                self.stats["success_count"] += 1

                return True
            else:
                print("\n⚠️  예매 번호를 찾을 수 없습니다.")

                # 페이지 HTML 덤프 (디버깅용)
                page_html = page.content()
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                os.makedirs("tmp", exist_ok=True)
                html_dump_path = f"tmp/page_dump_{timestamp}.html"
                with open(html_dump_path, "w", encoding="utf-8") as f:
                    f.write(page_html)
                print(f"📄 HTML 덤프 저장: {html_dump_path}")

                os.makedirs("tmp", exist_ok=True)
                page.screenshot(
                    path=f"tmp/booking_failed_{time.strftime('%Y%m%d_%H%M%S')}.png"
                )

                self._log_event(
                    "failure", {"error": "no_booking_number", "url": page.url}
                )
                self.stats["failure_count"] += 1

                return False

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)

            print(f"❌ 오류 발생: {error_msg}")
            print(f"⏱️  실패 시점: {elapsed_time:.2f}초")

            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                os.makedirs("tmp", exist_ok=True)
                page.screenshot(path=f"tmp/error_{timestamp}.png")
                print(f"📸 에러 스크린샷 저장: tmp/error_{timestamp}.png")
            except:
                pass

            self._log_event(
                "error", {"error": error_msg, "elapsed_time": f"{elapsed_time:.2f}s"}
            )
            self.stats["failure_count"] += 1
            self.stats["errors"].append(error_msg)

            return False

    def run_continuous(self, url: Optional[str] = None):
        """티켓 예매 프로세스 반복 실행 (Ctrl+C로 종료)"""
        with sync_playwright() as p:
            # 브라우저 실행
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(self.default_timeout)

            attempt = 0
            
            # 사용할 URL 결정
            target_url = url or self.base_url

            try:
                while True:
                    attempt += 1
                    self.stats["total_attempts"] = attempt

                    print(f"\n{'=' * 60}")
                    print(
                        f"🔄 예매 시도 #{attempt} (성공: {self.stats['success_count']}회)"
                    )
                    print(f"📍 URL: {target_url}")
                    print(f"{'=' * 60}\n")

                    success = self.run_once(page, context, url=target_url)

                    if success:
                        print(
                            f"\n🎉 예매 성공! (총 {self.stats['success_count']}회 성공)"
                        )
                    else:
                        print(f"\n⚠️  예매 실패. 재시도합니다...")

                    # 다음 시도 전 잠시 대기
                    wait_time = 3
                    print(f"\n⏱️  {wait_time}초 후 다음 예매를 시작합니다...")
                    time.sleep(wait_time)

            except KeyboardInterrupt:
                self._print_stats()
            finally:
                # 통계 저장
                self._save_stats()
                browser.close()

    def run_single(self, url: Optional[str] = None):
        """티켓 예매 프로세스 1회 실행"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(self.default_timeout)

            # 사용할 URL 결정
            target_url = url or self.base_url

            try:
                self.stats["total_attempts"] = 1
                print(f"\n{'=' * 60}")
                print(f"🔄 예매 시도 (1회 실행 모드)")
                print(f"📍 URL: {target_url}")
                print(f"{'=' * 60}\n")

                success = self.run_once(page, context, url=target_url)

                if success:
                    print(f"\n🎉 예매 성공!")
                    return True
                else:
                    print(f"\n⚠️  예매 실패")
                    return False

            finally:
                self._print_stats()
                self._save_stats()
                browser.close()

    def _print_stats(self):
        """통계 출력"""
        print(f"\n\n{'=' * 60}")
        print("🛑 예매 세션 종료")
        print(f"{'=' * 60}")
        print(f"📊 통계:")
        print(f"  - 총 시도: {self.stats['total_attempts']}회")
        print(f"  - 성공: {self.stats['success_count']}회")
        print(f"  - 실패: {self.stats['failure_count']}회")
        if self.stats["total_attempts"] > 0:
            success_rate = (
                self.stats["success_count"] / self.stats["total_attempts"]
            ) * 100
            print(f"  - 성공률: {success_rate:.1f}%")
        if self.stats["errors"]:
            print(f"  - 에러 종류: {len(set(self.stats['errors']))}개")
        print(f"{'=' * 60}")

    def _save_stats(self):
        """통계 JSON 파일로 저장"""
        if hasattr(self.logger, "log_file"):
            stats_file = str(self.logger.log_file).replace(
                "booking_log_", "booking_stats_"
            )
            try:
                # 통계 파일은 기존 로거의 위치(logs/)를 유지
                with open(stats_file, "w", encoding="utf-8") as f:
                    json.dump(self.stats, f, ensure_ascii=False, indent=2)
                print(f"📊 통계 파일 저장: {stats_file}")
            except Exception as e:
                self.logger.warning(f"통계 파일 저장 실패: {e}")

    def _human_delay(self, min_s=0.5, max_s=1.5):
        """사람처럼 보이기 위한 랜덤 지연"""
        delay = random.uniform(min_s, max_s)
        time.sleep(delay)

    def _human_move_and_click(self, page: Page, selector: str, name: str = "element"):
        """사람처럼 마우스를 이동시켜 클릭"""
        try:
            locator = page.locator(selector).first
            # 화면 섹션으로 스크롤 (중요!)
            locator.scroll_into_view_if_needed()
            locator.wait_for(state="visible", timeout=5000)
            
            # 요소의 위치와 크기 가져오기
            box = locator.bounding_box()
            if not box:
                locator.click()  # 실패 시 기본 클릭 시도
                return

            # 버튼 내부의 랜덤한 좌표 계산 (가장자리 20% 제외)
            target_x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
            target_y = box['y'] + box['height'] * random.uniform(0.2, 0.8)

            # 현재 마우스 위치 (알 수 없으면 랜덤 시작점)
            curr_x, curr_y = 0, 0 # Playwright는 0,0에서 시작
            
            # 마우스 이동 시뮬레이션 (3~5단계로 나누어 이동)
            steps = random.randint(3, 6)
            for i in range(1, steps + 1):
                inter_x = curr_x + (target_x - curr_x) * (i / steps) + random.uniform(-5, 5)
                inter_y = curr_y + (target_y - curr_y) * (i / steps) + random.uniform(-5, 5)
                page.mouse.move(inter_x, inter_y)
                time.sleep(random.uniform(0.01, 0.05))

            # 최종 위치로 부드럽게 이동
            page.mouse.move(target_x, target_y)
            time.sleep(random.uniform(0.1, 0.3)) # 클릭 전 망설임

            # 클릭
            page.mouse.click(target_x, target_y)
            print(f"✅ {name} 클릭 성공 (Human-like)")
            return True
        except Exception as e:
            print(f"⚠️  {name} 인간형 클릭 실패: {e}")
            try:
                page.locator(selector).first.click(timeout=5000)
                return True
            except:
                return False

    def _safe_wait_for_load(self, page: Page):
        """안전한 페이지 로드 대기"""
        try:
            # domcontentloaded는 networkidle보다 덜 엄격함
            page.wait_for_load_state("domcontentloaded", timeout=self.default_timeout)
            time.sleep(0.5)  # 추가 안정화 시간
        except PlaywrightTimeoutError:
            print("⚠️  페이지 로드 타임아웃 (계속 진행)")
            time.sleep(1)

    def _safe_click(self, page: Page, selector: str, element_name: str) -> bool:
        """안전한 클릭 (재시도 포함)"""
        for retry in range(self.max_retries):
            try:
                # 요소가 나타날 때까지 대기
                page.wait_for_selector(
                    selector, state="visible", timeout=self.default_timeout
                )
                element = page.locator(selector).first
                element.click(timeout=10000)
                print(f"✅ {element_name} 클릭 성공")
                return True
            except Exception as e:
                print(
                    f"⚠️  {element_name} 클릭 실패 (시도 {retry + 1}/{self.max_retries}): {e}"
                )
                time.sleep(2)

        print(f"❌ {element_name} 클릭 최종 실패")
        return False

    def _click_next_button(self, page: Page, button_text: str) -> bool:
        """다음 단계 버튼 클릭 (텍스트로 찾기)"""
        for retry in range(self.max_retries):
            try:
                # 방법 1: 텍스트로 버튼 찾기
                button = page.get_by_role("button", name=button_text)
                
                # 방법 2 (백업): ID로 버튼 찾기 (특히 좌석 선택 페이지의 '선택 완료' 버튼은 #next-btn임)
                if button_text == "선택 완료" and not button.is_visible():
                    button = page.locator("#next-btn")

                # 버튼이 보일 때까지 대기
                if button.is_visible(timeout=5000):
                    button.scroll_into_view_if_needed()
                    button.click(timeout=10000)
                    print(f"✅ '{button_text}' 버튼 클릭 성공")
                    return True
                else:
                    print(
                        f"⚠️  '{button_text}' 버튼이 보이지 않음 (시도 {retry + 1}/{self.max_retries})"
                    )
            except Exception as e:
                print(
                    f"⚠️  '{button_text}' 버튼 클릭 실패 (시도 {retry + 1}/{self.max_retries}): {e}"
                )
                time.sleep(2)

        print(f"❌ '{button_text}' 버튼 클릭 최종 실패")
        return False

    def _login(self, page: Page) -> bool:
        """로그인 수행

        Returns:
            성공 여부
        """
        try:
            print("⏳ 로그인 페이지 로딩 대기 중...")

            # 로그인 폼이 나타날 때까지 대기
            page.wait_for_selector(
                "#login-form", state="visible", timeout=self.default_timeout
            )
            time.sleep(1)  # 페이지 안정화

            # 이메일 입력
            print(f"📧 이메일 입력: {self.login_email}")
            email_input = page.locator("#email")
            email_input.fill(self.login_email)
            time.sleep(0.5)

            # 비밀번호 입력
            print(f"🔑 비밀번호 입력")
            password_input = page.locator("#password")
            password_input.fill(self.login_password)
            time.sleep(0.5)

            # 로그인 버튼 클릭
            print("🔘 로그인 버튼 클릭")
            login_btn = page.locator("button[type='submit']").filter(has_text="로그인")
            login_btn.click(timeout=10000)

            # 로그인 성공 대기 (alert 또는 페이지 이동 대기)
            time.sleep(3)  # alert 표시 및 리다이렉트 대기

            # sessionStorage에 currentUser가 저장되었는지 확인
            is_logged_in = page.evaluate("""
                () => {
                    const user = sessionStorage.getItem('currentUser');
                    return user !== null;
                }
            """)

            if is_logged_in:
                print("✅ 로그인 성공 (세션 확인됨)")
                return True
            else:
                print("⚠️  로그인 실패 (세션 없음)")
                return False

        except Exception as e:
            print(f"❌ 로그인 실패: {e}")
            return False

    def _handle_captcha(self, page: Page):
        """CAPTCHA 처리 (테스트 사이트용)"""
        try:
            # CAPTCHA 오버레이가 표시될 때까지 대기
            print("🔍 CAPTCHA 확인 중...")
            captcha_overlay = page.locator("#captcha-overlay:not(.captcha-hidden)")

            if captcha_overlay.is_visible(timeout=10000):
                print("🔍 CAPTCHA 감지됨 - 자동 해결 시도...")

                # CAPTCHA 정답을 페이지에서 추출 (currentCaptcha 변수)
                time.sleep(1)  # 캔버스 렌더링 대기

                captcha_answer = page.evaluate("""
                    () => {
                        // 테스트 사이트는 currentCaptcha 변수에 정답 저장
                        return window.currentCaptcha || '';
                    }
                """)

                if captcha_answer:
                    # 자동 입력
                    captcha_input = page.locator("#captcha-input")
                    captcha_input.fill(captcha_answer)
                    print(f"💡 CAPTCHA 정답 입력: {captcha_answer}")

                    # 제출 버튼 클릭
                    submit_btn = page.locator("#captcha-submit-btn")
                    submit_btn.click(timeout=10000)
                    
                    # 제출 후 잠시 대기 (연속 클릭 방지)
                    time.sleep(1.0) 

                    # CAPTCHA가 사라질 때까지 1초마다 확인 (최대 20초)
                    print("⏳ CAPTCHA 처리 완료 대기 중...")
                    for i in range(20):
                        time.sleep(1)

                        # CAPTCHA 오버레이가 hidden 클래스를 가졌는지 확인
                        is_hidden = page.evaluate("""
                            () => {
                                const overlay = document.getElementById('captcha-overlay');
                                return overlay && overlay.classList.contains('captcha-hidden');
                            }
                        """)

                        if is_hidden:
                            print(f"✅ CAPTCHA 자동 통과 ({i + 1}초)")
                            time.sleep(1.5)  # 화면 전환을 위한 추가 안정화 대기
                            return

                    print("⚠️  CAPTCHA 처리 타임아웃 (20초 경과)")
                else:
                    # 수동 입력 필요
                    print(
                        "⏸️  CAPTCHA 정답을 찾을 수 없습니다. 수동으로 입력해주세요..."
                    )
                    os.makedirs("tmp", exist_ok=True)
                    page.screenshot(
                        path=f"tmp/captcha_{time.strftime('%Y%m%d_%H%M%S')}.png"
                    )

                    # 1초마다 CAPTCHA 사라졌는지 확인 (최대 30초)
                    for i in range(30):
                        time.sleep(1)

                        is_hidden = page.evaluate("""
                            () => {
                                const overlay = document.getElementById('captcha-overlay');
                                return overlay && overlay.classList.contains('captcha-hidden');
                            }
                        """)

                        if is_hidden:
                            print(f"✅ CAPTCHA 통과 ({i + 1}초)")
                            time.sleep(1.5)  # 화면 전환을 위한 추가 안정화 대기
                            return

                    print("⚠️  CAPTCHA 수동 입력 타임아웃 (30초 경과)")
            else:
                print("✅ CAPTCHA 없음 - 계속 진행")
        except PlaywrightTimeoutError:
            # CAPTCHA가 없으면 계속 진행
            print("✅ CAPTCHA 표시 안됨 - 계속 진행")
        except Exception as e:
            print(f"⚠️  CAPTCHA 처리 중 오류 (계속 진행): {e}")

    def _select_seat(self, page: Page) -> Optional[Dict[str, str]]:
        """좌석 선택 (선택 성공할 때까지 재시도)

        Returns:
            선택된 좌석 정보 (seat_id, seat_grade) 또는 None
        """
        import random

        max_seat_attempts = 10  # 최대 10번 시도

        try:
            # CAPTCHA 통과 후 좌석이 이미 생성되어 있어야 함
            print("⏳ 좌석 로딩 대기 중...")
            time.sleep(1)  # 좌석 그리드 생성 대기 (CAPTCHA 통과 후이므로 짧게)

            # available 좌석이 나타날 때까지 대기
            try:
                page.wait_for_selector(
                    ".seat.available", state="visible", timeout=self.default_timeout
                )
            except PlaywrightTimeoutError:
                print("❌ 선택 가능한 좌석이 없습니다 (타임아웃)")
                return None

            # 좌석 선택 시도 (이미 선택된 좌석일 수 있으므로 반복)
            for attempt in range(max_seat_attempts):
                try:
                    # 현재 available 좌석 수 확인
                    available_count = page.locator(".seat.available").count()

                    if available_count == 0:
                        print("⚠️  선택 가능한 좌석이 없습니다.")
                        return None

                    print(
                        f"🪑 좌석 선택 시도 {attempt + 1}/{max_seat_attempts} (가능 좌석: {available_count}개)"
                    )

                    # 랜덤하게 available 좌석 선택 (모든 좌석 중에서)
                    seat_index = random.randint(0, available_count - 1)
                    available_seat = page.locator(".seat.available").nth(seat_index)

                    # 좌석 정보 가져오기
                    seat_id = available_seat.get_attribute("data-seat")
                    seat_grade = available_seat.get_attribute("data-grade")

                    # "Undefined" 등급 체크 (비정상적인 좌석 상태)
                    if not seat_grade or seat_grade.lower() in ["undefined", "none", "null"]:
                        print(f"⚠️  올바르지 않은 좌석 등급 감지: {seat_id} ({seat_grade}). 처음 화면으로 이동합니다.")
                        return {"status": "RESTART"}

                    # 요소의 위치와 크기 가져오기
                    available_seat.scroll_into_view_if_needed()
                    time.sleep(0.1) # 스크롤 후 안정화
                    box = available_seat.bounding_box()
                    if not box:
                        print(f"⚠️  좌석 {seat_id}의 좌표를 가져올 수 없습니다. 재시도...")
                        continue

                    # 버튼 내부의 중앙에 밀집된 좌표 계산 (작아진 좌석 대응: 0.2~0.8 -> 0.4~0.6)
                    target_x = box['x'] + box['width'] * random.uniform(0.4, 0.6)
                    target_y = box['y'] + box['height'] * random.uniform(0.4, 0.6)

                    # 인간형 마우스 이동 및 클릭 적용
                    self._human_delay(0.2, 0.5) # 좌석 고르는데 걸리는 시간
                    
                    seat_selector = f"[data-seat='{seat_id}']"
                    if not self._human_move_and_click(page, seat_selector, f"좌석 {seat_id}"):
                        continue

                    # 클릭 후 확인 전 잠시 대기 (사람의 반응 속도)
                    self._human_delay(0.3, 0.8)

                    # 팝업 체크 (이미 선택된 좌석인 경우)
                    try:
                        alert_btn = page.locator("#alert-confirm-btn")
                        if alert_btn.is_visible(timeout=500):
                            print(f"⚠️  이미 선택된 좌석입니다 ({seat_id}). 팝업 확인 중...")
                            self._human_delay(0.5, 1.2) # 팝업 보고 당황하는 시간
                            alert_btn.click()
                            time.sleep(0.5)
                            continue 
                    except:
                        pass

                    # 최종 확인
                    selected_count = page.locator(".seat.selected").count()
                    next_btn = page.locator("#next-btn")
                    
                    if selected_count > 0:
                        try:
                            # 버튼이 나타날 때까지 대기
                            next_btn.wait_for(state="visible", timeout=2000)
                            print(f"✅ 좌석 선택 완료 (선택된 좌석: {selected_count}개)")
                            self._human_delay(0.5, 1.0) # 다음 단계 누르기 전 생각하는 시간
                            return {
                                "seat_id": seat_id or "unknown",
                                "seat_grade": seat_grade or "unknown",
                            }
                        except:
                            print(f"⚠️  좌석은 선택된 듯하나 '선택 완료' 버튼이 보이지 않음. 재시도...")
                    else:
                        print(f"⚠️  좌석 선택 실패. 다음 좌석을 시도합니다.")
                        self._human_delay(0.3, 0.6)

                except Exception as e:
                    print(f"⚠️  좌석 클릭 실패 (시도 {attempt + 1}): {e}")
                    time.sleep(1)

            print(f"❌ 좌석 선택 최종 실패 ({max_seat_attempts}번 시도)")
            return None

        except Exception as e:
            print(f"❌ 좌석 선택 오류: {e}")
            return None

    def _fill_booker_info(self, page: Page):
        """예매자 정보 입력"""
        try:
            # 입력 함수 정의 (readonly 체크)
            def safe_fill(selector, value):
                locator = page.locator(selector)
                if locator.is_visible(timeout=3000):
                    # 필드가 편집 가능한지 확인 (readonly가 아닌지)
                    is_editable = page.evaluate(f"""
                        () => {{
                            const el = document.querySelector('{selector}');
                            return el && !el.readOnly && !el.disabled;
                        }}
                    """)
                    if is_editable:
                        locator.fill(value)
                    else:
                        print(f"ℹ️  필드 {selector}가 읽기 전용이므로 입력을 건너뜁니다.")

            # 이름
            safe_fill("#booker-name", "홍길동")

            # 전화번호
            safe_fill("#booker-phone", "010-1234-5678")

            # 이메일
            safe_fill("#booker-email", self.login_email)

            print("✅ 예매자 정보 입력 단계 완료")
        except Exception as e:
            print(f"⚠️  예매자 정보 입력 중 오류 (계속 진행): {e}")

    def _get_booking_confirmation(self, page: Page) -> Optional[str]:
        """예매 완료 확인 및 예매 번호 추출

        Returns:
            예매 번호 (M으로 시작하는 8자리 숫자) 또는 None
        """
        try:
            # 방법 1: ID로 찾기 (booking_complete.html의 #booking-number)
            try:
                booking_number_elem = page.locator("#booking-number")
                if booking_number_elem.is_visible(timeout=5000):
                    text = booking_number_elem.inner_text().strip()
                    if text and text != "-":
                        print(f"✅ 예매 번호 발견 (ID): {text}")
                        return text
            except:
                pass

            # 방법 2: 클래스로 찾기
            try:
                booking_number_elem = page.locator(
                    ".booking-number, .confirmation-number"
                )
                if booking_number_elem.is_visible(timeout=5000):
                    text = booking_number_elem.inner_text().strip()
                    if text and text != "-":
                        print(f"✅ 예매 번호 발견 (클래스): {text}")
                        return text
            except:
                pass

            # 방법 3: 페이지 전체 텍스트에서 패턴 검색
            try:
                page_text = page.inner_text("body")
                if "예매 번호" in page_text or "M" in page_text:
                    # M으로 시작하는 예매 번호 패턴 찾기 (M + 8자리 숫자)
                    import re

                    match = re.search(r"M\d{8}", page_text)
                    if match:
                        booking_number = match.group(0)
                        print(f"✅ 예매 번호 발견 (정규식): {booking_number}")
                        return booking_number
            except Exception as e:
                print(f"⚠️  페이지 텍스트 검색 실패: {e}")

            # 방법 4: JavaScript로 직접 추출
            try:
                booking_number = page.evaluate("""
                    () => {
                        const elem = document.getElementById('booking-number');
                        if (elem && elem.textContent.trim() !== '-') {
                            return elem.textContent.trim();
                        }
                        
                        // 페이지 전체에서 M으로 시작하는 패턴 찾기
                        const text = document.body.textContent;
                        const match = text.match(/M\\d{8}/);
                        return match ? match[0] : null;
                    }
                """)
                if booking_number:
                    print(f"✅ 예매 번호 발견 (JavaScript): {booking_number}")
                    return booking_number
            except Exception as e:
                print(f"⚠️  JavaScript 추출 실패: {e}")

            print("❌ 모든 방법으로 예매 번호를 찾을 수 없습니다")
            return None

        except Exception as e:
            print(f"⚠️  예매 번호 추출 실패: {e}")
            return None


def main():
    """메인 함수"""
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(
        description="티켓 예매 자동화 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python ticket_booking_automation.py                           # 기본 설정으로 무한 반복 실행
  python ticket_booking_automation.py --once                    # 1회만 실행
  python ticket_booking_automation.py --headless                # 헤드리스 모드
  python ticket_booking_automation.py --email user@test.com --password 12345678
  python ticket_booking_automation.py --url http://localhost:8000
        """,
    )

    parser.add_argument(
        "url_pos",
        nargs="?",
        default=None,
        help="티켓 예매 사이트 URL (nargs가 우선순위가 더 높음)",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="티켓 예매 사이트 URL (기본: http://localhost:5000)",
    )
    parser.add_argument(
        "--email",
        default="test1@email.com",
        help="로그인 이메일 (기본: test1@email.com)",
    )
    parser.add_argument(
        "--password", default="11111111", help="로그인 비밀번호 (기본: 11111111)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="헤드리스 모드로 실행 (브라우저 창 숨김)",
    )
    parser.add_argument(
        "--once", action="store_true", help="1회만 실행 (무한 반복 안함)"
    )
    parser.add_argument(
        "--log-dir", default="logs", help="로그 파일 저장 디렉토리 (기본: logs)"
    )

    args = parser.parse_args()
    
    # URL 결정: 위치 인자가 있으면 그것을 사용, 없으면 --url 플래그 사용
    final_url = args.url_pos if args.url_pos else args.url

    # 헤더 출력
    print("=" * 60)
    print("🎫 티켓 예매 자동화 시작")
    print("=" * 60)
    print(f"📍 URL: {args.url}")
    print(f"👤 이메일: {args.email}")
    print(f"🔒 비밀번호: {'*' * len(args.password)}")
    print(f"🖥️  헤드리스: {'예' if args.headless else '아니오'}")
    print(f"🔄 실행 모드: {'1회 실행' if args.once else '무한 반복'}")
    print(f"📁 로그 디렉토리: {args.log_dir}")

    if not args.once:
        print("💡 Ctrl+C를 눌러 종료할 수 있습니다.")

    print("=" * 60)
    print()

    # 로거 설정
    logger = setup_logger(args.log_dir)

    # 봇 실행
    bot = TicketBookingBot(
        base_url=final_url,
        headless=args.headless,
        login_email=args.email,
        login_password=args.password,
        logger=logger,
    )

    # 실행 모드에 따라 분기
    if args.once:
        success = bot.run_single(url=final_url)
        sys.exit(0 if success else 1)
    else:
        bot.run_continuous(url=final_url)


if __name__ == "__main__":
    main()
