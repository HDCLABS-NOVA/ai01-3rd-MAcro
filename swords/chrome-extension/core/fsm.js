/**
 * Finite State Machine Core Engine
 * Manages state transitions, history, and context
 */

class FSM {
  constructor(initialState = 'IDLE') {
    this.states = new Map();
    this.currentState = initialState;
    this.previousState = null;
    this.history = [];
    this.context = {
      retryCount: 0,
      errors: [],
      startTime: null,
      config: {}
    };
    this.listeners = new Map();
    this.maxHistorySize = 50;
    
    // Booking flow logging
    this.bookingFlow = {
      flowId: null,
      performanceId: null,  // 공연 ID (e.g., "IU001")
      performanceName: null,  // 공연명
      startTime: null,
      stages: {},
      attemptNumber: 0,
      totalAttempts: 0,
      autoLoop: false,
      status: 'in_progress'  // 'success', 'failed', 'in_progress'
    };
  }

  /**
   * Register a state handler
   */
  registerState(name, stateInstance) {
    stateInstance.fsm = this;
    stateInstance.name = name;
    this.states.set(name, stateInstance);
    return this;
  }

  /**
   * Transition to a new state
   */
  async transition(nextState, data = {}, reason = '') {
    if (!this.states.has(nextState)) {
      throw new Error(`Unknown state: ${nextState}`);
    }

    const currentHandler = this.states.get(this.currentState);
    const nextHandler = this.states.get(nextState);

    // Validation
    if (currentHandler && !currentHandler.canTransition(nextState)) {
      logger.warn('TRANSITION_BLOCKED', {
        from: this.currentState,
        to: nextState,
        reason: 'Validation failed'
      });
      return false;
    }

    logger.info('STATE_TRANSITION', {
      from: this.currentState,
      to: nextState,
      reason,
      data
    });

    try {
      // Exit current state
      if (currentHandler) {
        await currentHandler.onExit();
      }

      // Record history
      this.history.push({
        from: this.currentState,
        to: nextState,
        timestamp: Date.now(),
        reason,
        data: {...data}
      });

      // Trim history if too large
      if (this.history.length > this.maxHistorySize) {
        this.history = this.history.slice(-this.maxHistorySize);
      }

      // Update state
      this.previousState = this.currentState;
      this.currentState = nextState;

      // Emit transition event
      this.emit('transition', {
        from: this.previousState,
        to: nextState,
        data
      });

      // Enter new state
      await nextHandler.onEnter(data);

      // Auto-execute if state supports it
      if (typeof nextHandler.execute === 'function') {
        await nextHandler.execute();
      }

      return true;

    } catch (error) {
      logger.error('TRANSITION_ERROR', {
        from: this.currentState,
        to: nextState,
        error: error.message,
        stack: error.stack
      });

      // Transition to ERROR state
      if (nextState !== 'ERROR') {
        await this.handleError(error);
      }

      return false;
    }
  }

  /**
   * Handle errors by transitioning to ERROR state
   */
  async handleError(error) {
    this.context.errors.push({
      error: error.message,
      state: this.currentState,
      timestamp: Date.now(),
      stack: error.stack
    });

    await this.transition('ERROR', {
      error,
      recoverable: error.recoverable !== false
    }, 'Error occurred');
  }

  /**
   * Reset the FSM to initial state
   */
  async reset() {
    logger.info('FSM_RESET', {currentState: this.currentState});
    
    // Clear context but preserve config
    const savedConfig = this.context.config;
    this.context = {
      retryCount: 0,
      errors: [],
      startTime: null,
      config: savedConfig
    };

    await this.transition('IDLE', {}, 'Reset');
  }

  /**
   * Event emitter pattern
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      for (const callback of this.listeners.get(event)) {
        try {
          callback(data);
        } catch (error) {
          logger.error('EVENT_LISTENER_ERROR', {event, error: error.message});
        }
      }
    }
  }

  /**
   * Get current state info
   */
  getState() {
    return {
      current: this.currentState,
      previous: this.previousState,
      context: {...this.context},
      history: this.history.slice(-10) // Last 10 transitions
    };
  }

  /**
   * Check if can transition to target state
   */
  canTransitionTo(targetState) {
    const currentHandler = this.states.get(this.currentState);
    return currentHandler ? currentHandler.canTransition(targetState) : false;
  }

  /**
   * Pause/Resume (useful for debugging)
   */
  pause() {
    this.paused = true;
    logger.info('FSM_PAUSED');
  }

