const puppeteer = require('puppeteer');

// Configuration
const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 200; // 🔄 Set this to the number of times you want to run
const HEADLESS_MODE = true; // Set true for background execution

// Utils
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const randomDelay = (min, max) => delay(Math.floor(Math.random() * (max - min + 1)) + min);

// Track mouse position to avoid jumps (remove anchor points)
let lastMouseX = 640;
let lastMouseY = 400;

async function humanMove(page, targetX, targetY) {
  const startX = lastMouseX;
  const startY = lastMouseY;

  // Bezier control point with more randomness
  const cp1 = {
    x: startX + (targetX - startX) * (0.3 + Math.random() * 0.4),
    y: startY + (targetY - startY) * (0.3 + Math.random() * 0.4)
  };

  const steps = 6; // Optimized for speed but still curved
  for (let i = 0; i <= 1; i += 1 / steps) {
    // Bezier formula
    let x = Math.pow(1 - i, 2) * startX + 2 * (1 - i) * i * cp1.x + Math.pow(i, 2) * targetX;
    let y = Math.pow(1 - i, 2) * startY + 2 * (1 - i) * i * cp1.y + Math.pow(i, 2) * targetY;

    // Add micro-jitter (human tremor)
    x += (Math.random() - 0.5) * 1.5;
    y += (Math.random() - 0.5) * 1.5;

    await page.mouse.move(x, y);
    // Faster interval between steps
    await delay(2 + Math.random() * 3);
  }

  // Final precise move to target
  await page.mouse.move(targetX, targetY);
  lastMouseX = targetX;
  lastMouseY = targetY;
}

// Helper for FAST human-like click duration (40-80ms)
async function humanClick(element, options = {}) {
  const clickDelay = 40 + Math.floor(Math.random() * 40); // 40-80ms duration (Pro-gamer level)
  await element.click({ ...options, delay: clickDelay });
}

// Helper for micro-movements (breathing/waiting)
async function humanJitter(page, durationMs) {
  const startTime = Date.now();
  while (Date.now() - startTime < durationMs) {
    const offsetX = (Math.random() - 0.5) * 3; // -1.5 to 1.5 px
    const offsetY = (Math.random() - 0.5) * 3;
    await page.mouse.move(lastMouseX + offsetX, lastMouseY + offsetY);
    await delay(100 + Math.random() * 200);
  }
}

// Smart Captcha Solver: Reads from memory but acts like a human
async function solveCaptchaSmart(page) {
  try {
    // 1. Wait for captcha to be generated
    await page.waitForFunction(() => window.currentCaptcha && window.currentCaptcha.length > 0, { timeout: 5000 });

    // 2. Get the real answer directly from the page memory (Instant!)
    const text = await page.evaluate(() => window.currentCaptcha);
    console.log(`[SmartSolve] Answer obtained: ${text}`);

    // 3. Simulate human thinking time (1.5 ~ 3 seconds)
    console.log('[SmartSolve] Simulating human thinking...');
    await humanJitter(page, 1500 + Math.random() * 1500);

    return text;
  } catch (e) {
    console.error('[SmartSolve] Error:', e.message);
    return null;
  }
}

const personas = ['elite', 'fast', 'pro'];

