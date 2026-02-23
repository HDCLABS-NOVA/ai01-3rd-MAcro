const puppeteer = require('puppeteer');

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000/';
const LOOP_COUNT = Number(process.env.LOOP_COUNT || 300);
const HEADLESS_MODE = process.env.HEADLESS_MODE
  ? String(process.env.HEADLESS_MODE).toLowerCase() === 'true'
  : true;
const BOT_TYPE = process.env.BOT_TYPE || 'test/macro';
const DETAIL_DEADLINE_MS = Number(process.env.DETAIL_DEADLINE_MS || 60000);

const PROFILES = [
  {
    name: 'burst_overshoot',
    weight: 0.4,
    pollMinMs: 4,
    pollMaxMs: 22,
    pauseChance: 0.2,
    pauseMinMs: 70,
    pauseMaxMs: 240,
    moveStepsMin: 2,
    moveStepsMax: 8,
    overshootChance: 0.75,
    overshootScaleMin: 1.02,
    overshootScaleMax: 1.08,
    overshootJitterPx: 10,
    clickDelayMinMs: 1,
    clickDelayMaxMs: 8,
    captchaKeyDelayMinMs: 0,
    captchaKeyDelayMaxMs: 1,
    targetSeatMin: 1,
    targetSeatMax: 3,
    seatStrategy: 'front_bias',
    seatPoolMax: 10,
    maxSeatAttempts: 55,
    confirmWaitMinMs: 18,
    confirmWaitMaxMs: 60,
    backoffBaseMs: 80,
    backoffStepMs: 18,
    backoffCapMs: 380,
    sessionGapMinMs: 1200,
    sessionGapMaxMs: 2800,
  },
  {
    name: 'paced_humanish',
    weight: 0.35,
    pollMinMs: 18,
    pollMaxMs: 70,
    pauseChance: 0.35,
    pauseMinMs: 120,
    pauseMaxMs: 420,
    moveStepsMin: 6,
    moveStepsMax: 16,
    overshootChance: 0.35,
    overshootScaleMin: 1.01,
    overshootScaleMax: 1.04,
    overshootJitterPx: 6,
    clickDelayMinMs: 6,
    clickDelayMaxMs: 25,
    captchaKeyDelayMinMs: 3,
    captchaKeyDelayMaxMs: 10,
    targetSeatMin: 1,
    targetSeatMax: 2,
    seatStrategy: 'middle_bias',
    seatPoolMax: 24,
    maxSeatAttempts: 45,
    confirmWaitMinMs: 50,
    confirmWaitMaxMs: 140,
    backoffBaseMs: 130,
    backoffStepMs: 24,
    backoffCapMs: 700,
    sessionGapMinMs: 2200,
    sessionGapMaxMs: 5000,
  },
  {
    name: 'hybrid_spread',
    weight: 0.25,
    pollMinMs: 8,
    pollMaxMs: 45,
    pauseChance: 0.28,
    pauseMinMs: 90,
    pauseMaxMs: 320,
    moveStepsMin: 4,
    moveStepsMax: 12,
    overshootChance: 0.55,
    overshootScaleMin: 1.01,
    overshootScaleMax: 1.06,
    overshootJitterPx: 8,
    clickDelayMinMs: 2,
    clickDelayMaxMs: 14,
    captchaKeyDelayMinMs: 0,
    captchaKeyDelayMaxMs: 4,
    targetSeatMin: 1,
    targetSeatMax: 4,
    seatStrategy: 'spread',
    seatPoolMax: 30,
    maxSeatAttempts: 50,
    confirmWaitMinMs: 25,
    confirmWaitMaxMs: 90,
    backoffBaseMs: 100,
    backoffStepMs: 20,
    backoffCapMs: 520,
    sessionGapMinMs: 1800,
    sessionGapMaxMs: 3600,
  },
];

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const randomInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;

