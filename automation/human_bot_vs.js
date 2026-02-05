const puppeteer = require('puppeteer');

const BASE_URL = 'http://localhost:8000/';
const LOOP_COUNT = 300;
const HEADLESS_MODE = true;

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const randomDelay = (min, max) => delay(Math.floor(Math.random() * (max - min + 1)) + min);

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

  console.log(`\n👨‍💼 [BATTLE] Expert Human Iteration ${iteration}`);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: { width: 1280, height: 800 },
    args: ['--no-sandbox']
  });

  try {
    const context = await browser.createIncognitoBrowserContext();
    const page = await context.newPage();
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    await page.evaluate(() => { sessionStorage.setItem('bot_type', 'human'); });

    // Login
    await page.goto(`${BASE_URL}login.html`, { waitUntil: 'networkidle2' });
    await page.type('#email', USER_EMAIL, { delay: 40 + Math.random() * 40 });
    await page.type('#password', USER_PASS, { delay: 40 + Math.random() * 40 });
    await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle2' }), page.click('button[type="submit"]')]);

    // Perf
    await page.waitForSelector('.performance-card');
    await page.click('.performance-card');
    await page.waitForSelector('.date-btn:not([disabled])');
    await page.click('.date-btn:not([disabled])');
    await randomDelay(300, 600);
    await page.waitForSelector('.time-btn:not([disabled])');
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
      if (overlay) { overlay.classList.add('captcha-hidden'); overlay.style.display = 'none'; }
    });

    await randomDelay(500, 1000);

    let humanSeatSelected = false;
    let humanAttempts = 0;
    while (!humanSeatSelected && humanAttempts < 5) {
      const availableSeats = await page.$$('.seat.available');
      if (availableSeats.length === 0) break;
      const targetSeat = availableSeats[Math.floor(Math.random() * Math.min(availableSeats.length, 10))];
      const box = await targetSeat.boundingBox();
      if (box) {
        await humanMove(page, box.x + box.width / 2, box.y + box.height / 2);
        await targetSeat.click({ delay: 40 + Math.random() * 30 });
      }
      await randomDelay(400, 600);
      const isSelected = await page.evaluate(el => el.classList.contains('selected'), targetSeat);
      if (isSelected) humanSeatSelected = true;
      else humanAttempts++;
    }

    await randomDelay(400, 800);
    await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle2' }), page.click('#next-btn')]);

    // Fast finish to save log
    for (let i = 0; i < 3; i++) {
      await randomDelay(500, 1000);
      let btn = await page.$('button.btn-primary') || await page.$('button[onclick*="confirm"]');
      if (btn) await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 5000 }).catch(() => { }), btn.click()]);
    }

    if (page.url().includes('booking_complete.html')) {
      console.log(`[${iteration}] 🎉 SUCCESS! Expert Human log saved.`);
      await delay(2000);
    }
  } catch (e) { console.error(`[${iteration}] ❌ Error:`, e.message); }
  finally { await browser.close(); }
}

(async () => {
  for (let i = 1; i <= LOOP_COUNT; i++) {
    await runHumanIteration(i);
    await delay(2000);
  }
})();