async function runHumanIteration(iteration) {
  const persona = personas[iteration % personas.length];
  console.log(`\n🏆 Starting ${persona.toUpperCase()} (High-Skill Human) Iteration ${iteration} / ${LOOP_COUNT}`);

  // Persona-based parameters: Focusing on HIGH SPEED but HUMAN CHARACTER
  const getDelayRange = () => {
    if (persona === 'elite') return { min: 30, max: 100 }; // Ultra fast
    if (persona === 'pro') return { min: 100, max: 250 };   // Pro gamer
    return { min: 200, max: 400 }; // Fast human
  };

  const reactionTime = () => {
    if (persona === 'elite') return { min: 80, max: 150 };  // Human limit reaction
    if (persona === 'pro') return { min: 150, max: 300 };
    return { min: 250, max: 500 };
  };

  const pRange = getDelayRange();
  const rTime = reactionTime();

  const USER_EMAIL = 'human@email.com';
  const USER_PASS = '1';

  // Starting from a random position
  lastMouseX = Math.floor(Math.random() * 1280);
  lastMouseY = Math.floor(Math.random() * 800);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: { width: 1280, height: 800 },
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const pages = await browser.pages();
    const page = pages[0];

    console.log(`[${iteration}] TARGET: ${BASE_URL} (Persona: ${persona})`);

    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    await page.evaluate(() => { sessionStorage.setItem('bot_type', 'human'); });

    // 3. Login
    await page.goto(`${BASE_URL}login.html`, { waitUntil: 'networkidle2' });
    await page.type('#email', USER_EMAIL, { delay: pRange.min / 2 + Math.random() * 40 });
    await page.type('#password', USER_PASS, { delay: pRange.min / 2 + Math.random() * 40 });
    const loginBtn = await page.$('button[type="submit"]');
    const lBox = await loginBtn.boundingBox();
    if (lBox) await humanMove(page, lBox.x + lBox.width / 2, lBox.y + lBox.height / 2);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      loginBtn.click({ delay: 80 + Math.random() * 70 })
    ]);

    // 1. Index -> Detail
    const TARGET_PERF_ID = 'perf001';
    await page.goto(`${BASE_URL}index.html`, { waitUntil: 'networkidle2' });
    const perfCard = await page.$(`.performance-card[onclick*="${TARGET_PERF_ID}"]`);
    const cBox = await perfCard.boundingBox();
    if (cBox) await humanMove(page, cBox.x + cBox.width / 2, cBox.y + cBox.height / 2);
    await randomDelay(pRange.min, pRange.max);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      perfCard.click({ delay: 80 + Math.random() * 70 })
    ]);

    // --- Human-like Wait & Click Logic ---
    await page.waitForSelector('.date-btn');
    const dateBtn = await page.$('.date-btn');
    const btnBox = await dateBtn.boundingBox();
    if (btnBox) {
      await humanMove(page, btnBox.x + btnBox.width / 2, btnBox.y + btnBox.height / 2);
    }

    let isBtnEnabled = false;
    while (!isBtnEnabled) {
      isBtnEnabled = await page.evaluate(() => {
        const btn = document.querySelector('.date-btn');
        return btn && !btn.disabled;
      });

      if (!isBtnEnabled) {
        const tremorX = (btnBox?.x || 0) + (btnBox?.width || 0) / 2 + (Math.random() - 0.5) * (persona === 'erratic' ? 15 : 4);
        const tremorY = (btnBox?.y || 0) + (btnBox?.height || 0) / 2 + (Math.random() - 0.5) * (persona === 'erratic' ? 15 : 4);
        await page.mouse.move(tremorX, tremorY);
        await delay(100);
      }
    }

    // Reaction Time
    await randomDelay(rTime.min, rTime.max);

    await page.waitForSelector('.date-btn:not([disabled])', { visible: true });
    const activeDateBtn = await page.$('.date-btn:not([disabled])');
    if (activeDateBtn) {
      const activeBox = await activeDateBtn.boundingBox();
      if (activeBox) {
        await humanMove(page, activeBox.x + activeBox.width / 2, activeBox.y + activeBox.height / 2);
        await randomDelay(pRange.min / 2, pRange.max / 2);
        await humanClick(activeDateBtn);
      }
    }

    await randomDelay(pRange.min, pRange.max);

    // 6. Select Time
    await page.waitForSelector('.time-btn:not([disabled])', { visible: true });
    const timeBtn = await page.$('.time-btn:not([disabled])');
    if (timeBtn) {
      const tBox = await timeBtn.boundingBox();
      if (tBox) {
        await humanMove(page, tBox.x + tBox.width / 2, tBox.y + tBox.height / 2);
        await randomDelay(pRange.min / 2, pRange.max / 2);
        await humanClick(timeBtn);
      }
    }

    await randomDelay(pRange.min, pRange.max);

    // 7. Start Booking
    const startBtn = await page.$('#start-booking-btn');
    const sBtnBox = await startBtn.boundingBox();
    if (sBtnBox) await humanMove(page, sBtnBox.x + sBtnBox.width / 2, sBtnBox.y + sBtnBox.height / 2);
    await randomDelay(pRange.min / 2, pRange.max / 2);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      startBtn.click({ delay: 80 + Math.random() * 70 })
    ]);

    // ⏳ Handle Queue
    try {
      if (page.url().includes('queue.html')) {
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 60000 });
      }
    } catch (e) { }

    // Seat Page & Captcha
    await page.waitForSelector('#seat-grid', { timeout: 30000 });
    await page.waitForSelector('#captcha-overlay', { visible: true, timeout: 5000 }).catch(() => { });

    const captchaOverlay = await page.$('#captcha-overlay:not(.captcha-hidden)');
    if (captchaOverlay) {
      const text = await solveCaptchaSmartPersona(page, persona);

      if (text) {
        const inputField = await page.$('#captcha-input');
        const iBox = await inputField.boundingBox();
        if (iBox) {
          await humanMove(page, iBox.x + iBox.width / 2, iBox.y + iBox.height / 2);
          await inputField.click({ delay: 80 + Math.random() * 70 });
        }

        for (const char of text) {
          await page.type('#captcha-input', char, { delay: 40 + Math.random() * (persona === 'slow' ? 200 : 100) });
        }

        const submitBtn = await page.$('#captcha-submit-btn');
        const sBox = await submitBtn.boundingBox();
        if (sBox) {
          await humanMove(page, sBox.x + sBox.width / 2, sBox.y + sBox.height / 2);
          await randomDelay(pRange.min / 2, pRange.max / 2);
          await humanClick(submitBtn);
        }
        await delay(1000);
      }
    }

    // Seat selection
    let humanSeatSelected = false;
    let humanAttempts = 0;
    while (!humanSeatSelected && humanAttempts < 10) {
      const availableSeats = await page.$$('.seat.available');
      if (availableSeats.length > 0) {
        const targetSeat = availableSeats[Math.floor(Math.random() * Math.min(10, availableSeats.length))];
        const box = await targetSeat.boundingBox();
        if (box) {
          await humanMove(page, box.x + box.width / 2, box.y + box.height / 2);
          await randomDelay(pRange.min / 2, pRange.max / 2);
          await humanClick(targetSeat);
        }

        await randomDelay(200, 400);

        const alertModal = await page.$('.custom-alert-overlay');
        if (alertModal) {
          const closeBtn = await page.$('.custom-alert-overlay .alert-close, .custom-alert-overlay button');
          if (closeBtn) {
            const clBox = await closeBtn.boundingBox();
            if (clBox) await humanMove(page, clBox.x + clBox.width / 2, clBox.y + clBox.height / 2);
            await closeBtn.click({ delay: 80 + Math.random() * 70 });
            await randomDelay(pRange.min, pRange.max);
          }
          humanAttempts++;
          continue;
        }

        const isSelected = await page.evaluate(el => el.classList.contains('selected'), targetSeat);
        if (isSelected) {
          humanSeatSelected = true;
        } else {
          humanAttempts++;
          await randomDelay(pRange.min, pRange.max);
        }
      } else break;
    }

    await randomDelay(pRange.min, pRange.max);
    const nextBtn = await page.$('#next-btn');
    const nBox = await nextBtn.boundingBox();
    if (nBox) await humanMove(page, nBox.x + nBox.width / 2, nBox.y + nBox.height / 2);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      nextBtn.click({ delay: 80 + Math.random() * 70 })
    ]);

    // Finish
    for (let i = 0; i < 3; i++) {
      await randomDelay(pRange.min * 2, pRange.max * 2);
      let btn = await page.$('button.btn-primary') || await page.$('button[onclick*="confirm"]');
      if (btn) {
        const fBox = await btn.boundingBox();
        if (fBox) await humanMove(page, fBox.x + fBox.width / 2, fBox.y + fBox.height / 2);
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 5000 }).catch(() => { }),
          btn.click({ delay: 80 + Math.random() * 70 })
        ]);
      }
    }

    if (page.url().includes('booking_complete.html')) {
      console.log(`[${iteration}] 🎉 SUCCESS!`);
      await delay(1500);
    }

  } catch (e) {
    console.error(`[${iteration}] ❌ Error:`, e.name, e.message);
  } finally {
    await browser.close();
  }
}

async function solveCaptchaSmartPersona(page, persona) {
  try {
    await page.waitForFunction(() => window.currentCaptcha && window.currentCaptcha.length > 0, { timeout: 5000 });
    const text = await page.evaluate(() => window.currentCaptcha);

    let thinkTime = 1500 + Math.random() * 1500;
    if (persona === 'fast') thinkTime = 500 + Math.random() * 500;
    if (persona === 'slow') thinkTime = 3000 + Math.random() * 3000;

    await humanJitter(page, thinkTime);
    return text;
  } catch (e) { return null; }
}

(async () => {
  for (let i = 1; i <= LOOP_COUNT; i++) {
    await runHumanIteration(i);
    await delay(1000 + Math.random() * 2000);
  }
  console.log('\n✅ Persona Human data collection finished.');
})();
