// ==UserScript==
// @name         티켓팅 매크로 시뮬레이터 (좌석 선택 매크로 패턴)
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  좌석 선택 매크로 패턴 시뮬레이션 - 우클릭 스카우팅, 직선 마우스, 초고속 반응
// @author       AI Team
// @match        http://localhost:8000/*
// @match        http://127.0.0.1:8000/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function () {
  'use strict';

  /* ========================================
     설정 및 상태 관리
     ======================================== */

  const CONFIG = {
    macroMode: false,       // true: 매크로 패턴, false: 정상 사용자 패턴
    autoRun: false,         // true: 자동 시작, false: 수동 시작
    loopCount: 100,         // 총 반복 횟수
    currentLoop: 0,         // 현재 반복 횟수
    enabled: false          // 스크립트 활성화 여부
  };

  // localStorage에서 설정 로드
  function loadConfig() {
    const saved = localStorage.getItem('macro_config');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        Object.assign(CONFIG, parsed);
      } catch (e) {
        console.error('설정 로드 실패:', e);
      }
    }
  }

  // localStorage에 설정 저장
  function saveConfig() {
    localStorage.setItem('macro_config', JSON.stringify(CONFIG));
  }

  loadConfig();

  /* ========================================
     페이지별 라우팅
     ======================================== */

  const currentPath = window.location.pathname;
  const currentURL = window.location.href;
  console.log('🤖 매크로 스크립트 로드됨!');
  console.log('  📍 경로:', currentPath);
  console.log('  🌐 전체 URL:', currentURL);
  console.log('  ⚙️ CONFIG:', JSON.stringify(CONFIG, null, 2));

  // 컨트롤 패널 UI 추가
  window.addEventListener('load', () => {
    console.log('✅ 페이지 로드 완료 - 컨트롤 패널 추가 시작');
    try {
      addControlPanel();
      console.log('✅ 컨트롤 패널 추가 성공!');
    } catch (error) {
      console.error('❌ 컨트롤 패널 추가 실패:', error);
    }

    // Auto-Run이 활성화되어 있으면 자동 시작
    if (CONFIG.autoRun && CONFIG.enabled) {
      console.log('⚡ Auto-Run 활성화됨 - 자동 시작 예정');
      setTimeout(() => {
        executePageAction();
      }, 500);
    } else {
      console.log('ℹ️ Auto-Run 비활성화 - 수동 시작 대기 중');
    }
  });

  function executePageAction() {
    console.log('🎬 executePageAction 호출됨');
    console.log('  📍 현재 경로:', currentPath);
    console.log('  ⚙️ enabled:', CONFIG.enabled);

    if (!CONFIG.enabled) {
      console.log('⏸️ CONFIG.enabled = false 이므로 실행하지 않음');
      return;
    }

    if (currentPath.includes('index.html') || currentPath === '/' || currentPath === '') {
      console.log('  → 🏠 index.html 페이지 감지');
      handleIndexPage();
    } else if (currentPath.includes('performance_detail.html')) {
      console.log('  → 📅 performance_detail.html 페이지 감지');
      handlePerformanceDetailPage();
    } else if (currentPath.includes('queue.html')) {
      console.log('  → ⏳ queue.html 페이지 감지');
      handleQueuePage();
    } else if (currentPath.includes('seat_select.html')) {
      console.log('  → 🎫 seat_select.html 페이지 감지');
      handleSeatSelectPage();
    } else if (currentPath.includes('discount.html')) {
      console.log('  → 💰 discount.html 페이지 감지');
      handleDiscountPage();
    } else if (currentPath.includes('order_info.html')) {
      console.log('  → 📝 order_info.html 페이지 감지');
      handleOrderInfoPage();
    } else if (currentPath.includes('payment.html')) {
      console.log('  → 💳 payment.html 페이지 감지');
      handlePaymentPage();
    } else if (currentPath.includes('booking_complete.html')) {
      console.log('  → ✅ booking_complete.html 페이지 감지');
      handleBookingCompletePage();
    } else {
      console.log('  ⚠️ 알 수 없는 페이지 - 핸들러 없음');
    }
  }

  /* ========================================
     1. 공연 선택 페이지 (index.html)
     ======================================== */

  function handleIndexPage() {
    console.log('📋 공연 선택 페이지');

    const delay = CONFIG.macroMode
      ? (50 + Math.random() * 50)
      : (500 + Math.random() * 500);

    setTimeout(() => {
      const cards = document.querySelectorAll('.performance-card');
      const openCards = Array.from(cards).filter(card => {
        const badge = card.querySelector('.performance-status-badge');
        return badge && badge.textContent.includes('판매중');
      });

      if (openCards.length === 0) {
        console.error('❌ 판매 중인 공연이 없습니다');
        updateStatus('판매 중인 공연 없음', 'error');
        return;
      }

      const randomCard = openCards[Math.floor(Math.random() * openCards.length)];
      const perfTitle = randomCard.querySelector('.performance-card-title')?.textContent.trim();

      if (!CONFIG.macroMode) {
        // Human: 호버 먼저
        randomCard.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
        setTimeout(() => {
          randomCard.click();
          console.log('👤 정상 클릭:', perfTitle);
          updateStatus(`공연 선택: ${perfTitle}`);
        }, 300);
      } else {
        // Macro: 즉시 클릭
        randomCard.click();
        console.log('🤖 매크로 클릭:', perfTitle);
        updateStatus(`공연 선택: ${perfTitle} (매크로)`);
      }

      logMacroAction('performance_select', {
        reaction_time_ms: delay,
        macro_mode: CONFIG.macroMode,
        performance: perfTitle
      });
    }, delay);
  }

  /* ========================================
     2. 공연 상세 - 날짜/회차 선택 (performance_detail.html)
     ======================================== */

  function handlePerformanceDetailPage() {
    console.log('📅 공연 상세 페이지');

    // 오픈 시간 대기
    waitForOpen(() => {
      console.log('✅ 티켓 오픈됨!');

      // 날짜 선택
      const dateDelay = CONFIG.macroMode
        ? (10 + Math.random() * 40)
        : (300 + Math.random() * 500);

      setTimeout(() => {
        const dateButtons = document.querySelectorAll('.date-btn:not([disabled])');
        if (dateButtons.length === 0) {
          console.error('❌ 선택 가능한 날짜가 없습니다');
          return;
        }

        const randomDate = dateButtons[Math.floor(Math.random() * dateButtons.length)];

        if (!CONFIG.macroMode) {
          // Human: 호버 + 곡선
          const trajectory = simulateHumanMouseMove(randomDate);
          randomDate.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
          setTimeout(() => {
            randomDate.click();
            console.log('👤 정상 날짜 선택');
            updateStatus('날짜 선택 완료');
          }, 200);
        } else {
          // Macro: 직선 + 즉시
          const trajectory = simulateMacroMouseMove(randomDate);
          randomDate.click();
          console.log('🤖 매크로 날짜 선택');
          updateStatus('날짜 선택 완료 (매크로)');
        }

        logMacroAction('date_select', {
          reaction_time_from_open_ms: dateDelay,
          macro_mode: CONFIG.macroMode
        });

        // 시간 선택
        const timeDelay = CONFIG.macroMode
          ? (10 + Math.random() * 40)
          : (500 + Math.random() * 500);

        setTimeout(() => {
          const timeButtons = document.querySelectorAll('.time-btn:not([disabled])');
          if (timeButtons.length === 0) return;

          const randomTime = timeButtons[Math.floor(Math.random() * timeButtons.length)];

          if (!CONFIG.macroMode) {
            simulateHumanMouseMove(randomTime);
            randomTime.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
            setTimeout(() => {
              randomTime.click();
              console.log('👤 정상 시간 선택');
              updateStatus('시간 선택 완료');
            }, 200);
          } else {
            simulateMacroMouseMove(randomTime);
            randomTime.click();
            console.log('🤖 매크로 시간 선택');
            updateStatus('시간 선택 완료 (매크로)');
          }

          logMacroAction('time_select', {
            click_interval_ms: timeDelay,
            macro_mode: CONFIG.macroMode
          });

          // "예매 시작" 버튼 클릭
          const bookingDelay = CONFIG.macroMode
            ? (10 + Math.random() * 40)
            : (400 + Math.random() * 300);

          setTimeout(() => {
            const startButton = document.getElementById('start-booking-btn');
            if (startButton && startButton.style.display !== 'none' && !startButton.disabled) {
              startButton.click();
              console.log('✅ 예매 시작 클릭');
              updateStatus('예매 시작');
            }
          }, bookingDelay);

        }, timeDelay);

      }, dateDelay);
    });
  }

  function waitForOpen(callback) {
    const checkOpen = setInterval(() => {
      const dateButtons = document.querySelectorAll('.date-btn:not([disabled])');
      if (dateButtons.length > 0) {
        clearInterval(checkOpen);
        callback();
      }
    }, 100);

    // 타임아웃 (60초)
    setTimeout(() => {
      clearInterval(checkOpen);
      console.error('❌ 오픈 대기 타임아웃');
    }, 60000);
  }

  /* ========================================
     3. 대기열 페이지 (queue.html)
     ======================================== */

  function handleQueuePage() {
    console.log('⏳ 대기열 페이지 (자동 통과)');
    updateStatus('대기열 통과 중...');
    // 웹사이트가 자동으로 다음 페이지로 이동시킴
  }

  /* ========================================
     4. 좌석 선택 페이지 (seat_select.html) - 핵심!
     ======================================== */

  function handleSeatSelectPage() {
    console.log('🎫 좌석 선택 페이지');
    updateStatus('좌석 선택 중...');

    // CAPTCHA 통과 대기
    waitForCaptcha(() => {
      console.log('✅ CAPTCHA 통과');

      // 좌석 그리드 로드 대기
      waitForElement('.seat.available', () => {
        console.log('✅ 좌석 그리드 로드됨');

        if (CONFIG.macroMode) {
          // 🤖 Macro Mode - 이미지 패턴 완전 재현!
          executeMacroSeatSelection();
        } else {
          // 👤 Human Mode - 정상 사용자 패턴
          executeHumanSeatSelection();
        }
      });
    });
  }

  // 매크로 좌석 선택
  function executeMacroSeatSelection() {
    console.log('🤖 매크로 좌석 선택 시작');

    // 1. 원도우 포커싱
    window.focus();
    console.log('  ✓ 원도우 포커싱');

    setTimeout(() => {
      const seats = document.querySelectorAll('.seat.available');
      if (seats.length === 0) {
        console.error('❌ 선택 가능한 좌석 없음');
        return;
      }

      const seat = seats[Math.floor(Math.random() * Math.min(5, seats.length))];

      // 2. 우클릭 스카우팅 (비파괴적 정보 수집)
      const scoutInfo = rightClickScout(seat);
      console.log('  ✓ 우클릭 스카우팅:', scoutInfo);

      setTimeout(() => {
        // 3. 직선 마우스 이동
        const trajectory = simulateMacroMouseMove(seat);
        console.log('  ✓ 직선 마우스 이동 (straightness: 0.98)');

        // 4. 좌클릭
        seat.click();
        console.log('  ✓ 좌석 클릭:', seat.dataset.seat);
        updateStatus(`좌석 선택: ${seat.dataset.seat} (매크로)`);

        // 로그에 매크로 지표 기록
        logMacroIndicators({
          reaction_time_from_load_ms: 25,
          has_right_click_scouting: true,
          right_click_data: scoutInfo,
          mouse_straightness: 0.98,
          has_tremor: false,
          trajectory_points: trajectory.length,
          window_focus_immediate: true,
          click_intervals: [25, 25]
        });

        // 5. "다음" 버튼 클릭
        setTimeout(() => {
          const nextButton = document.getElementById('next-btn') || document.querySelector('button[onclick="confirmSeats()"]');
          if (nextButton && nextButton.style.display !== 'none') {
            nextButton.click();
            console.log('  ✓ 다음 버튼 클릭');
          }
        }, 25);

      }, 25);

    }, 10);
  }

  // 정상 사용자 좌석 선택
  function executeHumanSeatSelection() {
    console.log('👤 정상 좌석 선택 시작');

    setTimeout(() => {
      const seats = document.querySelectorAll('.seat.available');
      if (seats.length === 0) {
        console.error('❌ 선택 가능한 좌석 없음');
        return;
      }

      const seat = seats[Math.floor(Math.random() * Math.min(5, seats.length))];

      // 호버링 (떨림 포함)
      const hoverDuration = 2000 + Math.random() * 3000;
      simulateHumanHover(seat, hoverDuration);
      console.log(`  ✓ 호버링 (${Math.floor(hoverDuration)}ms, 떨림 포함)`);

      setTimeout(() => {
        // 곡선 마우스 이동
        const trajectory = simulateHumanMouseMove(seat);
        console.log('  ✓ 곡선 마우스 이동 (straightness: 0.7)');

        // 클릭
        seat.click();
        console.log('  ✓ 좌석 클릭:', seat.dataset.seat);
        updateStatus(`좌석 선택: ${seat.dataset.seat}`);

        logHumanIndicators({
          reaction_time_ms: 450,
          mouse_straightness: 0.7,
          has_tremor: true,
          trajectory_points: trajectory.length,
          hover_duration_ms: hoverDuration
        });

        setTimeout(() => {
          const nextButton = document.getElementById('next-btn') || document.querySelector('button[onclick="confirmSeats()"]');
          if (nextButton && nextButton.style.display !== 'none') {
            nextButton.click();
            console.log('  ✓ 다음 버튼 클릭');
          }
        }, 500);

      }, 450 + hoverDuration);

    }, 450);
  }

  // 우클릭 스카우팅 (비파괴적 정보 수집) - 매크로 전용
  function rightClickScout(seat) {
    const rect = seat.getBoundingClientRect();

    const event = new MouseEvent('contextmenu', {
      bubbles: true,
      cancelable: true,
      view: window,
      button: 2,  // 우클릭
      clientX: rect.left + rect.width / 2,
      clientY: rect.top + rect.height / 2
    });

    seat.dispatchEvent(event);
    event.preventDefault();  // 실제 컨텍스트 메뉴는 안 띄움

    // 정보 수집 (비파괴적)
    const info = {
      seat_id: seat.dataset.seat,
      grade: seat.dataset.grade,
      price: seat.dataset.price,
      row: seat.dataset.row,
      col: seat.dataset.col,
      status: 'available',
      timestamp: Date.now()
    };

    return info;
  }

  // 직선 마우스 이동 시뮬레이션 (매크로)
  function simulateMacroMouseMove(element) {
    const rect = element.getBoundingClientRect();
    const endX = rect.left + rect.width / 2;
    const endY = rect.top + rect.height / 2;

    // 직선: 시작점 → 끝점 (중간 포인트 최소)
    const trajectory = [
      [100, 100, 0],
      [endX, endY, 25]
    ];

    // straightness: 0.98 (거의 완벽한 직선)
    return trajectory;
  }

  // 곡선 마우스 이동 시뮬레이션 (정상 사용자)
  function simulateHumanMouseMove(element) {
    const rect = element.getBoundingClientRect();
    const endX = rect.left + rect.width / 2;
    const endY = rect.top + rect.height / 2;

    // 곡선: 여러 중간 포인트 (떨림 포함)
    const trajectory = [];
    const startX = 100, startY = 100;
    const steps = 10 + Math.floor(Math.random() * 10);

    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const x = startX + (endX - startX) * t + (Math.random() - 0.5) * 20; // 떨림
      const y = startY + (endY - startY) * t + (Math.random() - 0.5) * 20;
      trajectory.push([x, y, i * 50]);
    }

    // straightness: 약 0.6-0.8 (곡선)
    return trajectory;
  }

  // 호버링 시뮬레이션 (정상 사용자만)
  function simulateHumanHover(element, duration) {
    element.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));

    // 떨림 효과
    const tremorInterval = setInterval(() => {
      // 미세한 떨림 기록만 (실제 마우스는 안 움직임)
      const rect = element.getBoundingClientRect();
      const x = rect.left + rect.width / 2 + (Math.random() - 0.5) * 5;
      const y = rect.top + rect.height / 2 + (Math.random() - 0.5) * 5;

      // 떨림 데이터 기록 (로그용)
      if (window.mouseTrajectory) {
        window.mouseTrajectory.push([x, y, Date.now()]);
      }
    }, 100);

    setTimeout(() => {
      clearInterval(tremorInterval);
    }, duration);
  }

  function waitForCaptcha(callback) {
    // CAPTCHA가 없거나 이미 통과한 경우
    const captchaOverlay = document.getElementById('captcha-overlay');
    if (!captchaOverlay || captchaOverlay.classList.contains('captcha-hidden')) {
      callback();
      return;
    }

    // CAPTCHA 통과 대기
    const checkCaptcha = setInterval(() => {
      if (captchaOverlay.classList.contains('captcha-hidden')) {
        clearInterval(checkCaptcha);
        callback();
      }
    }, 500);

    // 타임아웃 (30초)
    setTimeout(() => {
      clearInterval(checkCaptcha);
      console.error('❌ CAPTCHA 통과 타임아웃');
    }, 30000);
  }

  function waitForElement(selector, callback, timeout = 10000) {
    const startTime = Date.now();
    const checkElement = setInterval(() => {
      const element = document.querySelector(selector);
      if (element) {
        clearInterval(checkElement);
        callback();
      } else if (Date.now() - startTime > timeout) {
        clearInterval(checkElement);
        console.error('❌ 요소 로드 타임아웃:', selector);
      }
    }, 100);
  }

  /* ========================================
     5. 할인 선택 페이지 (discount.html)
     ======================================== */

  function handleDiscountPage() {
    console.log('💰 할인 선택 페이지');
    updateStatus('할인 선택 중...');

    setTimeout(() => {
      // "할인 없음" 선택
      const noDiscountOption = document.querySelector('[onclick*="None"]') ||
        document.querySelector('[data-discount="none"]');

      if (noDiscountOption) {
        noDiscountOption.click();
        console.log('  ✓ 할인 없음 선택');
      }

      setTimeout(() => {
        // "다음" 버튼 클릭
        const nextButton = document.querySelector('button[onclick*="confirmDiscount"]') ||
          document.getElementById('next-btn');
        if (nextButton) {
          nextButton.click();
          console.log('  ✓ 다음 버튼 클릭');
        }
      }, 300);

    }, 400);
  }

  /* ========================================
     6. 예매 정보 입력 페이지 (order_info.html)
     ======================================== */

  function handleOrderInfoPage() {
    console.log('📝 예매 정보 입력 페이지');
    updateStatus('예매 정보 입력 중...');

    setTimeout(() => {
      // 배송 방법 선택 (픽업)
      const pickupOption = document.querySelector('[onclick*="pickup"]') ||
        Array.from(document.querySelectorAll('.payment-method')).find(el =>
          el.textContent.includes('현장 수령')
        );

      if (pickupOption) {
        pickupOption.click();
        console.log('  ✓ 현장 수령 선택');
      }

      setTimeout(() => {
        // "다음" 버튼 클릭
        const confirmButton = document.querySelector('[onclick="confirmOrderInfo()"]') ||
          document.querySelector('button.btn-primary');
        if (confirmButton) {
          confirmButton.click();
          console.log('  ✓ 다음 버튼 클릭');
        }
      }, 300);

    }, 400);
  }

  /* ========================================
     7. 결제 수단 선택 페이지 (payment.html)
     ======================================== */

  function handlePaymentPage() {
    console.log('💳 결제 페이지');
    updateStatus('결제 진행 중...');

    setTimeout(() => {
      // 신용카드 선택
      const cardOption = document.querySelector('[onclick*="card"]') ||
        Array.from(document.querySelectorAll('.payment-method')).find(el =>
          el.textContent.includes('신용카드')
        );

      if (cardOption) {
        cardOption.click();
        console.log('  ✓ 신용카드 선택');
      }

      setTimeout(() => {
        // "결제하기" 버튼 클릭
        const payButton = document.querySelector('[onclick="processPayment()"]') ||
          document.querySelector('button.btn-primary');
        if (payButton) {
          payButton.click();
          console.log('  ✓ 결제하기 클릭');
        }
      }, 400);

    }, 300);
  }

  /* ========================================
     8. 예매 완료 페이지 (booking_complete.html)
     ======================================== */

  function handleBookingCompletePage() {
    console.log('✅ 예매 완료 페이지');

    CONFIG.currentLoop++;
    saveConfig();

    updateStatus(`완료: ${CONFIG.currentLoop}/${CONFIG.loopCount}`, 'success');

    console.log(`🎉 ${CONFIG.currentLoop}번째 완료!`);

    // 다음 반복 확인
    if (CONFIG.enabled && CONFIG.currentLoop < CONFIG.loopCount) {
      console.log(`⏭️ ${CONFIG.currentLoop + 1}번 시작 준비...`);

      setTimeout(() => {
        // 처음부터 다시
        window.location.href = '/index.html';
      }, 2000);
    } else if (CONFIG.currentLoop >= CONFIG.loopCount) {
      console.log(`🎊 전체 ${CONFIG.loopCount}개 완료!`);
      updateStatus(`전체 완료: ${CONFIG.loopCount}개`, 'success');
      CONFIG.enabled = false;
      CONFIG.currentLoop = 0;
      saveConfig();
    }
  }

  /* ========================================
     로깅 함수들
     ======================================== */

  function logMacroAction(action, data) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      action: action,
      macro_mode: CONFIG.macroMode,
      ...data
    };

    console.log('📊 로그:', logEntry);

    // 기존 로깅 시스템에 추가
    if (window.logData && window.logData.stages) {
      const currentStage = getCurrentStage();
      if (currentStage) {
        if (!window.logData.stages[currentStage].macro_actions) {
          window.logData.stages[currentStage].macro_actions = [];
        }
        window.logData.stages[currentStage].macro_actions.push(logEntry);
      }
    }
  }

  function logMacroIndicators(indicators) {
    console.log('🤖 매크로 지표:', indicators);

    if (window.logData && window.logData.stages && window.logData.stages.seat) {
      window.logData.stages.seat.macro_indicators = indicators;
    }
  }

  function logHumanIndicators(indicators) {
    console.log('👤 정상 사용자 지표:', indicators);

    if (window.logData && window.logData.stages && window.logData.stages.seat) {
      window.logData.stages.seat.human_indicators = indicators;
    }
  }

  function getCurrentStage() {
    if (currentPath.includes('index.html')) return 'perf';
    if (currentPath.includes('performance_detail.html')) return 'perf';
    if (currentPath.includes('queue.html')) return 'queue';
    if (currentPath.includes('seat_select.html')) return 'seat';
    if (currentPath.includes('discount.html')) return 'discount';
    if (currentPath.includes('order_info.html')) return 'order_info';
    if (currentPath.includes('payment.html')) return 'payment';
    return null;
  }

  /* ========================================
     컨트롤 패널 UI
     ======================================== */

  function addControlPanel() {
    const panel = document.createElement('div');
    panel.id = 'macro-control-panel';
    panel.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.95);
            color: white;
            padding: 15px;
            border-radius: 12px;
            z-index: 999999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            min-width: 280px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            backdrop-filter: blur(10px);
        `;

    panel.innerHTML = `
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                🤖 매크로 시뮬레이터
                <span id="macro-mode-badge" style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #666; margin-left: auto;">
                    ${CONFIG.macroMode ? '매크로' : '정상'}
                </span>
            </div>

            <label style="display: flex; align-items: center; margin-bottom: 8px; cursor: pointer;">
                <input type="checkbox" id="macro-mode-toggle" ${CONFIG.macroMode ? 'checked' : ''}
                       style="margin-right: 8px; width: 16px; height: 16px; cursor: pointer;">
                <span style="font-size: 14px;">🤖 Macro Mode (빠른 클릭)</span>
            </label>

            <label style="display: flex; align-items: center; margin-bottom: 8px; cursor: pointer;">
                <input type="checkbox" id="auto-run-toggle" ${CONFIG.autoRun ? 'checked' : ''}
                       style="margin-right: 8px; width: 16px; height: 16px; cursor: pointer;">
                <span style="font-size: 14px;">⚡ Auto Run (자동 실행)</span>
            </label>

            <div style="margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                <label style="font-size: 14px; flex-shrink: 0;">반복 횟수:</label>
                <input type="number" id="loop-count-input" value="${CONFIG.loopCount}" min="1" max="1000"
                       style="flex: 1; padding: 4px 8px; background: #222; color: white; border: 1px solid #444; border-radius: 4px; font-size: 14px;">
            </div>

            <div style="margin-bottom: 10px; font-size: 13px; color: #aaa;">
                진행: <span id="loop-progress">${CONFIG.currentLoop}/${CONFIG.loopCount}</span>
            </div>

            <button id="start-macro-btn"
                    style="width: 100%; padding: 10px; background: linear-gradient(135deg, #4CAF50, #45a049);
                           color: white; border: none; border-radius: 6px; cursor: pointer;
                           font-size: 14px; font-weight: bold; margin-bottom: 8px;">
                ${CONFIG.enabled ? '⏸️ 중지' : '▶️ 시작'}
            </button>

            <button id="reset-macro-btn"
                    style="width: 100%; padding: 8px; background: #555;
                           color: white; border: none; border-radius: 6px; cursor: pointer;
                           font-size: 13px;">
                🔄 초기화
            </button>

            <div id="macro-status" style="margin-top: 12px; padding: 8px; background: rgba(255,255,255,0.1);
                                          border-radius: 6px; font-size: 12px; color: #aaa; min-height: 40px;">
                대기 중...
            </div>

            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #333; font-size: 11px; color: #666;">
                v1.0.0 | Tampermonkey UserScript
            </div>
        `;

    document.body.appendChild(panel);

    // 이벤트 리스너
    document.getElementById('macro-mode-toggle').addEventListener('change', (e) => {
      CONFIG.macroMode = e.target.checked;
      saveConfig();
      const badge = document.getElementById('macro-mode-badge');
      badge.textContent = CONFIG.macroMode ? '매크로' : '정상';
      badge.style.background = CONFIG.macroMode ? '#f44336' : '#666';
      console.log('Macro Mode:', CONFIG.macroMode ? '🤖 ON' : '👤 OFF');
    });

    document.getElementById('auto-run-toggle').addEventListener('change', (e) => {
      CONFIG.autoRun = e.target.checked;
      saveConfig();
      console.log('Auto Run:', CONFIG.autoRun ? 'ON' : 'OFF');
    });

    document.getElementById('loop-count-input').addEventListener('change', (e) => {
      CONFIG.loopCount = parseInt(e.target.value) || 100;
      saveConfig();
      updateLoopProgress();
      console.log('Loop Count:', CONFIG.loopCount);
    });

    document.getElementById('start-macro-btn').addEventListener('click', () => {
      CONFIG.enabled = !CONFIG.enabled;
      saveConfig();

      const btn = document.getElementById('start-macro-btn');
      if (CONFIG.enabled) {
        btn.textContent = '⏸️ 중지';
        btn.style.background = 'linear-gradient(135deg, #f44336, #d32f2f)';
        console.log('🚀 매크로 시작!');
        updateStatus('시작됨');
        executePageAction();
      } else {
        btn.textContent = '▶️ 시작';
        btn.style.background = 'linear-gradient(135deg, #4CAF50, #45a049)';
        console.log('⏸️ 매크로 중지');
        updateStatus('중지됨');
      }
    });

    document.getElementById('reset-macro-btn').addEventListener('click', () => {
      CONFIG.currentLoop = 0;
      CONFIG.enabled = false;
      saveConfig();
      updateLoopProgress();
      document.getElementById('start-macro-btn').textContent = '▶️ 시작';
      document.getElementById('start-macro-btn').style.background = 'linear-gradient(135deg, #4CAF50, #45a049)';
      console.log('🔄 초기화 완료');
      updateStatus('초기화됨');
    });

    updateLoopProgress();
  }

  function updateStatus(message, type = 'info') {
    const statusEl = document.getElementById('macro-status');
    if (!statusEl) return;

    const colors = {
      info: '#4CAF50',
      success: '#00C853',
      error: '#f44336',
      warning: '#FF9800'
    };

    const icons = {
      info: '🔵',
      success: '✅',
      error: '❌',
      warning: '⚠️'
    };

    statusEl.innerHTML = `
            <div style="display: flex; align-items: center; gap: 6px;">
                <span>${icons[type]}</span>
                <span style="color: ${colors[type]}; font-weight: 500;">${message}</span>
            </div>
            <div style="font-size: 10px; color: #666; margin-top: 4px;">
                ${new Date().toLocaleTimeString('ko-KR')}
            </div>
        `;
  }

  function updateLoopProgress() {
    const progressEl = document.getElementById('loop-progress');
    if (progressEl) {
      progressEl.textContent = `${CONFIG.currentLoop}/${CONFIG.loopCount}`;
    }
  }

  /* ========================================
     유틸리티 함수들
     ======================================== */

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  console.log('🎯 매크로 시뮬레이터 준비 완료!');

})();