function pickProfile() {
  const sum = PROFILES.reduce((acc, p) => acc + p.weight, 0);
  let r = Math.random() * sum;
  for (const p of PROFILES) {
    r -= p.weight;
    if (r <= 0) return p;
  }
  return PROFILES[PROFILES.length - 1];
}

async function getRandomXY(box, padding = 3) {
  return {
    x: box.x + padding + Math.random() * Math.max(1, box.width - padding * 2),
    y: box.y + padding + Math.random() * Math.max(1, box.height - padding * 2),
  };
}

async function moveWithJitter(page, targetPoint, totalSteps, jitterPx = 4) {
  const current = await page.evaluate(() => ({ x: window.mouseX || 0, y: window.mouseY || 0 }));
  const midX = (current.x + targetPoint.x) / 2 + (Math.random() * jitterPx * 2 - jitterPx);
  const midY = (current.y + targetPoint.y) / 2 + (Math.random() * jitterPx * 2 - jitterPx);
  const steps1 = Math.max(1, Math.floor(totalSteps / 2));
  const steps2 = Math.max(1, totalSteps - steps1);
  await page.mouse.move(midX, midY, { steps: steps1 });
  await page.mouse.move(targetPoint.x, targetPoint.y, { steps: steps2 });
}

async function moveWithOvershoot(page, targetPoint, totalSteps, profile) {
  const current = await page.evaluate(() => ({ x: window.mouseX || 0, y: window.mouseY || 0 }));
  const scale = profile.overshootScaleMin + Math.random() * (profile.overshootScaleMax - profile.overshootScaleMin);
  const dx = targetPoint.x - current.x;
  const dy = targetPoint.y - current.y;
  const overshoot = {
    x: targetPoint.x + dx * (scale - 1) + (Math.random() * profile.overshootJitterPx * 2 - profile.overshootJitterPx),
    y: targetPoint.y + dy * (scale - 1) + (Math.random() * profile.overshootJitterPx * 2 - profile.overshootJitterPx),
  };
  const steps1 = Math.max(1, Math.floor(totalSteps * 0.6));
  const steps2 = Math.max(1, totalSteps - steps1);
  await page.mouse.move(overshoot.x, overshoot.y, { steps: steps1 });
  await page.mouse.move(targetPoint.x, targetPoint.y, { steps: steps2 });
}

async function moveToTarget(page, targetPoint, profile) {
  const steps = randomInt(profile.moveStepsMin, profile.moveStepsMax);
  if (Math.random() < profile.overshootChance) {
    await moveWithOvershoot(page, targetPoint, steps, profile);
  } else {
    await moveWithJitter(page, targetPoint, steps, 4);
  }
}

async function safeGoto(page, url, retries = 3) {
  for (let i = 0; i < retries; i += 1) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      return true;
    } catch (e) {
      if (i === retries - 1) return false;
      await delay(1000);
    }
  }
  return false;
}

async function safeCloseBrowser(browser) {
  if (!browser) return;
  for (let i = 0; i < 3; i += 1) {
    try {
      if (browser.isConnected()) {
        await browser.close();
      }
      return;
    } catch (e) {
      await delay(250 * (i + 1));
    }
  }

  try {
    const proc = browser.process();
    if (proc && !proc.killed) {
      proc.kill('SIGKILL');
    }
  } catch (e) {
    // ignore hard-close errors
  }
}

async function solveCaptchaSmart(page, profile) {
  try {
    await page.waitForFunction(() => window.currentCaptcha && window.currentCaptcha.length > 0, { timeout: 5000 });
    const text = await page.evaluate(() => window.currentCaptcha);
    if (!text) return false;

    const input = await page.$('#captcha-input');
    if (!input) return false;

    await input.click({ clickCount: 3 });
    await page.keyboard.type(text, {
      delay: randomInt(profile.captchaKeyDelayMinMs, profile.captchaKeyDelayMaxMs),
    });
    await page.click('#captcha-submit-btn');
    await delay(randomInt(200, 600));
    return true;
  } catch (e) {
    return false;
  }
}

