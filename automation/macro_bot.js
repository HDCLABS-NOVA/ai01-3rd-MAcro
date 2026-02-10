const puppeteer = require('puppeteer');

// Configuration
const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 80; // 🔄 Set this to the number of times you want to run
const HEADLESS_MODE = true; // Set true for faster background execution

// Utils
async function resetPerformanceTime(page, perfId, secondsInFuture, baseUrl) {
  const newOpenTime = new Date(Date.now() + secondsInFuture * 1000).toISOString();
  await page.evaluate(async (id, time, url) => {
    await fetch(`${url}api/admin/performances/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ open_time: time, status: 'upcoming' })
    });
  }, perfId, newOpenTime, baseUrl);
  console.log(`[SYSTEM] 🕒 Reset ${perfId} open time to ${secondsInFuture}s in future.`);
}

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const randomDelay = (min, max) => delay(Math.floor(Math.random() * (max - min + 1)) + min);

// Smart Captcha Solver (Macro Style: Instant)
async function solveCaptchaSmart(page) {
  try {
    // 1. Wait for captcha to be generated
    await page.waitForFunction(() => window.currentCaptcha && window.currentCaptcha.length > 0, { timeout: 5000 });

    // 2. Get the real answer directly from the page memory
    const text = await page.evaluate(() => window.currentCaptcha);
    return text;
  } catch (e) {
    return null;
  }
}

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
    // Use the default page instead of creating a new one
    const pages = await browser.pages();
    const page = pages[0]; // Use the first (default) page

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

    // Load index page
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

    // 4. Index -> Detail (Target: IU Concert)
    const TARGET_PERF_ID = 'perf001';
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

    // 5. Detail Page - ⚡ REALISTIC DOM-BASED MACRO (Using Puppeteer clicks for isTrusted=true)
    console.log(`[${iteration}] 📅 Waiting for UI state change (Real Macro Style)...`);

    // Fast polling with Puppeteer native clicks
    let clickedDate = false;
    let clickedTime = false;
    let clickedStart = false;

    while (!clickedStart) {
      try {
        if (!clickedDate) {
          const dateBtn = await page.$('.date-btn:not([disabled])');
          if (dateBtn) {
            // Macro-style: fast straight line movement
            const box = await dateBtn.boundingBox();
            if (box) {
              await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 3 });
              await delay(10);
            }
            await dateBtn.click({ delay: Math.floor(Math.random() * 15) + 1 }); // 1-15ms
            clickedDate = true;
            console.log('[Bot] Date clicked (Puppeteer)');
          }
        }

        if (clickedDate && !clickedTime) {
          const timeBtn = await page.$('.time-btn:not([disabled])');
          if (timeBtn) {
            const box = await timeBtn.boundingBox();
            if (box) {
              await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 3 });
              await delay(10);
            }
            await timeBtn.click({ delay: Math.floor(Math.random() * 15) + 1 });
            clickedTime = true;
            console.log('[Bot] Time clicked (Puppeteer)');
          }
        }

        if (clickedTime && !clickedStart) {
          const startBtn = await page.$('#start-booking-btn');
          if (startBtn) {
            const isVisible = await page.evaluate(el => {
              const style = window.getComputedStyle(el);
              return style.display !== 'none' && el.style.display !== 'none';
            }, startBtn);

            if (isVisible) {
              const box = await startBtn.boundingBox();
              if (box) {
                await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 3 });
                await delay(10);
              }
              await startBtn.click({ delay: Math.floor(Math.random() * 15) + 1 });
              clickedStart = true;
              console.log('[Bot] Start booking clicked (Puppeteer)');
            }
          }
        }

        await delay(30); // Same fast polling interval as before
      } catch (e) {
        // Element might be stale, continue polling
      }
    }

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

    // 7. Seat Selection & Captcha
    console.log(`[${iteration}] 🪑 Seat Map reached! Handling Captcha...`);
    await page.waitForSelector('#captcha-overlay', { visible: true, timeout: 5000 }).catch(() => { });

    // VLM Captcha Solve for Macro: Instant speed
    const captchaOverlay = await page.$('#captcha-overlay:not(.captcha-hidden)');
    if (captchaOverlay) {
      console.log(`[${iteration}] 🛡️ Solving Captcha with Smart Logic (Macro Style)...`);
      const text = await solveCaptchaSmart(page);
      if (text) {
        await page.type('#captcha-input', text, { delay: 0 }); // MACRO: Instant typing
        await page.click('#captcha-submit-btn');
        await delay(500); // Wait for overlay to hide
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

    // Pick Seat (High-Speed In-Page Logic with Retry - Using Puppeteer clicks)
    console.log(`[${iteration}] ⚡ Starting High-Speed Seat Selection...`);

    let selected = false;
    let attempts = 0;

    while (!selected && attempts < 50) {
      try {
        // 1. Check for Custom Alert Overlay (Already Taken)
        const alertOverlay = await page.$('#alert-overlay');
        if (alertOverlay) {
          const isActive = await page.evaluate(el => el.classList.contains('active'), alertOverlay);
          if (isActive) {
            const confirmBtn = await page.$('#alert-confirm-btn');
            if (confirmBtn) {
              await confirmBtn.click();
              await delay(300);
            }
          }
        }

        // 2. Find available seats
        const availableSeats = await page.$$('.seat.available:not(.selected)');

        if (availableSeats.length === 0) {
          await delay(100);
          attempts++;
          continue;
        }

        // 3. Select random seat and click immediately (realistic macro: no scouting!)
        const randomIndex = Math.floor(Math.random() * Math.min(10, availableSeats.length));
        const targetSeat = availableSeats[randomIndex];

        // 4. Move to target FAST and click (isTrusted=true)
        const box = await targetSeat.boundingBox();
        if (box) {
          // Fast straight-line movement
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 3 });
          await delay(10); // Minimal pause
        }
        await targetSeat.click({ delay: Math.floor(Math.random() * 15) + 1 }); // 1-15ms macro speed
        await delay(300); // Wait for potential alert or state change

        // 5. Verify selection
        const isSelected = await page.evaluate(el => el.classList.contains('selected'), targetSeat);
        if (isSelected) {
          selected = true;
          console.log(`[${iteration}] ✅ Seat selected successfully (Puppeteer click)`);
          break;
        }

        attempts++;
      } catch (e) {
        // Seat might have been taken or DOM changed, retry
        attempts++;
      }
    }

    const seatSelectionResult = selected;

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
