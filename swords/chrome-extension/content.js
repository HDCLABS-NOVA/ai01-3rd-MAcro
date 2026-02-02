/**
 * Content Script - Main Entry Point
 * Initializes FSM and handles page-level logic
 */

(function() {
  'use strict';

  // Check if already initialized
  if (window.SwordAutomation) {
    logger.warn('ALREADY_INITIALIZED');
    return;
  }

  class SwordAutomation {
    constructor() {
      this.fsm = new FSM('IDLE');
      this.recoveryManager = new RecoveryManager();
      this.initialized = false;
    }

    async initialize() {
      if (this.initialized) return;

      logger.info('SWORD_AUTOMATION_INIT', {
        url: location.href,
        site: getSiteConfig() ? 'Supported' : 'Unsupported'
      });

      // Register all states
      this.registerStates();

      // Add debug overlay (if enabled)
      if (await this.isDebugMode()) {
        this.injectDebugOverlay();
      }

      this.initialized = true;

      // Notify background that content script is ready (if chrome API available)
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
        try {
          chrome.runtime.sendMessage({
            type: 'CONTENT_READY',
            payload: {url: location.href}
          });
        } catch (e) {
          // Ignore if background not available
        }
      }

      logger.info('INITIALIZATION_COMPLETE');
    }

    registerStates() {
      this.fsm
        .registerState('IDLE', new IdleState())
        .registerState('WAIT_OPEN', new WaitOpenState())
        .registerState('CLICK_START', new ClickStartState())
        .registerState('HANDLE_POPUP', new HandlePopupState())
        .registerState('SELECT_ZONE', new SelectZoneState())
        .registerState('SELECT_SEAT', new SelectSeatState())
        .registerState('CONFIRM', new ConfirmState())
        .registerState('PAYMENT', new PaymentState())
        .registerState('HANDLE_CAPTCHA', new HandleCaptchaState())
        .registerState('ERROR', new ErrorState())
        .registerState('FAILED', new FailedState());

      // Listen to state transitions (explicit bind)
      this.fsm.on('transition', this.onStateTransition.bind(this));

      logger.info('STATES_REGISTERED', {count: this.fsm.states.size});
      
      // Initialize the initial IDLE state
      const idleState = this.fsm.states.get('IDLE');
      if (idleState) {
        console.log('[FSM] Initializing IDLE state...');
        idleState.onEnter({}).catch(err => {
          logger.error('IDLE_INIT_ERROR', {error: err.message});
        });
      }
    }

    setupMessageHandling() {
      // In MAIN world, chrome.runtime.onMessage might not be available
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
          this.handleMessage(message, sender, sendResponse);
          return true; // Keep async channel open
        });
      }
    }

    async handleMessage(message, sender, sendResponse) {
      logger.debug('MESSAGE_RECEIVED', {type: message.type});

      switch (message.type) {
        case 'START_AUTOMATION':
          await this.startAutomation(message.payload);
          sendResponse({success: true});
          break;

        case 'STOP_AUTOMATION':
          await this.stopAutomation();
          sendResponse({success: true});
          break;

        case 'GET_STATE':
          sendResponse(this.fsm.getState());
          break;

        case 'RESET':
          await this.fsm.reset();
          sendResponse({success: true});
          break;

        case 'TOGGLE_DEBUG':
          this.toggleDebugOverlay();
          sendResponse({success: true});
          break;

        default:
          logger.warn('UNKNOWN_MESSAGE_TYPE', {type: message.type});
          sendResponse({success: false, error: 'Unknown message type'});
      }
    }

    async startAutomation(config) {
      logger.info('START_AUTOMATION', config);

      // Force Reset if running (allows user to restart if stuck)
      if (this.fsm.currentState !== 'IDLE') {
        logger.info('FORCE_RESTART', {from: this.fsm.currentState});
        await this.fsm.reset();
        // Give it a moment to reset
        await new Promise(r => setTimeout(r, 100));
      }

      // Update context with config
      this.fsm.context.config = config;
      
      // Start booking flow logging (check if auto-loop is enabled)
      const autoLoopCount = config.autoLoopCount || 1;
      if (autoLoopCount > 1) {
        this.fsm.enableAutoLoop(autoLoopCount);
      } else {
        this.fsm.startBookingFlow(1);
      }
      
      // Save for auto-resume (Persistence)
      try {
        sessionStorage.setItem('SWORD_CONFIG', JSON.stringify(config));
        sessionStorage.setItem('SWORD_RUNNING', 'true');
      } catch (e) {}

      // Get the IDLE state and call handleStart directly
      const idleState = this.fsm.states.get('IDLE');
      if (idleState) {
        console.log('[SwordAutomation] Calling IdleState.handleStart directly');
        await idleState.handleStart(config);
      }
    }

    async stopAutomation() {
      logger.info('STOP_AUTOMATION');
      // Clear persistence
      try {
        sessionStorage.removeItem('SWORD_RUNNING');
      } catch(e) {}
      await this.fsm.reset();
    }

    // Auto-resume check
    async checkAutoResume() {
      try {
        const isRunning = sessionStorage.getItem('SWORD_RUNNING');
        const savedConfig = sessionStorage.getItem('SWORD_CONFIG');
        
        // Check URL for booking flow indicators
        const isBookingPage = location.href.includes('/section/') || 
                            location.href.includes('/booking/') || 
                            location.href.includes('/step') ||
                            location.href.includes('perfCode');

        logger.info('CHECK_AUTO_RESUME', { isRunning, hasConfig: !!savedConfig, isBookingPage });

        if ((isRunning === 'true' || isBookingPage) && savedConfig) {
          const config = JSON.parse(savedConfig);
          logger.info('AUTO_RESUME_DETECTED', { url: location.href, reason: isRunning ? 'flag' : 'url_context' });
          
          // Wait a bit for page to stabilize
          await new Promise(r => setTimeout(r, 1000));
          
          this.startAutomation(config);
        } else {
          logger.info('AUTO_RESUME_SKIPPED', { reason: 'No running state or booking context found' });
        }
      } catch (e) {
        logger.error('AUTO_RESUME_ERROR', {error: e.message});
      }
    }

    // ... existing debugging methods ...
    onStateTransition(data) {
      // Log stage for booking flow tracking
      this.fsm.logStage(data.to, {
        from: data.from,
        transitionData: data.data,
        url: location.href
      });

      // Complete booking flow on terminal states
      if (['PAYMENT', 'FAILED', 'ERROR'].includes(data.to)) {
        const status = data.to === 'PAYMENT' ? 'completed' : 'failed';
        this.fsm.completeBookingFlow(status);
      }

      // Clear persistence on terminal states (except IDLE to prevent clearing on reset)
      if (['PAYMENT', 'FAILED'].includes(data.to)) {
         try {
           sessionStorage.removeItem('SWORD_RUNNING');
         } catch(e) {}
      }

      // Send state update to background (if API available)
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
        try {
          chrome.runtime.sendMessage({
            type: 'STATE_UPDATE',
            payload: {
              from: data.from,
              to: data.to,
              context: this.fsm.context
            }
          }, () => {
            if (chrome.runtime.lastError) {
              // Ignore background connection errors
            }
          });
        } catch (e) {
          // Ignore if background not available
        }
      }

      // Update debug overlay
      if (this.debugOverlay) {
        this.debugOverlay.update(data.to, this.fsm.context);
      }
    }

    async isDebugMode() {
      if (typeof chrome === 'undefined' || !chrome.storage) {
        return false;
      }
      return new Promise((resolve) => {
        chrome.storage.local.get(['debugMode'], (result) => {
          resolve(result.debugMode || false);
        });
      });
    }



    injectDebugOverlay() {
      const overlay = document.createElement('div');
      overlay.id = 'sword-debug-overlay';
      overlay.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        background: rgba(0, 0, 0, 0.8);
        color: #00ff00;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        z-index: 999998;
        max-width: 300px;
        backdrop-filter: blur(10px);
      `;

      overlay.innerHTML = `
        <div style="font-weight: bold; margin-bottom: 8px; color: #00ffff;">🗡️ SWORD Debug</div>
        <div id="sword-debug-state">State: IDLE</div>
        <div id="sword-debug-retries">Retries: 0</div>
        <div id="sword-debug-time">Time: --:--</div>
      `;

      document.body.appendChild(overlay);

      this.debugOverlay = {
        element: overlay,
        update: (state, context) => {
          const stateEl = overlay.querySelector('#sword-debug-state');
          const retriesEl = overlay.querySelector('#sword-debug-retries');
          const timeEl = overlay.querySelector('#sword-debug-time');

          stateEl.textContent = `State: ${state}`;
          retriesEl.textContent = `Retries: ${context.retryCount}`;
          
          if (context.startTime) {
            const elapsed = Math.floor((Date.now() - context.startTime) / 1000);
            const mins = Math.floor(elapsed / 60);
            const secs = elapsed % 60;
            timeEl.textContent = `Time: ${mins}:${secs.toString().padStart(2, '0')}`;
          }
        }
      };
    }

    toggleDebugOverlay() {
      const overlay = document.querySelector('#sword-debug-overlay');
      if (overlay) {
        overlay.remove();
        this.debugOverlay = null;
      } else {
        this.injectDebugOverlay();
      }
    }
  }

  // Initialize when DOM is ready
  let automation;
  
  function initAutomation() {
    automation = new SwordAutomation();
    automation.initialize();
    
    // Explicitly assign to window (global scope)
    window.SwordAutomation = automation;
    
    // Check for auto-resume
    automation.checkAutoResume();
    
    // Debug confirmation - this should show in console
    console.log('[SWORD] window.SwordAutomation assigned:', typeof window.SwordAutomation);
    console.log('[SWORD] Verification:', window.SwordAutomation === automation);
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAutomation);
  } else {
    initAutomation();
  }

})();

// Double-check: Also try assigning after IIFE completes
// This ensures it's in the true global scope
setTimeout(() => {
  if (typeof window.SwordAutomation === 'undefined') {
    console.error('[SWORD] SwordAutomation still undefined after init!');
  } else {
    console.log('[SWORD] Global check passed:', typeof window.SwordAutomation);
  }
}, 100);
