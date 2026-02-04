const puppeteer = require('puppeteer');

// Configuration
const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 1;
const HEADLESS_MODE = false;

// Utils
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const randomDelay = (min, max) => delay(Math.floor(Math.random() * (max - min + 1)) + min);

// Simulate Human Mouse Movement (Bezier Curve)
async function humanMove(page, x, y) {
  await page.mouse.move(x, y, { steps: 25 + Math.floor(Math.random() * 20) });
}

async function runHumanIteration(iteration) {
  const USER_EMAIL = 'human@email.com';
  const USER_PASS = '1';
  const USER_NAME = 'HumanUser';

  console.log(`\n👨‍💼 Starting Human Iteration ${iteration} / ${LOOP_COUNT}`);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: { width: 1280, height: 800 },
    args: ['--start-maximized']
  });

  try {
    const context = await browser.createIncognitoBrowserContext();
    const page = await context.newPage();

    console.log(`[${iteration}] TARGET: ${BASE_URL}`);

    // 1. Visit Site
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    await randomDelay(1500, 3000); // "Reading the page"

    // 2. Login
    console.log(`[${iteration}] 🔑 Logging in (human style)...`);
    await page.goto(`${BASE_URL}login.html`, { waitUntil: 'networkidle2' });

    await randomDelay(1000, 2000);
    await page.type('#email', USER_EMAIL, { delay: 100 + Math.random() * 100 }); // Typing speed
    await randomDelay(500, 1000);
    await page.type('#password', USER_PASS, { delay: 150 + Math.random() * 100 });

    await randomDelay(800, 1500);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      page.click('button[type="submit"]')
    ]);

    // 3. Select Performance
    console.log(`[${iteration}] 🎭 Browsing performances...`);
    await randomDelay(2000, 4000);
    const perfCard = await page.$('.performance-card');
    if (perfCard) {
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'networkidle2' }),
        perfCard.click()
      ]);
    }

    // 🏷️ Tag this log as 'human'
    await page.evaluate(() => {
      if (typeof updateMetadata === 'function') {
        updateMetadata({ bot_type: 'human' });
      }
    });

    // 4. Select Date/Time
    console.log(`[${iteration}] 📅 Selecting date and time...`);
    await page.waitForSelector('.date-btn:not([disabled])');
    const dateBtns = await page.$$('.date-btn:not([disabled])');
    if (dateBtns.length > 0) {
      await dateBtns[0].click();
    }
    await randomDelay(1000, 2000);

    await page.waitForSelector('.time-btn:not([disabled])');
    const timeBtns = await page.$$('.time-btn:not([disabled])');
    if (timeBtns.length > 0) {
      await timeBtns[0].click();
    }

    await randomDelay(1500, 2500);
    console.log(`[${iteration}] 🎫 Clicking Start Booking...`);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      page.click('#start-booking-btn')
    ]);

    // 5. Seat Selection & Captcha
    console.log(`[${iteration}] 🪑 Seat selection (human speed)...`);
    // Wait through queue if exists
    try {
      if (page.url().includes('queue.html')) {
        console.log(`[${iteration}] ⏳ In queue...`);
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 60000 });
      }
    } catch (e) { }

    await page.waitForSelector('.seat.available', { timeout: 30000 });

    // Simulate thinking about captcha
    console.log(`[${iteration}] 🛡️ Solving captcha (simulated delay)...`);
    await randomDelay(6000, 10000);

    await page.evaluate(() => {
      if (window.isCaptchaVerified !== undefined) {
        window.isCaptchaVerified = true;
        const overlay = document.getElementById('captcha-overlay');
        if (overlay) overlay.classList.add('captcha-hidden'); // The macro uses 'captcha-hidden'
        if (sessionStorage) sessionStorage.setItem('captchaVerified', 'true');
      }
    });

    await randomDelay(3000, 5000);
    const availableSeats = await page.$$('.seat.available');
    if (availableSeats.length > 0) {
      const targetSeat = availableSeats[Math.floor(Math.random() * Math.min(availableSeats.length, 10))];
      await targetSeat.click();
    }

    await randomDelay(2000, 3500);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      page.click('#next-btn')
    ]);

    // 6. Discount/Order/Payment
    const stages = ['💸 Discount', '📋 Order Info', '💳 Payment'];
    for (const stageName of stages) {
      console.log(`[${iteration}] ${stageName} Page...`);
      await randomDelay(3000, 5000);

      let nextBtn = await page.$('button.btn-primary');
      if (!nextBtn) {
        const allBtns = await page.$$('button');
        for (const b of allBtns) {
          const bText = await page.evaluate(el => el.textContent, b);
          if (bText && (bText.includes('다음') || bText.includes('결제'))) {
            nextBtn = b;
            break;
          }
        }
      }

      if (nextBtn) {
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => { }),
          nextBtn.click()
        ]);
      }
    }

    if (page.url().includes('booking_complete.html')) {
      console.log(`[${iteration}] 🎉 SUCCESS! Human booking complete.`);
      console.log(`[${iteration}] ⏳ Waiting for logs to sync...`);
      await delay(5000);
    }

  } catch (e) {
    console.error(`[${iteration}] ❌ Error:`, e.stack);
  } finally {
    await browser.close();
  }
}

(async () => {
  for (let i = 1; i <= LOOP_COUNT; i++) {
    await runHumanIteration(i);
    if (i < LOOP_COUNT) await randomDelay(5000, 10000);
  }
  console.log('\n✅ Human data collection finished.');
})();
