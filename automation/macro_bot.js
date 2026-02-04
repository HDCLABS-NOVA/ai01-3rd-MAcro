const puppeteer = require('puppeteer');

// Configuration
const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 10; // 🔄 Set this to the number of times you want to run
const HEADLESS_MODE = true; // Set true for faster background execution

// Utils
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
    let context;
    if (browser.createIncognitoBrowserContext) {
      context = await browser.createIncognitoBrowserContext();
    } else {
      context = await browser.createBrowserContext(); // Fallback
    }
    const page = await context.newPage();

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

    // 4. Index -> Detail
    console.log(`[${iteration}] 🎭 Selecting Performance...`);
    await page.goto(`${BASE_URL}index.html`, { waitUntil: 'networkidle0' });
    await page.waitForSelector('.performance-card');
    const performances = await page.$$('.performance-card');
    if (performances.length > 0) await performances[0].click();
    await page.waitForNavigation();

    // 🏷️ Tag this log as 'macro'
    await page.evaluate(() => {
      if (typeof updateMetadata === 'function') {
        updateMetadata({ bot_type: 'macro' });
      }
    });

    // 5. Detail Page
    console.log(`[${iteration}] 📅 Selecting Date/Time...`);
    await page.waitForSelector('.date-btn:not([disabled])', { timeout: 10000 });
    const dateBtns = await page.$$('.date-btn:not([disabled])');
    if (dateBtns.length > 0) await dateBtns[0].click();
    await randomDelay(300, 600);

    await page.waitForSelector('.time-btn:not([disabled])');
    const timeBtns = await page.$$('.time-btn:not([disabled])');
    if (timeBtns.length > 0) await timeBtns[0].click();
    await randomDelay(300, 600);

    await page.click('#start-booking-btn');

    // 6. Seat Selection & Captcha
    await page.waitForSelector('#seat-grid', { timeout: 30000 });
    console.log(`[${iteration}] 🪑 Seat Selection...`);

    await delay(2000);
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

    // Pick Seat
    let seatSelected = false;
    let attempts = 0;
    while (!seatSelected && attempts < 10) {
      const availableSeats = await page.$$('.seat.available');
      if (availableSeats.length === 0) break;
      const targetSeat = availableSeats[Math.floor(Math.random() * Math.min(10, availableSeats.length))];

      // Safety check if seat exists
      if (!targetSeat) break;

      await targetSeat.click();
      await randomDelay(100, 300);
      const isSelected = await page.evaluate(el => el.classList.contains('selected'), targetSeat);
      if (isSelected) seatSelected = true;
      else attempts++;
    }

    // Add safe dialog handler
    page.on('dialog', async dialog => {
      console.log(`[${iteration}] 💬 Alert detected: ${dialog.message()}`);
      await dialog.dismiss();
    });

    if (seatSelected) {
      console.log(`[${iteration}] ✅ Seat selected. Clicking Next...`);
      await page.waitForSelector('#next-btn', { visible: true });

      await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
        page.click('#next-btn')
      ]);
      console.log(`[${iteration}] ⏩ Moved to Discount Page`);

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