  resume() {
    this.paused = false;
    logger.info('FSM_RESUMED');
  }

  /**
   * Execute current state (manual trigger)
   */
  async executeCurrent() {
    if (this.paused) {
      logger.warn('FSM_PAUSED', {action: 'execute blocked'});
      return;
    }

    const handler = this.states.get(this.currentState);
    if (handler && typeof handler.execute === 'function') {
      await handler.execute();
    }
  }

  /**
   * Start a new booking flow for logging
   */
  startBookingFlow(totalAttempts = 1) {
    this.bookingFlow.flowId = `flow_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    this.bookingFlow.startTime = Date.now();
    this.bookingFlow.stages = {};
    this.bookingFlow.attemptNumber++;
    this.bookingFlow.totalAttempts = totalAttempts;
    this.bookingFlow.autoLoop = totalAttempts > 1;

    logger.info('BOOKING_FLOW_STARTED', {
      flowId: this.bookingFlow.flowId,
      attemptNumber: this.bookingFlow.attemptNumber,
      totalAttempts: this.bookingFlow.totalAttempts
    });
  }

  /**
   * Log a stage in the booking flow
   */
  logStage(stageName, data = {}) {
    this.bookingFlow.stages[stageName] = {
      timestamp: Date.now(),
      state: this.currentState,
      ...data
    };
  }

  /**
   * Complete and save the current booking flow
   */
  async completeBookingFlow(status = 'completed') {
    // Update status
    this.bookingFlow.status = status;
    
    // Generate filename: [날짜]_[공연ID]_[flow_id]_[결제성공여부].json
    const date = new Date();
    const dateStr = date.toISOString().split('T')[0].replace(/-/g, ''); // YYYYMMDD
    const performanceId = this.bookingFlow.performanceId || 'UNKNOWN';
    const flowIdShort = this.bookingFlow.flowId ? this.bookingFlow.flowId.split('_').pop() : 'unknown';
    const statusStr = status === 'completed' ? 'success' : 'failed';
    const filename = `${dateStr}_${performanceId}_${flowIdShort}_${statusStr}`;
    
    const flowData = {
      flowId: this.bookingFlow.flowId,
      performanceId: this.bookingFlow.performanceId,
      performanceName: this.bookingFlow.performanceName,
      attemptNumber: this.bookingFlow.attemptNumber,
      totalAttempts: this.bookingFlow.totalAttempts,
      status: statusStr,
      duration: Date.now() - this.bookingFlow.startTime,
      completedAt: new Date().toISOString(),
      filename
    };

    // Send to server with custom filename
    const sent = await logger.sendToServer(flowData, this.bookingFlow.stages, filename);

    logger.info('BOOKING_FLOW_COMPLETED', {
      ...flowData,
      serverLogged: sent
    });

    // If auto-loop is enabled and we haven't reached target
    if (this.bookingFlow.autoLoop && this.bookingFlow.attemptNumber < this.bookingFlow.totalAttempts) {
      logger.info('AUTO_LOOP_CONTINUE', {
        current: this.bookingFlow.attemptNumber,
        target: this.bookingFlow.totalAttempts
      });

      // Wait a bit before next attempt
      setTimeout(() => {
        this.startNextAttempt();
      }, 3000); // 3 second delay between attempts
    } else if (this.bookingFlow.attemptNumber >= this.bookingFlow.totalAttempts) {
      logger.info('AUTO_LOOP_COMPLETED', {
        totalAttempts: this.bookingFlow.attemptNumber
      });
    }
  }

  /**
   * Start the next booking attempt in auto-loop mode
   */
  async startNextAttempt() {
    logger.info('STARTING_NEXT_ATTEMPT', {
      attemptNumber: this.bookingFlow.attemptNumber + 1
    });

    // Reset FSM to IDLE
    await this.reset();

    // Start new flow with same total
    const totalAttempts = this.bookingFlow.totalAttempts;
    this.startBookingFlow(totalAttempts);

    // Navigate to start page
    window.location.href = 'http://localhost:8000/html/index.html';
  }

  /**
   * Enable auto-loop mode for collecting multiple logs
   */
  enableAutoLoop(targetCount = 1000) {
    logger.info('AUTO_LOOP_ENABLED', {targetCount});
    this.startBookingFlow(targetCount);
  }
}

// Export for use in content script
if (typeof window !== 'undefined') {
  window.FSM = FSM;
}
