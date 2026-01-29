/**
 * Base State Class
 * All state handlers inherit from this
 */

class BaseState {
  constructor() {
    this.fsm = null; // Set by FSM during registration
    this.name = '';
    this.entryTime = null;
    this.observers = [];
  }

  /**
   * Called when entering this state
   * @param {Object} data - Data passed from previous state
   */
  async onEnter(data) {
    this.entryTime = Date.now();
    logger.debug(`${this.name}_ENTER`, data);
  }

  /**
   * Main execution logic (override in subclasses)
   */
  async execute() {
    throw new Error(`${this.name}: execute() not implemented`);
  }

  /**
   * Called when exiting this state
   */
  async onExit() {
    // Cleanup observers
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
    
    const duration = Date.now() - this.entryTime;
    logger.debug(`${this.name}_EXIT`, {duration});
  }

  /**
   * Validate if transition to target state is allowed
   * @param {string} targetState
   * @returns {boolean}
   */
  canTransition(targetState) {
    // Default: allow ERROR transitions always
    if (targetState === 'ERROR') return true;
    
    // Override in subclasses for specific validation
    return true;
  }

  /**
   * Helper: Wait for element with MutationObserver
   */
  async waitForElement(selector, timeout = 5000) {
    const element = document.querySelector(selector);
    if (element) return element;

    return new Promise((resolve, reject) => {
      const observer = new MutationObserver(() => {
        const el = document.querySelector(selector);
        if (el) {
          observer.disconnect();
          resolve(el);
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true
      });

      this.observers.push(observer);

      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Timeout waiting for ${selector}`));
      }, timeout);
    });
  }

  /**
   * Helper: Wait for element to disappear
   */
  async waitForElementRemoval(selector, timeout = 5000) {
    if (!document.querySelector(selector)) return true;

    return new Promise((resolve, reject) => {
      const observer = new MutationObserver(() => {
        if (!document.querySelector(selector)) {
          observer.disconnect();
          resolve(true);
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true
      });

      this.observers.push(observer);

      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Timeout waiting for ${selector} removal`));
      }, timeout);
    });
  }

  /**
   * Helper: Safe click with human-like behavior
   */
  async safeClick(element, delay = 0) {
    if (!element) throw new Error('Element is null');
    
    if (!element.offsetParent && element.tagName !== 'BODY') {
      throw new Error('Element not visible');
    }

    if (element.disabled) {
      throw new Error('Element is disabled');
    }

    // Human-like pre-click delay (100-300ms)
    const preDelay = delay > 0 ? delay : (100 + Math.random() * 200);
    await sleep(preDelay);

    // Simulate human interaction sequence
    // 1. Hover (人がマウスを要素の上に移動)
    element.dispatchEvent(new MouseEvent('mouseover', {
      bubbles: true,
      cancelable: true,
      view: window
    }));
    
    // Brief hover pause (50-150ms - 人が要素を確認する時間)
    await sleep(50 + Math.random() * 100);
    
    // 2. Mouse down (人がクリックを開始)
    element.dispatchEvent(new MouseEvent('mousedown', {
      bubbles: true,
      cancelable: true,
      view: window,
      button: 0
    }));
    
    // Click press duration (30-100ms - 人の自然なクリック時間)
    await sleep(30 + Math.random() * 70);
    
    // 3. Mouse up (人がクリックを完了)
    element.dispatchEvent(new MouseEvent('mouseup', {
      bubbles: true,
      cancelable: true,
      view: window,
      button: 0
    }));
    
    // 4. Actual click event
    element.click();
    
    // Post-click delay (100-200ms - ページの反応を待つ)
    await sleep(100 + Math.random() * 100);
    
    logger.debug('HUMAN_CLICK', {
      tag: element.tagName,
      id: element.id,
      class: element.className
    });
  }

  /**
   * Helper: Get current context
   */
  getContext() {
    return this.fsm.context;
  }

  /**
   * Helper: Update context
   */
  updateContext(updates) {
    Object.assign(this.fsm.context, updates);
  }

  /**
   * Helper: Transition to next state
   */
  async transitionTo(nextState, data = {}, reason = '') {
    await this.fsm.transition(nextState, data, reason);
  }

  /**
   * Helper: Throw recoverable error
   */
  throwRecoverable(message) {
    const error = new Error(message);
    error.recoverable = true;
    throw error;
  }

  /**
   * Helper: Throw fatal error
   */
  throwFatal(message) {
    const error = new Error(message);
    error.recoverable = false;
    throw error;
  }
}

// Export
if (typeof window !== 'undefined') {
  window.BaseState = BaseState;
}
