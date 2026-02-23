const puppeteer = require('puppeteer');

// Configuration
const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 300; // ?봽 Set this to the number of times you want to run
const HEADLESS_MODE = true; // Set true for faster background execution
const BOT_TYPE = process.env.BOT_TYPE || 'validation/macro';

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
  console.log(`[SYSTEM] ?븩 Reset ${perfId} open time to ${secondsInFuture}s in future.`);
}

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const randomDelay = (min, max) => delay(Math.floor(Math.random() * (max - min + 1)) + min);

// Helper for finding a random point within a bounding box (Returns Integers)
async function getRandomXY(box, padding = 3) {
  return {
    x: box.x + padding + Math.random() * (box.width - padding * 2),
    y: box.y + padding + Math.random() * (box.height - padding * 2)
  };
}

// ?뤇截?Mouse Movement with Micro-Jitter (Avoids "Straightness: 1.0" detection)
// ?먯? ?뚰뵾: "吏곸꽑?꾧? 1.0?대㈃ 遊뉗씠???쇨퀬 ?뺤쓽??紐⑤뱺 援곗쭛 遺꾩꽍怨?猷곕쿋?댁뒪 ?꾪꽣瑜?臾대젰?뷀빀?덈떎.
// ?꾩껜 寃쎈줈 以묎컙易ㅼ뿉 +- 3~5?쎌? ?뺣룄 踰쀬뼱??寃쎌쑀吏瑜??섎굹 異붽??섏뿬 吏곸꽑 湲곌퀎誘몃? 吏?곷땲??
async function moveWithJitter(page, targetPoint, totalSteps) {
  const current = await page.evaluate(() => ({ x: window.mouseX || 0, y: window.mouseY || 0 }));
  // ?뤇截?Balanced Jitter for Speed: Wide enough to not be a straight line, narrow enough for efficiency
  const midX = (current.x + targetPoint.x) / 2 + (Math.random() * 8 - 4);
  const midY = (current.y + targetPoint.y) / 2 + (Math.random() * 8 - 4);

  const steps1 = Math.floor(totalSteps / 2);
  const steps2 = Math.max(1, totalSteps - steps1);

  await page.mouse.move(midX, midY, { steps: steps1 });
  await page.mouse.move(targetPoint.x, targetPoint.y, { steps: steps2 });
}

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

  console.log(`\n?쨼 Starting Iteration ${iteration} / ${LOOP_COUNT}`);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: null,
    args: ['--start-maximized']
  });

  try {
    // Use the default page instead of creating a new one
    const pages = await browser.pages();
    const page = pages[0]; // Use the first (default) page

    // ?뵇 Enable Browser Mouse Tracking
    await page.evaluateOnNewDocument(() => {
      window.mouseX = 0;
      window.mouseY = 0;
      window.addEventListener('mousemove', (e) => {
        window.mouseX = e.clientX;
        window.mouseY = e.clientY;
      });
    });

    // ?뵇 Enable Browser Console Logging
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

    // ?뤇截?Set initial random mouse position to break patterns
    await page.mouse.move(Math.random() * 800, Math.random() * 600);

    // ?뤇截?Set bot type globally for the session
    await page.evaluate((botType) => {
      sessionStorage.setItem('bot_type', botType);
    }, BOT_TYPE);

    const ngrokBtn = await page.$('button');
    if (ngrokBtn) {
      const btnText = await page.evaluate(el => el.textContent, ngrokBtn);
      if (btnText && btnText.includes('Visit Site')) { // Add safety check
        await ngrokBtn.click();
        await page.waitForNavigation({ waitUntil: 'networkidle0' });
      }
    }

    // 3. Login
    console.log(`[${iteration}] ?뵎 Logging in...`);
    let loginLoadSuccess = false;
    if (!page.url().includes('login.html')) {
      for (let i = 0; i < 3; i++) {
        try {
          await page.goto(`${BASE_URL}login.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
          loginLoadSuccess = true;
          break;
        } catch (e) { console.log(`[${iteration}] ?좑툘 Login load retry ${i + 1}...`); await delay(1000); }
      }
    } else {
      loginLoadSuccess = true;
    }

    if (loginLoadSuccess) {
      await page.type('#email', USER_EMAIL);
      await page.type('#password', USER_PASS);
      const loginBtn = await page.$('button[type="submit"]');
      const box = await loginBtn.boundingBox();
      if (box) {
        const point = await getRandomXY(box);
        // ?뤇截?Dynamic Steps: 2 (Teleport) up to 30 (Smooth)
        const steps = Math.floor(Math.random() * 28) + 2;

        // ?뤇截?Micro-Jitter: Use helper for midpoint deviation
        await moveWithJitter(page, point, steps);
      }
      // ?뤇截?High-Speed Click: 1ms to 20ms
      await loginBtn.click({ delay: Math.floor(Math.random() * 20) + 1 });
      try {
        await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 30000 });
      } catch (e) {
        console.log('?좑툘 Navigation timeout, assuming success if URL changed');
      }
    }

    // 4. Index -> Detail (Target: IU Concert)
    const TARGET_PERF_ID = 'perf001';
    console.log(`[${iteration}] ?렚 Selecting Performance ${TARGET_PERF_ID}...`);
    await page.goto(`${BASE_URL}index.html`, { waitUntil: 'networkidle0' });
    await page.waitForSelector(`.performance-card[onclick*="${TARGET_PERF_ID}"]`);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle0' }),
      page.click(`.performance-card[onclick*="${TARGET_PERF_ID}"]`)
    ]);

    // ?뤇截?Tag this log as 'macro'
    await page.evaluate((botType) => {
      if (typeof updateMetadata === 'function') {
        updateMetadata({ bot_type: botType });
      }
    }, BOT_TYPE);

    // 5. Detail Page - ??REALISTIC DOM-BASED MACRO (Using Puppeteer clicks for isTrusted=true)
    console.log(`[${iteration}] ?뱟 Waiting for UI state change (Real Macro Style)...`);

    // Fast polling with Puppeteer native clicks
    let clickedDate = false;
    let clickedTime = false;
    let clickedStart = false;

    while (!clickedStart) {
      // ?뤇截?Aggressive Polling: 5ms to 40ms (Human-impossible consistency)
      await delay(Math.floor(Math.random() * 35) + 5);

      try {
        if (!clickedDate) {
          const dateBtn = await page.$('.date-btn:not([disabled])');
          if (dateBtn) {
            // Macro-style: fast RANDOM point movement
            const box = await dateBtn.boundingBox();
            if (box) {
              const point = await getRandomXY(box);
              const steps = Math.floor(Math.random() * 6) + 1; // 1~7 steps
              await moveWithJitter(page, point, steps);
              await delay(Math.floor(Math.random() * 20)); // Max 20ms micro-pause
            }
            await dateBtn.click({ delay: Math.floor(Math.random() * 10) + 1 });
            clickedDate = true;
            console.log('[Bot] Date clicked (Random XY)');
          }
        }

        if (clickedDate && !clickedTime) {
          const timeBtn = await page.$('.time-btn:not([disabled])');
          if (timeBtn) {
            const box = await timeBtn.boundingBox();
            if (box) {
              const point = await getRandomXY(box);
              const steps = Math.floor(Math.random() * 6) + 1;
              await moveWithJitter(page, point, steps);
              await delay(Math.floor(Math.random() * 20));
            }
            await timeBtn.click({ delay: Math.floor(Math.random() * 10) + 1 });
            clickedTime = true;
            console.log('[Bot] Time clicked (Random XY)');
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
                const point = await getRandomXY(box);
                const steps = Math.floor(Math.random() * 10) + 5; // 5~15 steps

                // ?뤇截?Micro-Jitter: Use helper for midpoint deviation
                await moveWithJitter(page, point, steps);
                await delay(Math.floor(Math.random() * 20) + 5);
              }
              await startBtn.click({ delay: Math.floor(Math.random() * 15) + 1 });
              clickedStart = true;
              console.log('[Bot] Start booking clicked (Random XY)');
            }
          }
        }

        await delay(30); // Same fast polling interval as before
      } catch (e) {
        // Element might be stale, continue polling
      }
    }

    console.log(`[${iteration}] ??Entry sequence clicked. Waiting for next page...`);

    // 6. Resilient Page Transition (Handling "Target closed" errors)
    let pageSettled = false;
    const navStartTime = Date.now();

    while (Date.now() - navStartTime < 20000) { // Max 20s
      try {
        const currentUrl = page.url();

        // If we are in the Queue, just wait
        if (currentUrl.includes('queue.html')) {
          if (!pageSettled) {
            console.log(`[${iteration}] ??In Queue. Waiting for auto-redirect...`);
            pageSettled = true;
          }
        }
        // If we reached the Seat Map, wait for the grid
        else if (currentUrl.includes('seat_select.html')) {
          const grid = await page.$('#seat-grid');
          if (grid) {
            console.log(`[${iteration}] ?첄 Seat Map reached!`);
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
    console.log(`[${iteration}] ?첄 Proceeding with Seat Selection...`);

    // 7. Seat Selection & Captcha
    console.log(`[${iteration}] ?첄 Seat Map reached! Handling Captcha...`);
    await page.waitForSelector('#captcha-overlay', { visible: true, timeout: 5000 }).catch(() => { });

    // VLM Captcha Solve for Macro: Instant speed
    const captchaOverlay = await page.$('#captcha-overlay:not(.captcha-hidden)');
    if (captchaOverlay) {
      console.log(`[${iteration}] ?썳截?Solving Captcha with Smart Logic (Macro Style)...`);
      const text = await solveCaptchaSmart(page);
      if (text) {
        await page.type('#captcha-input', text, { delay: 0 }); // MACRO: Instant typing
        await page.click('#captcha-submit-btn');
        await delay(500); // Wait for overlay to hide
      }
    }

    // Auto-dismiss alerts (for "Already selected seat" messages)
    page.on('dialog', async dialog => {
      console.log(`[${iteration}] ?좑툘 Alert detected: ${dialog.message()}`);
      await dialog.dismiss();
    });

    // Pick Seat (High-Speed In-Page Logic with Retry - Using Puppeteer clicks)
    const targetSeatCount = Math.floor(Math.random() * 4) + 1; // 1~4 seats random
    console.log(`[${iteration}] ??Starting High-Speed Seat Selection (Target: ${targetSeatCount})...`);

    let selectedCount = 0;
    let attempts = 0;

    while (selectedCount < targetSeatCount && attempts < 50) {
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
          // Fast random point movement with randomized steps and jitter
          const point = await getRandomXY(box);
          const steps = Math.floor(Math.random() * 4) + 1; // 1~5 steps (Extreme Flicker)

          // ?뤇截?Micro-Jitter: Use helper for midpoint deviation
          await moveWithJitter(page, point, steps);
          await delay(Math.floor(Math.random() * 15)); // Almost no pause
        }
        await targetSeat.click({ delay: Math.floor(Math.random() * 10) + 1 });
        await delay(Math.floor(Math.random() * 50) + 20); // ?뤇截?20-70ms confirmation wait

        // 5. Verify selection
        const isSelected = await page.evaluate(el => el.classList.contains('selected'), targetSeat);
        if (isSelected) {
          selectedCount++;
          console.log(`[${iteration}] ??Seat ${selectedCount}/${targetSeatCount} selected successfully`);
        } else {
          attempts++;
        }
      } catch (e) {
        // Seat might have been taken or DOM changed, retry
        attempts++;
      }
    }

    const seatSelectionResult = selectedCount > 0;

    if (seatSelectionResult) {
      console.log(`[${iteration}] ??Seat selected! Clicking Next...`);
      await page.waitForSelector('#next-btn', { visible: true });

      // Robust Click & Wait
      try {
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 10000 }).catch(() => { }),
          page.click('#next-btn')
        ]);
      } catch (e) {
        console.log(`[${iteration}] ??Navigation handled: ${page.url()}`);
      }

      // 7. Discount
      console.log(`[${iteration}] ?뮯 Discount Page...`);
      await page.waitForSelector('.discount-option');

      let discountBtn = await page.$('button[onclick*="confirmDiscount"]');
      if (!discountBtn) {
        const btns = await page.$$('button');
        for (const btn of btns) {
          const txt = await page.evaluate(el => el.textContent, btn);
          if (txt && txt.includes('?ㅼ쓬')) { discountBtn = btn; break; }
        }
      }

      if (discountBtn) {
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          discountBtn.click()
        ]);
        console.log(`[${iteration}] ??Moved to Order Info Page`);
      }

      // 8. Order Info
      console.log(`[${iteration}] ?뱥 Order Info Page...`);
      await page.waitForSelector('#booker-name', { visible: true });

      console.log(`[${iteration}] ??Skipping input (auto-filled). clicking Payment...`);

      // Scroll to button
      let orderBtn = await page.$('button[onclick*="confirmOrderInfo"]');
      if (!orderBtn) {
        const btns = await page.$$('button');
        for (const btn of btns) {
          const txt = await page.evaluate(el => el.textContent, btn);
          if (txt && txt.includes('寃곗젣')) { orderBtn = btn; break; }
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
        console.log(`[${iteration}] ??Moved to Payment Page`);
      }

      // 9. Payment
      console.log(`[${iteration}] ?뮩 Payment Page...`);
      await page.waitForSelector('#total-price');

      let payBtn = await page.$('button[onclick*="processPayment"]');
      if (!payBtn) {
        const btns = await page.$$('button');
        for (const btn of btns) {
          const txt = await page.evaluate(el => el.textContent, btn);
          if (txt && txt.includes('寃곗젣')) { payBtn = btn; break; }
        }
      }

      if (payBtn) {
        await payBtn.click();
        // Payment might take time or use replaceState, just wait for selector or URL
        await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 20000 });
      }

      if (page.url().includes('booking_complete.html')) {
        console.log(`[${iteration}] ?럦 SUCCESS! Booking complete.`);
        console.log(`[${iteration}] ??Waiting for server log sync...`);
        await delay(5000);
      } else {
        console.error(`[${iteration}] ??Failed (Wrong URL): ${page.url()}`);
      }
    }

  } catch (e) {
    console.error(`[${iteration}] ??Error:`, e.message);
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
  console.log('\n??All iterations finished.');
})();

