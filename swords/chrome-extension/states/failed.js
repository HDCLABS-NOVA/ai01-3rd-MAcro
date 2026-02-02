/**
 * FAILED State - Terminal state for failed bookings
 */

class FailedState extends BaseState {
  async onEnter(data) {
    await super.onEnter(data);
    logger.error('BOOKING_FAILED', {
      reason: data.reason || 'Unknown',
      error: data.error
    });

    // Show failure overlay
    this.showFailureOverlay(data.reason);
  }

  showFailureOverlay(reason) {
    const overlay = document.createElement('div');
    overlay.id = 'sword-failure-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100vh;
      background: rgba(139, 0, 0, 0.3);
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
      border: 4px solid #8b0000;
      pointer-events: auto;
    `;

    box.innerHTML = `
      <div style="font-size: 48px; margin-bottom: 20px;">❌</div>
      <h2 style="margin: 0 0 10px; color: #8b0000;">Booking Failed</h2>
      <p style="font-size: 16px; margin: 0 0 20px; color: #666;">${reason || 'Unknown error'}</p>
      <div style="font-size: 12px; color: #888;">The automation will reset automatically.</div>
    `;

    overlay.appendChild(box);
    document.body.appendChild(overlay);

    // Auto-remove after 5 seconds
    setTimeout(() => overlay.remove(), 5000);
  }

  async onExit() {
    const overlay = document.getElementById('sword-failure-overlay');
    if (overlay) overlay.remove();
    await super.onExit();
  }

  canTransition(targetState) {
    return ['IDLE'].includes(targetState);
  }
}

if (typeof window !== 'undefined') {
  window.FailedState = FailedState;
}
