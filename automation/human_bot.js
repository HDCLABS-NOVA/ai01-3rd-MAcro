const puppeteer = require('puppeteer');

// Configuration
const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 300; // 🔄 Set this to the number of times you want to run
const HEADLESS_MODE = true; // Set true for background execution

// Utils
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const randomDelay = (min, max) => delay(Math.floor(Math.random() * (max - min + 1)) + min);

// Simulate Expert Human Mouse Movement (Bezier Curve for Organic Path)
async function resetPerformanceTime(page, perfId, secondsInFuture) {
  const newOpenTime = new Date(Date.now() + secondsInFuture * 1000).toISOString();
  await page.evaluate(async (id, time) => {
    await fetch(`/api/admin/performances/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ open_time: time, status: 'upcoming' })
    });
  }, perfId, newOpenTime);
  console.log(`[SYSTEM] 🕒 Reset ${perfId} open time to ${secondsInFuture}s in future.`);
}

async function humanMove(page, targetX, targetY) {
  const start = await page.evaluate(() => ({ x: window.innerWidth / 2, y: window.innerHeight / 2 }));
  const cp1 = {
    x: start.x + (targetX - start.x) * Math.random(),
    y: start.y + (targetY - start.y) * Math.random()
  };

  const steps = 6;
  for (let i = 0; i <= 1; i += 1 / steps) {
    const x = Math.pow(1 - i, 2) * start.x + 2 * (1 - i) * i * cp1.x + Math.pow(i, 2) * targetX;
    const y = Math.pow(1 - i, 2) * start.y + 2 * (1 - i) * i * cp1.y + Math.pow(i, 2) * targetY;
    await page.mouse.move(x, y);
  }
}

async function runHumanIteration(iteration) {
  const USER_EMAIL = 'human@email.com';
  const USER_PASS = '1';

  console.log(`\n👨‍💼 Starting Expert Human Iteration ${iteration} / ${LOOP_COUNT}`);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: { width: 1280, height: 800 },
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const context = await browser.createIncognitoBrowserContext();
    const page = await context.newPage();

    console.log(`[${iteration}] TARGET: ${BASE_URL}`);
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });

    await page.evaluate(() => { sessionStorage.setItem('bot_type', 'human'); });

    // Login
    await page.goto(`${BASE_URL}login.html`, { waitUntil: 'networkidle2' });
    await page.type('#email', USER_EMAIL, { delay: 40 + Math.random() * 40 });
    await page.type('#password', USER_PASS, { delay: 40 + Math.random() * 40 });
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      page.click('button[type="submit"]')
    ]);

    // 0. Index -> Detail (Target: IU Concert with Auto-Reset)
    const TARGET_PERF_ID = 'perf001';
    await resetPerformanceTime(page, TARGET_PERF_ID, 15);

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

    // 4. Biological Reaction Time: Human takes 300-600ms to realize it's open
    console.log(`[${iteration}] 📢 Open! Reacting...`);
    await randomDelay(300, 600);

    // 5. Select Date with Curve
    const activeDateBtn = await page.$('.date-btn:not([disabled])');
    const activeBox = await activeDateBtn.boundingBox();
    if (activeBox) {
      await humanMove(page, activeBox.x + activeBox.width / 2, activeBox.y + activeBox.height / 2);
      await activeDateBtn.click({ delay: 50 + Math.random() * 50 });
    } else {
      await activeDateBtn.click();
    }

    await randomDelay(400, 700);

    // 6. Select Time
    await page.waitForSelector('.time-btn:not([disabled])');
    const timeBtn = await page.$('.time-btn:not([disabled])');
    const tBox = await timeBtn.boundingBox();
    if (tBox) {
      await humanMove(page, tBox.x + tBox.width / 2, tBox.y + tBox.height / 2);
      await timeBtn.click({ delay: 50 + Math.random() * 50 });
    } else {
      await timeBtn.click();
    }

    await randomDelay(400, 800);

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

    console.log(`[${iteration}] 🛡️ Bypassing Captcha (Macro-style)...`);
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

    await randomDelay(300, 600); // Shorter delay like a pro

    let humanSeatSelected = false;
    let humanAttempts = 0;
    while (!humanSeatSelected && humanAttempts < 5) {
      const availableSeats = await page.$$('.seat.available');
      if (availableSeats.length > 0) {
        const targetSeat = availableSeats[Math.floor(Math.random() * Math.min(availableSeats.length, 10))];
        const box = await targetSeat.boundingBox();

        if (box) {
          await humanMove(page, box.x + box.width / 2, box.y + box.height / 2);
          await targetSeat.click({ delay: 40 + Math.random() * 30 }); // 40-70ms elite human
        } else {
          await targetSeat.click();
        }

        await randomDelay(400, 600);
        const isSelected = await page.evaluate(el => el.classList.contains('selected'), targetSeat);

        if (isSelected) {
          humanSeatSelected = true;
          console.log(`[${iteration}] ⚡ Expert! Grabbed seat.`);
        } else {
          console.log(`[${iteration}] ⚠️ Taken! Reacting fast...`);
          await randomDelay(300, 500); // 0.3s reaction
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
