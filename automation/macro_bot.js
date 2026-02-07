const puppeteer = require('puppeteer');

// Configuration
const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 300; // 🔄 Set this to the number of times you want to run
const HEADLESS_MODE = true; // Set true for faster background execution

// Utils
async function resetPerformanceTime(page, perfId, secondsInFuture) {
  const newOpenTime = new Date(Date.now() + secondsInFuture * 1000).toISOString();
  await page.evaluate(async (id, time) => {
    await fetch(`/api/admin/performances/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ open_time: time, status: 'upcoming' })
    });
  }, perfId, newOpenTime);
}

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const randomDelay = (min, max) => delay(Math.floor(Math.random() * (max - min + 1)) + min);

async function runBotIteration(iteration) {
  const USER_EMAIL = 'macro@email.com';
  const USER_PASS = '1';
  const USER_NAME = 'MacroUser';
  const USER_PHONE = '010-0000-0000';
  const USER_BIRTH = '1990-01-01';

  console.log(`\n🤖 Starting Iteration ${iteration} / ${LOOP_COUNT}`);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: null,
    args: ['--start-maximized']
  });

  try {
    // Use Incognito context to ensure fresh session
    const context = await browser.createIncognitoBrowserContext();
    const page = await context.newPage();

    // Close any other open pages (like the default blank one) to keep only one window
    const pages = await browser.pages();
    for (const p of pages) {
      if (p !== page) await p.close();
    }

    // 🔍 Enable Browser Console Logging
    page.on('console', msg => {
      const type = msg.type();
      const text = msg.text();
      // Filter out some noise if needed, but for now show everything relevant
      if (!text.includes('HMR') && !text.includes('Hot')) {
        console.log(`[Browser ${type}] ${text}`);
      }
    });

    console.log(`[${iteration}] TARGET: ${BASE_URL}`);

    // 1. Check ngrok
    await page.goto(BASE_URL, { waitUntil: 'networkidle0' });

    // 🏷️ Set bot type globally for the session
    await page.evaluate(() => {
      sessionStorage.setItem('bot_type', 'macro');
    });

    const ngrokBtn = await page.$('button');
    if (ngrokBtn) {
      const btnText = await page.evaluate(el => el.textContent, ngrokBtn);
      if (btnText && btnText.includes('Visit Site')) { // Add safety check
        await ngrokBtn.click();
        await page.waitForNavigation({ waitUntil: 'networkidle0' });
      }
    }

    // 3. Login
    console.log(`[${iteration}] 🔑 Logging in...`);
    let loginLoadSuccess = false;
    if (!page.url().includes('login.html')) {
      for (let i = 0; i < 3; i++) {
        try {
          await page.goto(`${BASE_URL}login.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
          loginLoadSuccess = true;
          break;
        } catch (e) { console.log(`[${iteration}] ⚠️ Login load retry ${i + 1}...`); await delay(1000); }
      }
    } else {
      loginLoadSuccess = true;
    }

    if (loginLoadSuccess) {
      await page.waitForSelector('#email');
      await page.type('#email', USER_EMAIL);
      await page.type('#password', USER_PASS);
      const loginBtn = await page.$('button[type="submit"]');
      await loginBtn.click();
      try {
        await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 30000 });
      } catch (e) { console.log('⚠️ Navigation timeout, assuming success if URL changed'); }
    }

    // 4. Index -> Detail (Target: IU Concert with Auto-Reset)
    const TARGET_PERF_ID = 'perf001';
    await resetPerformanceTime(page, TARGET_PERF_ID, 15);

    console.log(`[${iteration}] 🎭 Selecting Performance ${TARGET_PERF_ID}...`);
    await page.goto(`${BASE_URL}index.html`, { waitUntil: 'networkidle0' });
    await page.waitForSelector(`.performance-card[onclick*="${TARGET_PERF_ID}"]`);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle0' }),
      page.click(`.performance-card[onclick*="${TARGET_PERF_ID}"]`)
    ]);

    // 🏷️ Tag this log as 'macro'
    await page.evaluate(() => {
      if (typeof updateMetadata === 'function') {
        updateMetadata({ bot_type: 'macro' });
      }
    });

    // 5. Detail Page - ⚡ REALISTIC DOM-BASED MACRO
    console.log(`[${iteration}] 📅 Waiting for UI state change (Real Macro Style)...`);

    await page.evaluate(() => {
      return new Promise((resolve) => {
        let clickedDate = false;
        let clickedTime = false;
        let clickedStart = false;

        const dispatchSequence = (el) => {
          const rect = el.getBoundingClientRect();
          const x = rect.left + rect.width / 2;
          const y = rect.top + rect.height / 2;
          const opts = { view: window, bubbles: true, cancelable: true, clientX: x, clientY: y };

          // Real click sequence: mousedown -> mouseup -> click
          el.dispatchEvent(new MouseEvent('mousedown', opts));
          el.dispatchEvent(new MouseEvent('mouseup', opts));
          el.dispatchEvent(new MouseEvent('click', opts));
        };

        const checkInterval = setInterval(() => {
          if (!clickedDate) {
            const dateBtn = document.querySelector('.date-btn:not([disabled])');
            if (dateBtn) {
              dispatchSequence(dateBtn);
              clickedDate = true;
              console.log('[Bot] Date clicked (Full Sequence)');
            }
          }

          if (clickedDate && !clickedTime) {
            const timeBtn = document.querySelector('.time-btn:not([disabled])');
            if (timeBtn) {
              dispatchSequence(timeBtn);
              clickedTime = true;
              console.log('[Bot] Time clicked (Full Sequence)');
            }
          }

          if (clickedTime && !clickedStart) {
            const startBtn = document.getElementById('start-booking-btn');
            if (startBtn && (startBtn.style.display === 'block' || window.getComputedStyle(startBtn).display !== 'none')) {
              dispatchSequence(startBtn);
              clickedStart = true;
              clearInterval(checkInterval);
              resolve();
            }
          }
        }, 30);
      });
    });

    console.log(`[${iteration}] ⚡ Entry sequence clicked. Waiting for next page...`);

    // 6. Resilient Page Transition (Handling "Target closed" errors)
    let pageSettled = false;
    const navStartTime = Date.now();

    while (Date.now() - navStartTime < 20000) { // Max 20s
      try {
        const currentUrl = page.url();

        // If we are in the Queue, just wait
        if (currentUrl.includes('queue.html')) {
          if (!pageSettled) {
            console.log(`[${iteration}] ⏳ In Queue. Waiting for auto-redirect...`);
            pageSettled = true;
          }
        }
        // If we reached the Seat Map, wait for the grid
        else if (currentUrl.includes('seat_select.html')) {
          const grid = await page.$('#seat-grid');
          if (grid) {
            console.log(`[${iteration}] 🪑 Seat Map reached!`);
            break;
          }
        }
      } catch (e) {
        // During navigation, page.url() or page.$() might throw "Target closed"
        // We just ignore it and try again after a short sleep
      }
      await delay(200);
    }

    // 7. Seat Selection & Captcha
    console.log(`[${iteration}] 🪑 Proceeding with Seat Selection...`);

    // Ensure we give enough time for seat_select.js to initialize
    await delay(1000);

    const captchaOverlay = await page.$('#captcha-overlay');
    if (captchaOverlay) {
      const isHidden = await page.evaluate(el => el.classList.contains('captcha-hidden'), captchaOverlay);
      if (!isHidden) {
        console.log(`[${iteration}] 🛡️ Bypassing Captcha...`);
        await page.evaluate(() => {
          if (window.verifyCaptcha) {
            window.isCaptchaVerified = true;
            if (sessionStorage) sessionStorage.setItem('captchaVerified', 'true');
            const overlay = document.getElementById('captcha-overlay');
            if (overlay) overlay.classList.add('captcha-hidden');
          }
        });
      }
    }

    // Add safe dialog handler (Moved before loop to catch alerts during selection)
    page.on('dialog', async dialog => {
      console.log(`[${iteration}] 💬 Alert detected: ${dialog.message()}`);
      await dialog.dismiss();
    });

    // Auto-dismiss alerts (for "Already selected seat" messages)
    page.on('dialog', async dialog => {
      console.log(`[${iteration}] ⚠️ Alert detected: ${dialog.message()}`);
      await dialog.dismiss();
    });

    // Pick Seat (High-Speed In-Page Logic with Retry)
    console.log(`[${iteration}] ⚡ Starting High-Speed Seat Selection...`);
    const seatSelectionResult = await page.evaluate(async () => {
      const wait = (ms) => new Promise(res => setTimeout(res, ms));
      let selected = false;
      let attempts = 0;

      while (!selected && attempts < 50) {
        // 1. Check for Custom Alert Overlay (Already Taken)
        const alertOverlay = document.getElementById('alert-overlay');
        if (alertOverlay && alertOverlay.classList.contains('active')) {
          const confirmBtn = document.getElementById('alert-confirm-btn');
          if (confirmBtn) confirmBtn.click();
          await wait(300);
        }

        const availableSeats = Array.from(document.querySelectorAll('.seat.available:not(.selected)'));
        if (availableSeats.length === 0) {
          await wait(100);
          attempts++;
          continue;
        }

        const randomIndex = Math.floor(Math.random() * Math.min(10, availableSeats.length));
        const targetSeat = availableSeats[randomIndex];

        // Dispatch realistic sequence
        const rect = targetSeat.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        const opts = { view: window, bubbles: true, cancelable: true, clientX: x, clientY: y };
        targetSeat.dispatchEvent(new MouseEvent('mousedown', opts));
        targetSeat.dispatchEvent(new MouseEvent('mouseup', opts));
        targetSeat.dispatchEvent(new MouseEvent('click', opts));

        await wait(400); // Wait for potential alert or state change

        if (targetSeat.classList.contains('selected')) {
          selected = true;
          break;
        }
        attempts++;
      }
      return selected;
    });

    if (seatSelectionResult) {
      console.log(`[${iteration}] ✅ Seat selected! Clicking Next...`);
      await page.waitForSelector('#next-btn', { visible: true });

      // Robust Click & Wait
      try {
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 10000 }).catch(() => { }),
          page.click('#next-btn')
        ]);
      } catch (e) {
        console.log(`[${iteration}] ⏩ Navigation handled: ${page.url()}`);
      }

      // 7. Discount
      console.log(`[${iteration}] 💸 Discount Page...`);
      await page.waitForSelector('.discount-option');

      let discountBtn = await page.$('button[onclick*="confirmDiscount"]');
      if (!discountBtn) {
        const btns = await page.$$('button');
        for (const btn of btns) {
          const txt = await page.evaluate(el => el.textContent, btn);
          if (txt && txt.includes('다음')) { discountBtn = btn; break; }
        }
      }

      if (discountBtn) {
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          discountBtn.click()
        ]);
        console.log(`[${iteration}] ⏩ Moved to Order Info Page`);
      }

      // 8. Order Info
      console.log(`[${iteration}] 📋 Order Info Page...`);
      await page.waitForSelector('#booker-name', { visible: true });

      console.log(`[${iteration}] ⏩ Skipping input (auto-filled). clicking Payment...`);

      // Scroll to button
      let orderBtn = await page.$('button[onclick*="confirmOrderInfo"]');
      if (!orderBtn) {
        const btns = await page.$$('button');
        for (const btn of btns) {
          const txt = await page.evaluate(el => el.textContent, btn);
          if (txt && txt.includes('결제')) { orderBtn = btn; break; }
        }
      }

      if (orderBtn) {
        // Scroll and wait
        await page.evaluate((btn) => btn.scrollIntoView(), orderBtn);
        await delay(500);

        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          orderBtn.click()
        ]);
        console.log(`[${iteration}] ⏩ Moved to Payment Page`);
      }

      // 9. Payment
      console.log(`[${iteration}] 💳 Payment Page...`);
      await page.waitForSelector('#total-price');

      let payBtn = await page.$('button[onclick*="processPayment"]');
      if (!payBtn) {
        const btns = await page.$$('button');
        for (const btn of btns) {
          const txt = await page.evaluate(el => el.textContent, btn);
          if (txt && txt.includes('결제')) { payBtn = btn; break; }
        }
      }

      if (payBtn) {
        await payBtn.click();
        // Payment might take time or use replaceState, just wait for selector or URL
        await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 20000 });
      }

      if (page.url().includes('booking_complete.html')) {
        console.log(`[${iteration}] 🎉 SUCCESS! Booking complete.`);
        console.log(`[${iteration}] ⏳ Waiting for server log sync...`);
        await delay(5000);
      } else {
        console.error(`[${iteration}] ❌ Failed (Wrong URL): ${page.url()}`);
      }
    }

  } catch (e) {
    console.error(`[${iteration}] ❌ Error:`, e.message);
  } finally {
    // Keep browser open a bit longer just in case
    await delay(2000);
    await browser.close();
  }
}

(async () => {
  for (let i = 1; i <= LOOP_COUNT; i++) {
    await runBotIteration(i);
    await randomDelay(2000, 5000); // Wait between sessions
  }
  console.log('\n✅ All iterations finished.');
})();
