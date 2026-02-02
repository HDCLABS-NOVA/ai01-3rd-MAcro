/**
 * HANDLE_CAPTCHA State - Detect and handle CAPTCHA with auto-solve
 */

class HandleCaptchaState extends BaseState {
  async onEnter(data) {
    await super.onEnter(data);
    logger.info('CAPTCHA_DETECTED');

    // Ensure persistence is set so we resume after reload
    try {
      sessionStorage.setItem('SWORD_RUNNING', 'true');
    } catch(e) {}

    // Show alert overlay
    this.showCaptchaAlert();

    // Play alert sound
    this.playAlertSound();

    // Focus input if found
    const config = getSiteConfig();
    if (config?.captcha?.input) {
      const input = smartSelect(config.captcha.input);
      if (input) {
        input.focus();
        input.style.border = '3px solid #f5576c';
        input.style.boxShadow = '0 0 10px #f5576c';
      }
    }

    // Try automatic solving, then start polling
    await this.tryAutoSolve();
  }

  async tryAutoSolve() {
    const config = getSiteConfig();
    
    // Try API auto-solve first
    logger.info('CAPTCHA_AUTO_SOLVE_ATTEMPT');
    
    try {
      const solved = await this.callCaptchaAPI();
      
      if (solved) {
        logger.info('CAPTCHA_AUTO_SOLVED');
        
        // Wait for page to process
        await sleep(2000);
        
        // Check if CAPTCHA is gone
        const captchaStillPresent = smartSelect(config.captcha.selectors);
        
        if (!captchaStillPresent) {
          logger.info('CAPTCHA_CLEARED_AUTO');
          this.transitionTo('CLICK_START', {}, 'Captcha auto-solved');
          return;
        } else {
          logger.warn('CAPTCHA_AUTO_FAILED', {message: 'Still present after auto-solve'});
        }
      }
    } catch (error) {
      logger.warn('CAPTCHA_API_ERROR', {error: error.message});
    }
    
    // Fallback to manual polling
    this.startPolling();
  }

  /**
   * Call CAPTCHA API server for automatic solving
   */
  async callCaptchaAPI() {
    try {
      const response = await fetch('http://localhost:5000/solve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          use_screen_capture: true
        })
      });

      if (!response.ok) {
        logger.debug('CAPTCHA_API_HTTP_ERROR', {status: response.status});
        return false;
      }

      const result = await response.json();
      
      if (result.success) {
        logger.info('CAPTCHA_API_SUCCESS', {text: result.text});
        return true;
      } else {
        logger.debug('CAPTCHA_API_NO_DETECT', {message: result.message});
        return false;
      }
      
    } catch (error) {
      logger.debug('CAPTCHA_API_UNAVAILABLE', {
        hint: 'Start API: python swords/captcha_api_server.py'
      });
      return false;
    }
  }

  showCaptchaAlert() {
    this.overlay = document.createElement('div');
    this.overlay.id = 'sword-captcha-alert';
    this.overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100vh;
      background: rgba(255, 165, 0, 0.2);
      pointer-events: none;
      z-index: 999990;
      display: flex;
      justify-content: center;
      align-items: center;
    `;

    const box = document.createElement('div');
    box.style.cssText = `
      background: white;
      padding: 30px;
      border-radius: 15px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.5);
      text-align: center;
      border: 4px solid orange;
      pointer-events: auto;
      animation: pulse 1s infinite alternate;
    `;

    box.innerHTML = `
      <div style="font-size: 48px; margin-bottom: 20px;">🔐</div>
      <h2 style="margin: 0 0 10px; color: orange;">CAPTCHA Detected!</h2>
      <p style="font-size: 18px; margin: 0 0 10px;">Attempting automatic solve...</p>
      <div style="font-size: 14px; color: #666;">If auto-solve fails, please solve manually.</div>
      <div style="font-size: 12px; color: #888; margin-top: 10px;">Automation will resume automatically.</div>
    `;

    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        from { transform: scale(1); }
        to { transform: scale(1.05); }
      }
    `;

    this.overlay.appendChild(style);
    this.overlay.appendChild(box);
    document.body.appendChild(this.overlay);
  }

  playAlertSound() {
    // Simple beep pattern
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      
      const playBeep = (freq, duration, time) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = freq;
        osc.type = 'square';
        osc.start(time);
        osc.stop(time + duration);
      };

      const now = ctx.currentTime;
      playBeep(800, 0.1, now);
      playBeep(800, 0.1, now + 0.2);
      playBeep(800, 0.1, now + 0.4);
    } catch(e) {
      // Audio context might not be available
    }
  }

  startPolling() {
    const config = getSiteConfig();
    logger.info('CAPTCHA_MANUAL_WAIT');
    let attempts = 0;

    this.pollInterval = setInterval(() => {
      attempts++;
      
      // Check if CAPTCHA elements are gone
      const captchaContainer = smartSelect(config.captcha.selectors);
      
      if (!captchaContainer) {
        // CAPTCHA gone!
        logger.info('CAPTCHA_RESOLVED_MANUAL');
        this.transitionTo('CLICK_START', {}, 'Captcha resolved manually');
        return;
      }

      // Or check if we navigated away (URL change)
      if (!location.href.includes('captcha') && !document.querySelector('#captcha')) {
         logger.info('CAPTCHA_PAGE_EXITED');
         this.transitionTo('CLICK_START', {}, 'Navigated away from captcha');
         return;
      }

      // Timeout after 5 minutes (600 checks at 500ms)
      if (attempts > 600) {
        logger.error('CAPTCHA_TIMEOUT');
        this.throwRecoverable('CAPTCHA resolution timeout after 5 minutes');
      }

    }, 500);
  }

  async onExit() {
    if (this.pollInterval) clearInterval(this.pollInterval);
    if (this.overlay) this.overlay.remove();
    await super.onExit();
  }

  canTransition(targetState) {
    return ['CLICK_START', 'SELECT_ZONE', 'ERROR'].includes(targetState);
  }
}

if (typeof window !== 'undefined') {
  window.HandleCaptchaState = HandleCaptchaState;
}
