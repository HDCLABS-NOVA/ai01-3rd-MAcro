const puppeteer = require('puppeteer');

// Configuration
const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 300; // 🔄 Set this to the number of times you want to run
const HEADLESS_MODE = false; // Set true for background execution

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

  const steps = 12; // More steps for smoother but jittery path
  for (let i = 0; i <= 1; i += 1 / steps) {
    // Bezier formula
    let x = Math.pow(1 - i, 2) * startX + 2 * (1 - i) * i * cp1.x + Math.pow(i, 2) * targetX;
    let y = Math.pow(1 - i, 2) * startY + 2 * (1 - i) * i * cp1.y + Math.pow(i, 2) * targetY;

    // Add micro-jitter (human tremor)
    x += (Math.random() - 0.5) * 2;
    y += (Math.random() - 0.5) * 2;

    await page.mouse.move(x, y);
    // Randomize interval between steps
    await delay(5 + Math.random() * 10);
  }

  // Final precise move to target
  await page.mouse.move(targetX, targetY);
  lastMouseX = targetX;
  lastMouseY = targetY;
}

// Helper for human-like click duration (1-10ms)
async function humanClick(element, options = {}) {
  const clickDelay = 1 + Math.floor(Math.random() * 9); // 1-10ms duration
  await element.click({ ...options, delay: clickDelay });
}

