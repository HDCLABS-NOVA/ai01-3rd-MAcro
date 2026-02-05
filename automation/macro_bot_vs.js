const puppeteer = require('puppeteer');

const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 300;
const HEADLESS_MODE = true;

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const randomDelay = (min, max) => delay(Math.floor(Math.random() * (max - min + 1)) + min);

async function runBotIteration(iteration) {
  const USER_EMAIL = 'macro@email.com';
  const USER_PASS = '1';

  console.log(`\n🤖 [BATTLE] Pure Macro Iteration ${iteration}`);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    args: ['--no-sandbox']
  });

  try {
    const context = await browser.createIncognitoBrowserContext();
    const page = await context.newPage();

    // 🚦 BATTLE SYNC: Wait for human to login
    await delay(4500);

    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    await page.evaluate(() => { sessionStorage.setItem('bot_type', 'macro'); });

    // Login (Instant)
    await page.goto(`${BASE_URL}login.html`, { waitUntil: 'networkidle2' });
    await page.evaluate((e, p) => {
      document.getElementById('email').value = e;
      document.getElementById('password').value = p;
      document.querySelector('button[type="submit"]').click();
    }, USER_EMAIL, USER_PASS);
    await page.waitForNavigation({ waitUntil: 'networkidle2' });

    // Navigate (Instant)
    await page.waitForSelector('.performance-card');
    await page.click('.performance-card');
    await page.waitForSelector('.date-btn:not([disabled])');
    await page.click('.date-btn:not([disabled])');
    await page.click('.time-btn:not([disabled])');
    await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle2' }), page.click('#start-booking-btn')]);

    // Handle Queue
    try {
      if (page.url().includes('queue.html')) {
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 60000 });
      }
    } catch (e) { }

    // Seat Page & Captcha Bypass
    await page.waitForSelector('#seat-grid', { timeout: 30000 });
    await page.evaluate(() => {
      window.isCaptchaVerified = true;
      if (sessionStorage) sessionStorage.setItem('captchaVerified', 'true');
      const overlay = document.getElementById('captcha-overlay');
      if (overlay) overlay.classList.add('captcha-hidden');
    });

    let seatSelected = false;
    let attempts = 0;
    while (!seatSelected && attempts < 15) {
      const availableSeats = await page.$$('.seat.available');
      if (availableSeats.length === 0) break;
      const targetSeat = availableSeats[Math.floor(Math.random() * Math.min(availableSeats.length, 10))];
      await targetSeat.click({ delay: 1 });
      await delay(100);
      const isSelected = await page.evaluate(el => el.classList.contains('selected'), targetSeat);
      if (isSelected) seatSelected = true;
      else attempts++;
    }

    if (seatSelected) {
      await page.waitForSelector('#next-btn');
      await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded' }), page.click('#next-btn')]);

      // Fast finish for macro
      for (let i = 0; i < 3; i++) {
        await delay(200);
        let btn = await page.$('button.btn-primary') || await page.$('button[onclick*="confirm"]');
        if (btn) await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 5000 }).catch(() => { }), btn.click()]);
      }

      if (page.url().includes('booking_complete.html')) {
        console.log(`[${iteration}] 🎉 SUCCESS! Macro log saved.`);
        await delay(2000);
      }
    }
  } catch (e) { }
  finally { await browser.close(); }
}

(async () => {
  for (let i = 1; i <= LOOP_COUNT; i++) {
    await runBotIteration(i);
    await delay(2000);
  }
})();
