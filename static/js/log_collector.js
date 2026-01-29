/**
 * 로그 수집 중앙 관리 라이브러리
 * 각 페이지에서 사용하는 로그 수집 기능을 통합 관리
 */
const LogCollector = {

  // ============== 공통 유틸리티 ==============

  /**
   * 세션 ID 생성
   * @param {string} prefix - 접두사 (예: 'perf', 'que', 'book')
   * @returns {string} 생성된 세션 ID
   * from: perf_list.js, queue.js, section_select.js
   */
  generateSessionId: function (prefix) {
    return prefix + '_' + Math.random().toString(36).substr(2, 8);
  },

  /**
   * 브라우저 및 환경 정보 수집 (봇 탐지용)
   * @returns {object} 브라우저 정보 객체
   * from: section_select.js
   */
  initBrowserInfo: function () {
    return {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      cookieEnabled: navigator.cookieEnabled,
      doNotTrack: navigator.doNotTrack,
      hardwareConcurrency: navigator.hardwareConcurrency,
      deviceMemory: navigator.deviceMemory,
      maxTouchPoints: navigator.maxTouchPoints,
      language: navigator.language || navigator.userLanguage,
      webdriver: navigator.webdriver,  // Headless Chrome 탐지
      screen: {
        width: screen.width,
        height: screen.height,
        colorDepth: screen.colorDepth,
        pixelRatio: window.devicePixelRatio
      },
      window: {
        outerWidth: window.outerWidth,
        outerHeight: window.outerHeight,
        innerWidth: window.innerWidth, // Viewport width
        innerHeight: window.innerHeight // Viewport height
      },
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
    };
  },

  /**
   * 마우스 궤적 수집 리스너 설정
   * @param {Array} logArray - 마우스 궤적을 저장할 배열
   * @param {number} interval - 수집 간격 (ms)
   * @param {number} startTime - 시작 시간
   * @param {boolean} normalized - 정규화 좌표 포함 여부
   * from: perf_list.js, queue.js, section_select.js, seat_select.js
   */
  // ============== Click Metrics Tracking (매크로 탐지용) ==============

  _lastClickMetrics: {
    mousedownTime: 0,
    mouseupTime: 0,
    isTrusted: true
  },

  // 페이지 로드 시 클릭 트래킹 시작
  initClickMetrics: function () {
    document.addEventListener('mousedown', (e) => {
      this._lastClickMetrics.mousedownTime = Date.now();
      this._lastClickMetrics.isTrusted = e.isTrusted;
    }, true);

    document.addEventListener('mouseup', (e) => {
      this._lastClickMetrics.mouseupTime = Date.now();
      this._lastClickMetrics.isTrusted = e.isTrusted; // update in case it changes
    }, true);
  },

  /**
   * 최근 클릭 이벤트의 메트릭 반환
   * @param {number} clientX - 클릭 X 좌표
   * @param {number} clientY - 클릭 Y 좌표
   * @returns {object} { is_trusted, click_duration, is_integer }
   */
  getClickMetrics: function (clientX, clientY) {
    const duration = this._lastClickMetrics.mouseupTime - this._lastClickMetrics.mousedownTime;
    // 방어 로직: duration이 음수거나 너무 크면(이전 클릭 데이터인 경우) 0 처리
    const validDuration = (duration >= 0 && duration < 5000) ? duration : 0;

    return {
      is_trusted: this._lastClickMetrics.isTrusted,
      click_duration: validDuration,
      is_integer: Number.isInteger(clientX) && Number.isInteger(clientY)
    };
  },

  /**
   * 마우스 궤적 수집 리스너 설정 (Array format [x, y, t] for compression)
   * @param {Array} logArray - 마우스 궤적을 저장할 배열
   * @param {number} interval - 수집 간격 (ms)
   * @param {number} startTime - 시작 시간
   * @param {boolean} normalized - 정규화 좌표 포함 여부 (압축을 위해 false 권장)
   * from: perf_list.js, queue.js, section_select.js, seat_select.js
   */
  initMouseTracking: function (logArray, interval, startTime, normalized = false) {
    let lastMouseTime = 0;

    const handler = (e) => {
      const now = Date.now();
      if (now - lastMouseTime >= interval) {
        // [x, y, timestamp] - 압축 포맷
        const t = startTime ? (now - startTime) : (now - lastMouseTime); // startTime이 없으면 delta

        // 정수 좌표 사용 (매크로 탐지/용량 절감)
        const point = [
          Math.floor(e.clientX),
          Math.floor(e.clientY),
          t
        ];

        logArray.push(point);
        lastMouseTime = now;
      }
    };

    document.addEventListener('mousemove', handler);
    return handler;
  },

  // ============== 페이지별 로그 초기화 ==============

  /**
   * 공연 목록 페이지 로그 초기화
   * @returns {object} 로그 데이터 객체
   * from: perf_list.js
   */
  initPerfListLog: function () {
    const sessionId = this.generateSessionId('perf');
    const logData = {
      session_id: sessionId,
      stage: 'perf',
      page_entry_time: new Date().toISOString(),
      performance_id: null,
      actions: [],
      mouse_trajectory: [],
      card_clicks: [],
      date_selections: [],
      time_selections: []
    };

    // 마우스 궤적 수집 시작 (100ms 간격)
    const pageStartTime = new Date(logData.page_entry_time).getTime();
    this.initMouseTracking(logData.mouse_trajectory, 100, pageStartTime, false);

    return logData;
  },

  /**
   * 대기열 페이지 로그 초기화
   * @param {string} perfId - 공연 ID
   * @param {string} selectedDate - 선택한 날짜
   * @param {string} selectedTime - 선택한 시간
   * @param {number} totalQueue - 전체 대기 인원
   * @param {number} initialPosition - 초기 대기 순번
   * @returns {object} 로그 데이터 객체
   * from: queue.js
   */
  initQueueLog: function (perfId, selectedDate, selectedTime, totalQueue, initialPosition) {
    const sessionId = this.generateSessionId('que');
    const logData = {
      session_id: sessionId,
      stage: 'que',
      performance_id: perfId || '',
      selected_date: selectedDate || '',
      selected_time: selectedTime || '',
      queue_start_time: new Date().toISOString(),
      initial_position: initialPosition || 0,
      total_queue: totalQueue || 0,
      position_updates: [],
      queue_end_time: null,
      final_position: null,
      wait_duration_ms: null,
      mouse_trajectory: []
    };

    // 마우스 궤적 수집 시작 (30ms 간격)
    const startTime = new Date(logData.queue_start_time).getTime();
    this.initMouseTracking(logData.mouse_trajectory, 30, startTime, false);

    return logData;
  },

  /**
   * 예매 세션 로그 초기화 (구역 선택 시작)
   * @param {string} perfId - 공연 ID
   * @param {string} selectedDate - 선택한 날짜
   * @param {string} selectedTime - 선택한 시간
   * @returns {object} 로그 데이터 객체
   * from: section_select.js
   */
  initBookLog: function (perfId, selectedDate, selectedTime) {
    const sessionId = this.generateSessionId('book');
    const bookLogData = {
      session_id: sessionId,
      stage: 'book',
      performance_id: perfId || '',
      selected_date: selectedDate || '',
      selected_time: selectedTime || '',
      booking_start_time: new Date().toISOString(),
      viewport: { w: window.innerWidth, h: window.innerHeight },
      browser_info: this.initBrowserInfo(),
      section_selection: {
        start_time: new Date().toISOString(),
        clicks: [],
        final_section: null,
        final_grade: null,
        end_time: null,
        mouse_trajectory: []
      },
      seat_selection: null,
      discount: null,
      booking_end_time: null
    };

    // sessionStorage에 저장
    this.saveBookLog(bookLogData);

    return bookLogData;
  },

  /**
   * 좌석 선택 페이지 로그 초기화
   * @param {string} sessionId - 세션 ID
   * @returns {object} 로그 데이터 객체
   * from: seat_select.js
   */
  initSeatSelectionLog: function (sessionId) {
    const pageStartTime = Date.now();
    const logData = {
      session_id: sessionId,
      page: 'seat_selection',
      page_entry_time: new Date(pageStartTime).toISOString(),
      mouse_trajectory: [],
      clicks: [],
      hovers: []
    };

    return { logData, pageStartTime };
  },

  // ============== Flow 기반 로그 관리 ==============

  /**
   * Flow 로그 초기화 (예매 시도 시작)
   * @param {string} perfId - 공연 ID
   * @param {string} perfTitle - 공연 제목
   * @param {string} selectedDate - 선택한 날짜
   * @param {string} selectedTime - 선택한 시간
   * @param {string} userId - 사용자 ID
   * @param {string} userEmail - 사용자 이메일
   * @returns {object} flowLog 객체
   * from: perf_list.js
   */
  initFlowLog: function (perfId, perfTitle, selectedDate, selectedTime, userId, userEmail) {
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0].replace(/-/g, '');
    const randomStr = Math.random().toString(36).substr(2, 6);
    const flowId = `flow_${dateStr}_${randomStr}`;
    const sessionId = 'sess_' + Math.random().toString(36).substr(2, 8);

    const flowLog = {
      metadata: {
        flow_id: flowId,
        session_id: sessionId,
        user_id: userId || '',
        user_email: userEmail || '',
        user_ip: null,  // 서버에서 설정
        created_at: now.toISOString(),

        performance_id: perfId || '',
        performance_title: perfTitle || '',
        selected_date: selectedDate || '',
        selected_time: selectedTime || '',

        flow_start_time: now.toISOString(),
        flow_end_time: null,
        total_duration_ms: null,

        is_completed: false,
        completion_status: 'ongoing',
        final_seats: null,
        booking_id: null,

        browser_info: this.initBrowserInfo()
      },
      stages: {}
    };

    sessionStorage.setItem('flowLogData', JSON.stringify(flowLog));
    console.log('Flow log initialized:', flowId);

    // 초기 로그 서버 전송 (파일 생성)
    this.sendFlowLog(flowLog);

    return flowLog;
  },

  /**
   * Stage 데이터 추가 (각 페이지 진입/이탈 시 호출)
   * @param {string} stageName - 단계명 ('perf', 'queue', 'seat', etc.)
   * @param {object} stageData - 단계별 특화 데이터
   */
  addStageToFlow: function (stageName, stageData) {
    try {
      const flowLog = JSON.parse(sessionStorage.getItem('flowLogData') || '{}');
      if (!flowLog.metadata) {
        console.warn('No flow log found to add stage:', stageName);
        return;
      }

      // stageData에 기본 정보 추가
      const enhancedStageData = {
        ...stageData,
        entry_time: stageData.entry_time || new Date().toISOString()
      };

      flowLog.stages[stageName] = enhancedStageData;

      sessionStorage.setItem('flowLogData', JSON.stringify(flowLog));
      console.log('Stage added to flow:', stageName);

      // 변경된 로그 서버 전송 (업데이트)
      this.sendFlowLog(flowLog);

    } catch (e) {
      console.error('Failed to add stage to flow:', e);
      return null;
    }
  },

  /**
   * Flow 로그 완료 처리
   * @param {string} status - 완료 상태 ('success', 'failed_seat_taken', 'failed_timeout', 'failed_abandoned')
   * @param {Array} finalSeats - 최종 선택 좌석
   * @param {string} bookingId - 예매 번호
   * @returns {object|null} 완료된 flowLog 또는 null
   */
  completeFlow: function (status, finalSeats, bookingId) {
    try {
      const flowLog = JSON.parse(sessionStorage.getItem('flowLogData') || '{}');
      if (!flowLog.metadata) {
        console.warn('No flow log found to complete');
        return null;
      }

      const now = new Date();
      const startTime = new Date(flowLog.metadata.flow_start_time);

      flowLog.metadata.flow_end_time = now.toISOString();
      flowLog.metadata.total_duration_ms = now - startTime;
      flowLog.metadata.is_completed = (status === 'success');
      flowLog.metadata.completion_status = status;
      flowLog.metadata.final_seats = finalSeats || null;
      flowLog.metadata.booking_id = bookingId || null;

      // 즉시 sessionStorage에 저장하여 beforeunload 이벤트에서 is_completed 플래그를 확인 가능하게 함
      sessionStorage.setItem('flowLogData', JSON.stringify(flowLog));

      console.log('Flow completed:', status);
      return flowLog;
    } catch (e) {
      console.error('Failed to complete flow:', e);
      return null;
    }
  },

  /**
   * Flow 로그 전송
   * @param {object} flowLog - 전송할 flowLog
   * @returns {Promise} fetch 프로미스
   */
  sendFlowLog: async function (flowLog) {
    try {
      const response = await fetch('/api/flow-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(flowLog)
      });

      if (response.ok) {
        // 누적 업데이트 방식이므로 sessionStorage를 삭제하지 않음
        console.log('Flow log sent successfully');
      }

      return response;
    } catch (error) {
      console.error('Failed to send flow log:', error);
      throw error;
    }
  },

  /**
   * SessionStorage에서 flowLogData 가져오기
   * @returns {object|null} flowLog 또는 null
   */
  getFlowLog: function () {
    try {
      const data = sessionStorage.getItem('flowLogData');
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.error('Failed to get flow log:', e);
      return null;
    }
  },

  // ============== SessionStorage 관리 (Legacy - 하위 호환성) ==============

  /**
   * SessionStorage에서 bookLogData 가져오기
   * @returns {object|null} bookLogData 또는 null
   * from: seat_select.js, discount_select.js, payment.js
   */
  getBookLog: function () {
    try {
      const data = sessionStorage.getItem('bookLogData');
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.error('Failed to get book log:', e);
      return null;
    }
  },

  /**
   * SessionStorage에 bookLogData 저장
   * @param {object} data - 저장할 데이터
   * from: section_select.js, seat_select.js
   */
  saveBookLog: function (data) {
    try {
      sessionStorage.setItem('bookLogData', JSON.stringify(data));
    } catch (e) {
      console.error('Failed to save book log:', e);
    }
  },

  /**
   * SessionStorage에서 bookLogData 제거
   * from: discount_select.js, payment.js
   */
  clearBookLog: function () {
    try {
      sessionStorage.removeItem('bookLogData');
    } catch (e) {
      console.error('Failed to clear book log:', e);
    }
  },

  /**
   * 예매 완료 API 호출 (Legacy - payment.js에서 사용)
   * @param {object} sessionData - 예매 완료 데이터
   * @returns {Promise<object>} API 응답
   */
  sendCompleteLog: async function (sessionData) {
    try {
      const response = await fetch('/api/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sessionData)
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to send complete log:', error);
      return { success: false, error: error.message };
    }
  }

};

// 전역 객체로 노출
window.LogCollector = LogCollector;

// 클릭 지표 수집 자동 시작
LogCollector.initClickMetrics();