async function runHumanIteration(iteration) {
  const USER_EMAIL = 'human@email.com';
  const USER_PASS = '1';

  // Starting from a random position instead of fixed center
  lastMouseX = Math.floor(Math.random() * 1280);
  lastMouseY = Math.floor(Math.random() * 800);

  console.log(`\n👨‍💼 Starting Expert Human Iteration ${iteration} / ${LOOP_COUNT}`);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: { width: 1280, height: 800 },
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    // Use the default page instead of creating a new one
    const pages = await browser.pages();
    const page = pages[0]; // Use the first (default) page

    console.log(`[${iteration}] TARGET: ${BASE_URL}`);

    // Load index page
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });

    await page.evaluate(() => { sessionStorage.setItem('bot_type', 'human'); });

    // 3. Login
    await page.goto(`${BASE_URL}login.html`, { waitUntil: 'networkidle2' });
    await page.type('#email', USER_EMAIL, { delay: 40 + Math.random() * 40 });
    await page.type('#password', USER_PASS, { delay: 40 + Math.random() * 40 });
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      page.click('button[type="submit"]')
    ]);

    // 1. Index -> Detail (Target: IU Concert)
    const TARGET_PERF_ID = 'perf001';
    console.log(`[${iteration}] 🎭 Selecting Performance ${TARGET_PERF_ID}...`);
    await page.goto(`${BASE_URL}index.html`, { waitUntil: 'networkidle2' });
    await page.waitForSelector(`.performance-card[onclick*="${TARGET_PERF_ID}"]`);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      page.click(`.performance-card[onclick*="${TARGET_PERF_ID}"]`)
    ]);

    // --- Improved Expert Human Wait & Click Logic ---
    console.log(`[${iteration}] ⏳ Waiting for ticket to open...`);

    // 1. Wait for the date button to appear (even if disabled)
    await page.waitForSelector('.date-btn');

    // 2. Move mouse to the button area and hover while waiting
    const dateBtn = await page.$('.date-btn');
    const btnBox = await dateBtn.boundingBox();
    if (btnBox) {
      await humanMove(page, btnBox.x + btnBox.width / 2, btnBox.y + btnBox.height / 2);
    }

    // 3. Simulate human tension (micro-tremors) until enabled
    let isBtnEnabled = false;
    while (!isBtnEnabled) {
      isBtnEnabled = await page.evaluate(() => {
        const btn = document.querySelector('.date-btn');
        return btn && !btn.disabled;
      });

      if (!isBtnEnabled) {
        // Human tremor: slight movement while waiting
        const tremorX = (btnBox?.x || 0) + (btnBox?.width || 0) / 2 + (Math.random() - 0.5) * 4;
        const tremorY = (btnBox?.y || 0) + (btnBox?.height || 0) / 2 + (Math.random() - 0.5) * 4;
        await page.mouse.move(tremorX, tremorY);
        await delay(100); // 10hz polling with movement
      }
    }

    // 4. Biological Reaction Time: Quick human reaction for competitive ticketing
    console.log(`[${iteration}] 📢 Open! Reacting...`);
    await randomDelay(100, 300); // Fast reaction (was 300-600)

    // 5. Select Date with Curve
    await page.waitForSelector('.date-btn:not([disabled])', { visible: true });
    const activeDateBtn = await page.$('.date-btn:not([disabled])');
    if (!activeDateBtn) {
      throw new Error('Date button not found or still disabled');
    }

    // Scroll element into view if needed
    await activeDateBtn.evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'auto' }));
    await delay(30); // Quick scroll

    const activeBox = await activeDateBtn.boundingBox();
    if (activeBox) {
      await humanMove(page, activeBox.x + activeBox.width / 2, activeBox.y + activeBox.height / 2);
      await randomDelay(80, 200); // Cognitive thinking before click
      await humanClick(activeDateBtn);
    } else {
      await activeDateBtn.evaluate(el => el.click());
    }

    await randomDelay(150, 400); // Decision for time selection

    // 6. Select Time
    await page.waitForSelector('.time-btn:not([disabled])', { visible: true });
    const timeBtn = await page.$('.time-btn:not([disabled])');
    if (!timeBtn) {
      throw new Error('Time button not found or still disabled');
    }

    // Scroll element into view if needed
    await timeBtn.evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'auto' }));
    await delay(30); // Quick scroll

    const tBox = await timeBtn.boundingBox();
    if (tBox) {
      await humanMove(page, tBox.x + tBox.width / 2, tBox.y + tBox.height / 2);
      await randomDelay(80, 200); // Thinking
      await humanClick(timeBtn);
    } else {
      await timeBtn.evaluate(el => el.click());
    }

    await randomDelay(150, 400);

    // 7. Start Booking
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      page.click('#start-booking-btn')
    ]);

    // ⏳ Handle Queue if it appears
    try {
      if (page.url().includes('queue.html')) {
        console.log(`[${iteration}] ⏳ In queue... waiting for turn.`);
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 60000 });
      }
    } catch (e) {
      // If we are already on seat_select or queue timed out but we changed page
    }

    // Seat Page & Captcha Bypass
    await page.waitForSelector('#seat-grid', { timeout: 30000 });

    // Wait 1 second for CAPTCHA to appear (same as macro)
    await delay(1000);

    console.log(`[${iteration}] 🛡️ Bypassing Captcha...`);
    await page.evaluate(() => {
      // Direct access to state variables in seat_select.js
      window.isCaptchaVerified = true;
      if (typeof isCaptchaVerified !== 'undefined') isCaptchaVerified = true;

      if (sessionStorage) sessionStorage.setItem('captchaVerified', 'true');
      const overlay = document.getElementById('captcha-overlay');
      if (overlay) {
        overlay.classList.add('captcha-hidden');
        overlay.style.display = 'none';
      }
    });

    // Seat selection - FAST HUMAN: No browsing, immediate click!
    console.log(`[${iteration}] 💺 Selecting seat (FAST)...`);
    let humanSeatSelected = false;
    let humanAttempts = 0;
    const maxAttempts = 10;

    while (!humanSeatSelected && humanAttempts < maxAttempts) {
      const availableSeats = await page.$$('.seat.available');
      if (availableSeats.length > 0) {
        // Pick a random seat from top available (like real users)
        const targetSeat = availableSeats[Math.floor(Math.random() * Math.min(5, availableSeats.length))];
        const box = await targetSeat.boundingBox();

        if (box) {
          await humanMove(page, box.x + box.width / 2, box.y + box.height / 2);
          await randomDelay(100, 300); // Human scans before clicking
          await humanClick(targetSeat);
        } else {
          await targetSeat.click();
        }

        await randomDelay(200, 400); // Wait for potential alert

        // Check if "already taken" alert appeared
        const alertModal = await page.$('.custom-alert-overlay');
        if (alertModal) {
          console.log(`[${iteration}] ⚠️ Already taken! Closing alert...`);
          // Close the alert
          const closeBtn = await page.$('.custom-alert-overlay .alert-close, .custom-alert-overlay button');
          if (closeBtn) {
            await closeBtn.click();
            await randomDelay(100, 200); // Quick reaction
          }
          humanAttempts++;
          continue; // Try again immediately
        }

        // Check if seat was successfully selected
        const isSelected = await page.evaluate(el => el.classList.contains('selected'), targetSeat);

        if (isSelected) {
          humanSeatSelected = true;
          console.log(`[${iteration}] ⚡ Got it!`);
        } else {
          console.log(`[${iteration}] ⚠️ Taken! Retrying...`);
          await randomDelay(100, 300); // Fast reaction
          humanAttempts++;
        }
      } else {
        break;
      }
    }

    await randomDelay(400, 800);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      page.click('#next-btn')
    ]);

    // Fast finish
    for (let i = 0; i < 3; i++) {
      await randomDelay(500, 1000);
      let btn = await page.$('button.btn-primary') || await page.$('button[onclick*="confirm"]');
      if (btn) {
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 5000 }).catch(() => { }),
          btn.click()
        ]);
      }
    }

    if (page.url().includes('booking_complete.html')) {
      console.log(`[${iteration}] 🎉 SUCCESS! Expert Human.`);
      await delay(2000);
    }

  } catch (e) {
    console.error(`[${iteration}] ❌ Error:`, e.message);
  } finally {
    await browser.close();
  }
}

(async () => {
  for (let i = 1; i <= LOOP_COUNT; i++) {
    await runHumanIteration(i);
    if (i < LOOP_COUNT) await randomDelay(2000, 4000);
  }
  console.log('\n✅ Expert Human data collection finished.');
})();
