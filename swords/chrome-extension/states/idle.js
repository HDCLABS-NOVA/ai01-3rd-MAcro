/**
 * IDLE State - Waiting for user to start
 */

class IdleState extends BaseState {
  async onEnter(data) {
    await super.onEnter(data);
    
    // Initialize context
    this.updateContext({
      retryCount: 0,
      errors: [],
      seats: [],
      selectedSeats: [],
      unavailableSeats: new Set(),
    });

    logger.info('IDLE_STATE', {message: 'Waiting for user to start'});
    
    // Listen for start command via postMessage (from content.js)
    this.startListener = (event) => {
      console.log('[IdleState] Received message:', event.data);
      if (event.data && event.data.type === 'START_AUTOMATION') {
        console.log('[IdleState] Handling START_AUTOMATION');
        this.handleStart(event.data.payload);
      }
    };

    window.addEventListener('message', this.startListener);
    console.log('[IdleState] Listener registered');
  }

  async handleStart(config) {
    console.log('[IdleState] handleStart called with:', config);
    logger.info('START_REQUESTED', config);
    
    // Extract performance information from page
    const performanceInfo = this.extractPerformanceInfo();
    
    // Update FSM booking flow with performance info
    if (this.fsm && this.fsm.bookingFlow) {
      this.fsm.bookingFlow.performanceId = performanceInfo.id;
      this.fsm.bookingFlow.performanceName = performanceInfo.name;
      logger.info('PERFORMANCE_INFO_EXTRACTED', performanceInfo);
    }
    
    // Store config in context
    this.updateContext({
      config,
      startTime: Date.now()
    });

    // Transition based on whether we have a target time
    if (config.targetTime && config.targetTime > Date.now()) {
      console.log('[IdleState] Transitioning to WAIT_OPEN');
      await this.transitionTo('WAIT_OPEN', {
        targetTime: config.targetTime
      }, 'User started with wait time');
    } else {
      console.log('[IdleState] Transitioning to CLICK_START');
      await this.transitionTo('CLICK_START', {}, 'User started immediately');
    }
  }

  /**
   * Extract performance information from current page
   * @returns {Object} {id, name}
   */
  extractPerformanceInfo() {
    // Try to extract from page title or H1
    let performanceName = document.title;
    
    // Try H1 first
    const h1 = document.querySelector('h1');
    if (h1 && h1.textContent.trim()) {
      performanceName = h1.textContent.trim();
    }
    
    // Clean up name (remove extra whitespace, special characters)
    performanceName = performanceName.replace(/\s+/g, ' ').trim();
    
    // Generate performance ID from name or URL
    let performanceId = 'UNKNOWN';
    
    // Try to extract from URL (e.g., concert/IU001)
    const urlMatch = window.location.href.match(/concert[s]?\/([A-Za-z0-9]+)/);
    if (urlMatch) {
      performanceId = urlMatch[1];
    } else {
      // Generate from name (first letters + number)
      const words = performanceName.split(' ');
      const initials = words.slice(0, 2).map(w => w.charAt(0).toUpperCase()).join('');
      const timestamp = Date.now().toString().slice(-3);
      performanceId = `${initials}${timestamp}`;
    }
    
    return {
      id: performanceId,
      name: performanceName
    };
  }

  async onExit() {
    window.removeEventListener('message', this.startListener);
    await super.onExit();
  }

  canTransition(targetState) {
    // Can only go to WAIT_OPEN or CLICK_START from IDLE
    return ['WAIT_OPEN', 'CLICK_START', 'ERROR'].includes(targetState);
  }
}

if (typeof window !== 'undefined') {
  window.IdleState = IdleState;
}