async function pickSeatHandle(page, profile) {
  const availableSeats = await page.$$('.seat.available:not(.selected)');
  if (!availableSeats.length) return null;

  if (profile.seatStrategy === 'front_bias') {
    const maxPool = Math.min(profile.seatPoolMax, availableSeats.length);
    const idx = randomInt(0, Math.max(0, maxPool - 1));
    return availableSeats[idx];
  }

  if (profile.seatStrategy === 'middle_bias') {
    const start = Math.floor(availableSeats.length * 0.3);
    const end = Math.max(start, Math.floor(availableSeats.length * 0.7));
    const idx = randomInt(start, end);
    return availableSeats[Math.min(idx, availableSeats.length - 1)];
  }

  const spreadPool = Math.min(profile.seatPoolMax, availableSeats.length);
  const idx = randomInt(0, Math.max(0, spreadPool - 1));
  return availableSeats[idx];
}

async function runBotIteration(iteration) {
  const profile = pickProfile();
  const USER_EMAIL = 'macro@email.com';
  const USER_PASS = '1';
  const TARGET_PERF_ID = 'perf001';

  console.log(`\n[TEST-MACRO] Iteration ${iteration}/${LOOP_COUNT} | profile=${profile.name}`);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: null,
    args: ['--start-maximized'],
  });

  try {
    const pages = await browser.pages();
    const page = pages[0];

    await page.evaluateOnNewDocument(() => {
      window.mouseX = 0;
      window.mouseY = 0;
      window.addEventListener('mousemove', (e) => {
        window.mouseX = e.clientX;
        window.mouseY = e.clientY;
      });
    });

    page.on('console', (msg) => {
      const text = msg.text();
      if (!text.includes('HMR') && !text.includes('Hot')) {
        console.log(`[Browser ${msg.type()}] ${text}`);
      }
    });

    await page.goto(BASE_URL, { waitUntil: 'networkidle0' });
    await page.mouse.move(Math.random() * 800, Math.random() * 600);
    await page.evaluate((botType) => {
      sessionStorage.setItem('bot_type', botType);
    }, BOT_TYPE);

    const ngrokBtn = await page.$('button');
    if (ngrokBtn) {
      const btnText = await page.evaluate((el) => el.textContent, ngrokBtn);
      if (btnText && btnText.includes('Visit Site')) {
        await ngrokBtn.click();
        await page.waitForNavigation({ waitUntil: 'networkidle0' });
      }
    }

    const loginReady = page.url().includes('login.html') || (await safeGoto(page, `${BASE_URL}login.html`, 3));
    if (!loginReady) throw new Error('login page load failed');

    await page.type('#email', USER_EMAIL);
    await page.type('#password', USER_PASS);

    const loginBtn = await page.$('button[type="submit"]');
    if (loginBtn) {
      const box = await loginBtn.boundingBox();
      if (box) {
        const point = await getRandomXY(box);
        await moveToTarget(page, point, profile);
      }
      await loginBtn.click({ delay: randomInt(profile.clickDelayMinMs, profile.clickDelayMaxMs) });
      await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 30000 }).catch(() => {});
    }

    await page.goto(`${BASE_URL}index.html`, { waitUntil: 'networkidle0' });
    await page.waitForSelector(`.performance-card[onclick*="${TARGET_PERF_ID}"]`);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle0' }),
      page.click(`.performance-card[onclick*="${TARGET_PERF_ID}"]`),
    ]);

    // Some runs bounce back to index/login; force detail page if needed.
    if (!page.url().includes('performance_detail.html')) {
      await safeGoto(page, `${BASE_URL}performance_detail.html?id=${TARGET_PERF_ID}`, 2);
    }

    await page.evaluate((botType) => {
      if (typeof updateMetadata === 'function') {
        updateMetadata({ bot_type: botType });
      }
    }, BOT_TYPE);

    let clickedDate = false;
    let clickedTime = false;
    let clickedStart = false;
    const detailDeadline = Date.now() + DETAIL_DEADLINE_MS;

    while (!clickedStart && Date.now() < detailDeadline) {
      await delay(randomInt(profile.pollMinMs, profile.pollMaxMs));
      if (Math.random() < profile.pauseChance) {
        await delay(randomInt(profile.pauseMinMs, profile.pauseMaxMs));
      }

      try {
        if (!clickedDate) {
          const dateBtn = await page.$('.date-btn:not([disabled])');
          if (dateBtn) {
            const box = await dateBtn.boundingBox();
            if (box) {
              const point = await getRandomXY(box);
              await moveToTarget(page, point, profile);
            }
            await dateBtn.click({ delay: randomInt(profile.clickDelayMinMs, profile.clickDelayMaxMs) });
            clickedDate = true;
          }
        }

        if (clickedDate && !clickedTime) {
          const timeBtn = await page.$('.time-btn:not([disabled])');
          if (timeBtn) {
            const box = await timeBtn.boundingBox();
            if (box) {
              const point = await getRandomXY(box);
              await moveToTarget(page, point, profile);
            }
            await timeBtn.click({ delay: randomInt(profile.clickDelayMinMs, profile.clickDelayMaxMs) });
            clickedTime = true;
          }
        }

        if (clickedTime && !clickedStart) {
          const startBtn = await page.$('#start-booking-btn');
          if (startBtn) {
            const isVisible = await page.evaluate((el) => {
              const style = window.getComputedStyle(el);
              return style.display !== 'none' && el.style.display !== 'none';
            }, startBtn);
            if (isVisible) {
              const box = await startBtn.boundingBox();
              if (box) {
                const point = await getRandomXY(box);
                await moveToTarget(page, point, profile);
              }
              await startBtn.click({ delay: randomInt(profile.clickDelayMinMs, profile.clickDelayMaxMs) });
              clickedStart = true;
            }
          }
        }
      } catch (e) {
        // continue polling
      }
    }

    if (!clickedStart) {
      const debug = await page.evaluate(() => {
        const dateEnabled = !!document.querySelector('.date-btn:not([disabled])');
        const timeEnabled = !!document.querySelector('.time-btn:not([disabled])');
        const startBtn = document.querySelector('#start-booking-btn');
        const startVisible = !!(
          startBtn &&
          getComputedStyle(startBtn).display !== 'none' &&
          startBtn.style.display !== 'none'
        );
        return {
          href: location.href,
          dateEnabled,
          timeEnabled,
          startVisible,
        };
      }).catch(() => ({ href: 'unknown', dateEnabled: false, timeEnabled: false, startVisible: false }));
      throw new Error(
        `failed to click booking start in time: url=${debug.href}, dateEnabled=${debug.dateEnabled}, timeEnabled=${debug.timeEnabled}, startVisible=${debug.startVisible}`
      );
    }

    const navStart = Date.now();
    while (Date.now() - navStart < 20000) {
      try {
        const currentUrl = page.url();
        if (currentUrl.includes('seat_select.html')) {
          const grid = await page.$('#seat-grid');
          if (grid) break;
        }
      } catch (e) {
        // ignore during transition
      }
      await delay(200);
    }

    await page.waitForSelector('#captcha-overlay', { visible: true, timeout: 5000 }).catch(() => {});
    const captchaOverlay = await page.$('#captcha-overlay:not(.captcha-hidden)');
    if (captchaOverlay) {
      await solveCaptchaSmart(page, profile);
    }

    page.on('dialog', async (dialog) => {
      await dialog.dismiss();
    });

    const targetSeatCount = randomInt(profile.targetSeatMin, profile.targetSeatMax);
    let selectedCount = 0;
    let attempts = 0;

    while (selectedCount < targetSeatCount && attempts < profile.maxSeatAttempts) {
      try {
        const alertOverlay = await page.$('#alert-overlay');
        if (alertOverlay) {
          const isActive = await page.evaluate((el) => el.classList.contains('active'), alertOverlay);
          if (isActive) {
            const confirmBtn = await page.$('#alert-confirm-btn');
            if (confirmBtn) {
              await confirmBtn.click();
              await delay(randomInt(120, 300));
            }
          }
        }

        const targetSeat = await pickSeatHandle(page, profile);
        if (!targetSeat) {
          attempts += 1;
          await delay(randomInt(90, 180));
          continue;
        }

        const box = await targetSeat.boundingBox();
        if (box) {
          const point = await getRandomXY(box);
          await moveToTarget(page, point, profile);
        }

        await targetSeat.click({ delay: randomInt(profile.clickDelayMinMs, profile.clickDelayMaxMs) });
        await delay(randomInt(profile.confirmWaitMinMs, profile.confirmWaitMaxMs));

        const isSelected = await page.evaluate((el) => el.classList.contains('selected'), targetSeat);
        if (isSelected) {
          selectedCount += 1;
        } else {
          attempts += 1;
          const backoff = Math.min(profile.backoffCapMs, profile.backoffBaseMs + attempts * profile.backoffStepMs);
          await delay(backoff);
        }
      } catch (e) {
        attempts += 1;
      }
    }

    if (selectedCount > 0) {
      await page.waitForSelector('#next-btn', { visible: true });
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 12000 }).catch(() => {}),
        page.click('#next-btn'),
      ]);

      await page.waitForSelector('.discount-option');
      let discountBtn = await page.$('button[onclick*="confirmDiscount"]');
      if (!discountBtn) {
        const btns = await page.$$('button');
        for (const btn of btns) {
          const txt = await page.evaluate((el) => el.textContent, btn);
          if (txt && txt.includes('다음')) {
            discountBtn = btn;
            break;
          }
        }
      }
      if (discountBtn) {
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          discountBtn.click(),
        ]);
      }

      await page.waitForSelector('#booker-name', { visible: true });
      let orderBtn = await page.$('button[onclick*="confirmOrderInfo"]');
      if (!orderBtn) {
        const btns = await page.$$('button');
        for (const btn of btns) {
          const txt = await page.evaluate((el) => el.textContent, btn);
          if (txt && txt.includes('결제')) {
            orderBtn = btn;
            break;
          }
        }
      }
      if (orderBtn) {
        await page.evaluate((btn) => btn.scrollIntoView(), orderBtn);
        await delay(400);
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          orderBtn.click(),
        ]);
      }

      await page.waitForSelector('#total-price');
      let payBtn = await page.$('button[onclick*="processPayment"]');
      if (!payBtn) {
        const btns = await page.$$('button');
        for (const btn of btns) {
          const txt = await page.evaluate((el) => el.textContent, btn);
          if (txt && txt.includes('결제')) {
            payBtn = btn;
            break;
          }
        }
      }

      if (payBtn) {
        await payBtn.click();
        await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 20000 });
      }

      if (page.url().includes('booking_complete.html')) {
        console.log(`[TEST-MACRO] Iteration ${iteration} success (profile=${profile.name})`);
        await delay(5000);
      } else {
        console.log(`[TEST-MACRO] Iteration ${iteration} ended without completion URL (profile=${profile.name})`);
      }
    }
  } catch (e) {
    console.error(`[TEST-MACRO] Iteration ${iteration} error:`, e.message);
  } finally {
    await delay(1800);
    await safeCloseBrowser(browser);
  }

  await delay(randomInt(profile.sessionGapMinMs, profile.sessionGapMaxMs));
}

(async () => {
  for (let i = 1; i <= LOOP_COUNT; i += 1) {
    try {
      await runBotIteration(i);
    } catch (e) {
      console.error(`[TEST-MACRO] Iteration ${i} fatal error:`, e.message);
    }
  }
  console.log('[TEST-MACRO] all iterations finished');
})();
