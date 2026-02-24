const puppeteer = require('puppeteer');

const BASE_URL = (process.env.BASE_URL || 'http://localhost:8000/').replace(/\/+$/, '') + '/';
const LOOP_COUNT = Number(process.env.LOOP_COUNT || 200);
const HEADLESS_MODE = process.env.HEADLESS_MODE
  ? String(process.env.HEADLESS_MODE).toLowerCase() === 'true'
  : false;
const BOT_TYPE = process.env.BOT_TYPE || 'simul/macro';
const DETAIL_DEADLINE_MS = Number(process.env.DETAIL_DEADLINE_MS || 70000);
const SEAT_PAGE_TIMEOUT_MS = Number(process.env.SEAT_PAGE_TIMEOUT_MS || 35000);

const USER_EMAIL = process.env.USER_EMAIL || 'macro@email.com';
const USER_PASS = process.env.USER_PASS || '1';
const TARGET_PERF_ID = process.env.TARGET_PERF_ID || 'perf001';

const PROFILES = [
  {
    name: 'humanized_reactive',
    weight: 0.45,
    pollMinMs: 80,
    pollMaxMs: 220,
    burstPollMinMs: 10,
    burstPollMaxMs: 28,
    burstWindowChecks: 24,
    idleChance: 0.30,
    idleMinMs: 140,
    idleMaxMs: 420,
    moveStepsMin: 10,
    moveStepsMax: 22,
    overshootChance: 0.22,
    overshootPxMin: 2,
    overshootPxMax: 8,
    preClickDwellMinMs: 45,
    preClickDwellMaxMs: 150,
    clickDelayMinMs: 18,
    clickDelayMaxMs: 65,
    typingDelayMinMs: 35,
    typingDelayMaxMs: 120,
    captchaFastBurstChance: 0.28,
    captchaFastDelayMinMs: 0,
    captchaFastDelayMaxMs: 6,
    captchaBackspaceChance: 0.08,
    targetSeatMin: 1,
    targetSeatMax: 2,
    seatPoolMax: 26,
    deterministicSeatBias: 0.55,
    maxSeatAttempts: 32,
    seatConfirmMinMs: 90,
    seatConfirmMaxMs: 220,
    backoffBaseMs: 130,
    backoffStepMs: 22,
    backoffCapMs: 800,
    sessionGapMinMs: 2200,
    sessionGapMaxMs: 5200,
  },
  {
    name: 'smooth_then_burst',
    weight: 0.35,
    pollMinMs: 60,
    pollMaxMs: 170,
    burstPollMinMs: 6,
    burstPollMaxMs: 20,
    burstWindowChecks: 32,
    idleChance: 0.22,
    idleMinMs: 110,
    idleMaxMs: 340,
    moveStepsMin: 8,
    moveStepsMax: 18,
    overshootChance: 0.35,
    overshootPxMin: 3,
    overshootPxMax: 10,
    preClickDwellMinMs: 30,
    preClickDwellMaxMs: 110,
    clickDelayMinMs: 8,
    clickDelayMaxMs: 40,
    typingDelayMinMs: 22,
    typingDelayMaxMs: 90,
    captchaFastBurstChance: 0.42,
    captchaFastDelayMinMs: 0,
    captchaFastDelayMaxMs: 4,
    captchaBackspaceChance: 0.05,
    targetSeatMin: 1,
    targetSeatMax: 3,
    seatPoolMax: 18,
    deterministicSeatBias: 0.72,
    maxSeatAttempts: 36,
    seatConfirmMinMs: 60,
    seatConfirmMaxMs: 170,
    backoffBaseMs: 100,
    backoffStepMs: 18,
    backoffCapMs: 640,
    sessionGapMinMs: 1800,
    sessionGapMaxMs: 4200,
  },
  {
    name: 'macro_tinted_human',
    weight: 0.20,
    pollMinMs: 45,
    pollMaxMs: 120,
    burstPollMinMs: 4,
    burstPollMaxMs: 16,
    burstWindowChecks: 42,
    idleChance: 0.16,
    idleMinMs: 80,
    idleMaxMs: 240,
    moveStepsMin: 5,
    moveStepsMax: 14,
    overshootChance: 0.44,
    overshootPxMin: 4,
    overshootPxMax: 12,
    preClickDwellMinMs: 20,
    preClickDwellMaxMs: 85,
    clickDelayMinMs: 4,
    clickDelayMaxMs: 24,
    typingDelayMinMs: 14,
    typingDelayMaxMs: 70,
    captchaFastBurstChance: 0.62,
    captchaFastDelayMinMs: 0,
    captchaFastDelayMaxMs: 2,
    captchaBackspaceChance: 0.02,
    targetSeatMin: 2,
    targetSeatMax: 4,
    seatPoolMax: 14,
    deterministicSeatBias: 0.86,
    maxSeatAttempts: 42,
    seatConfirmMinMs: 40,
    seatConfirmMaxMs: 120,
    backoffBaseMs: 80,
    backoffStepMs: 16,
    backoffCapMs: 520,
    sessionGapMinMs: 1400,
    sessionGapMaxMs: 3000,
  },
];

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const randomInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const chance = (p) => Math.random() < p;

function pickProfile() {
  const total = PROFILES.reduce((acc, x) => acc + x.weight, 0);
  let r = Math.random() * total;
  for (const p of PROFILES) {
    r -= p.weight;
    if (r <= 0) return p;
  }
  return PROFILES[PROFILES.length - 1];
}

async function safeCloseBrowser(browser) {
  if (!browser) return;
  for (let i = 0; i < 3; i += 1) {
    try {
      if (browser.isConnected()) {
        await browser.close();
      }
      return;
    } catch (_) {
      await delay(220 * (i + 1));
    }
  }
  try {
    const proc = browser.process();
    if (proc && !proc.killed) proc.kill('SIGKILL');
  } catch (_) {
    // ignore
  }
}

async function safeGoto(page, url, retries = 3) {
  for (let i = 0; i < retries; i += 1) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      return true;
    } catch (_) {
      if (i === retries - 1) return false;
      await delay(900 + i * 250);
    }
  }
  return false;
}

async function maybeBypassNgrokInterstitial(page) {
  const btn = await page.$('button');
  if (!btn) return;
  const text = await page.evaluate((el) => (el.textContent || '').trim(), btn);
  if (text.includes('Visit Site')) {
    await btn.click();
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 20000 }).catch(() => {});
  }
}

async function setupMouseTracking(page) {
  await page.evaluateOnNewDocument(() => {
    window.mouseX = 0;
    window.mouseY = 0;
    window.addEventListener('mousemove', (e) => {
      window.mouseX = e.clientX;
      window.mouseY = e.clientY;
    });
  });
}

async function getMousePos(page) {
  return page.evaluate(() => ({ x: Number(window.mouseX || 0), y: Number(window.mouseY || 0) }));
}

async function getRandomXY(box, padding = 4) {
  const pad = Math.max(2, Math.min(padding, Math.floor(Math.min(box.width, box.height) / 3)));
  return {
    x: box.x + pad + Math.random() * Math.max(1, box.width - pad * 2),
    y: box.y + pad + Math.random() * Math.max(1, box.height - pad * 2),
  };
}

async function moveHybrid(page, target, profile) {
  const current = await getMousePos(page);
  const steps = randomInt(profile.moveStepsMin, profile.moveStepsMax);
  const jx = randomInt(-5, 5);
  const jy = randomInt(-5, 5);
  const mid = {
    x: (current.x + target.x) / 2 + jx,
    y: (current.y + target.y) / 2 + jy,
  };

  if (chance(profile.overshootChance)) {
    const overshootPx = randomInt(profile.overshootPxMin, profile.overshootPxMax);
    const dx = target.x - current.x;
    const dy = target.y - current.y;
    const len = Math.max(1, Math.hypot(dx, dy));
    const over = {
      x: target.x + (dx / len) * overshootPx + randomInt(-3, 3),
      y: target.y + (dy / len) * overshootPx + randomInt(-3, 3),
    };
    await page.mouse.move(mid.x, mid.y, { steps: Math.max(1, Math.floor(steps * 0.4)) });
    await page.mouse.move(over.x, over.y, { steps: Math.max(1, Math.floor(steps * 0.35)) });
    await page.mouse.move(target.x, target.y, { steps: Math.max(1, Math.floor(steps * 0.25)) });
    return;
  }

  await page.mouse.move(mid.x, mid.y, { steps: Math.max(1, Math.floor(steps * 0.5)) });
  await page.mouse.move(target.x, target.y, { steps: Math.max(1, Math.ceil(steps * 0.5)) });
}

async function randomHumanWarmup(page, profile) {
  const width = randomInt(900, 1500);
  const height = randomInt(500, 900);
  for (let i = 0; i < randomInt(2, 5); i += 1) {
    await page.mouse.move(randomInt(10, width), randomInt(20, height), { steps: randomInt(8, 20) });
    if (chance(0.35)) await delay(randomInt(40, 180));
  }
  if (chance(0.3)) {
    await page.mouse.wheel({ deltaY: randomInt(60, 280) });
    await delay(randomInt(40, 140));
    await page.mouse.wheel({ deltaY: randomInt(-220, -70) });
  }
  if (chance(profile.idleChance)) {
    await delay(randomInt(profile.idleMinMs, profile.idleMaxMs));
  }
}

async function clickElement(page, handle, profile) {
  const box = await handle.boundingBox();
  if (!box) return false;
  const point = await getRandomXY(box);
  await moveHybrid(page, point, profile);
  await delay(randomInt(profile.preClickDwellMinMs, profile.preClickDwellMaxMs));
  await handle.click({ delay: randomInt(profile.clickDelayMinMs, profile.clickDelayMaxMs) });
  return true;
}

async function typeWithProfile(page, selector, value, profile) {
  const input = await page.$(selector);
  if (!input) return false;
  await input.click({ clickCount: 3 });
  for (const ch of String(value)) {
    await page.keyboard.type(ch, { delay: randomInt(profile.typingDelayMinMs, profile.typingDelayMaxMs) });
  }
  return true;
}

async function findVisibleButton(page, selectorList) {
  for (const sel of selectorList) {
    const el = await page.$(sel);
    if (!el) continue;
    const visible = await page.evaluate((node) => {
      const style = window.getComputedStyle(node);
      return style.display !== 'none' && style.visibility !== 'hidden' && !node.disabled;
    }, el).catch(() => false);
    if (visible) return el;
  }
  return null;
}

async function login(page, profile) {
  const ok = page.url().includes('login.html') || (await safeGoto(page, `${BASE_URL}login.html`, 3));
  if (!ok) throw new Error('failed to open login page');

  await typeWithProfile(page, '#email', USER_EMAIL, profile);
  await delay(randomInt(20, 120));
  await typeWithProfile(page, '#password', USER_PASS, profile);

  const submit = await findVisibleButton(page, ['button[type="submit"]']);
  if (!submit) throw new Error('login submit button not found');
  await clickElement(page, submit, profile);
  await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 28000 }).catch(() => {});
}

async function enterPerformanceDetail(page, profile) {
  await page.goto(`${BASE_URL}index.html`, { waitUntil: 'networkidle0' });
  await randomHumanWarmup(page, profile);
  await page.waitForSelector(`.performance-card[onclick*="${TARGET_PERF_ID}"]`, { timeout: 25000 });
  const card = await page.$(`.performance-card[onclick*="${TARGET_PERF_ID}"]`);
  if (!card) throw new Error('target performance card not found');

  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 28000 }),
    clickElement(page, card, profile),
  ]);

  if (!page.url().includes('performance_detail.html')) {
    const forced = await safeGoto(page, `${BASE_URL}performance_detail.html?id=${TARGET_PERF_ID}`, 2);
    if (!forced) throw new Error('failed to enter performance detail page');
  }
}

async function performDetailEntry(page, profile) {
  let clickedDate = false;
  let clickedTime = false;
  let clickedStart = false;
  let burstChecks = profile.burstWindowChecks;
  const deadline = Date.now() + DETAIL_DEADLINE_MS;

  while (!clickedStart && Date.now() < deadline) {
    const usingBurst = clickedTime && !clickedStart && burstChecks > 0;
    if (usingBurst) {
      burstChecks -= 1;
      await delay(randomInt(profile.burstPollMinMs, profile.burstPollMaxMs));
    } else {
      await delay(randomInt(profile.pollMinMs, profile.pollMaxMs));
    }

    if (chance(profile.idleChance * 0.6)) {
      await delay(randomInt(Math.floor(profile.idleMinMs * 0.5), Math.floor(profile.idleMaxMs * 0.8)));
    }

    try {
      if (!clickedDate) {
        const dateBtn = await page.$('.date-btn:not([disabled])');
        if (dateBtn) {
          await clickElement(page, dateBtn, profile);
          clickedDate = true;
          continue;
        }
      }

      if (clickedDate && !clickedTime) {
        const timeBtn = await page.$('.time-btn:not([disabled])');
        if (timeBtn) {
          await clickElement(page, timeBtn, profile);
          clickedTime = true;
          continue;
        }
      }

      if (clickedTime && !clickedStart) {
        const startBtn = await page.$('#start-booking-btn');
        if (startBtn) {
          const visible = await page.evaluate((el) => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden' && !el.disabled;
          }, startBtn).catch(() => false);
          if (visible) {
            await clickElement(page, startBtn, profile);
            clickedStart = true;
          }
        }
      }
    } catch (_) {
      // keep polling
    }
  }

  if (!clickedStart) {
    throw new Error('failed to click start booking before deadline');
  }
}

async function waitUntilSeatPage(page, profile) {
  const started = Date.now();
  while (Date.now() - started < SEAT_PAGE_TIMEOUT_MS) {
    try {
      const url = page.url();
      if (url.includes('seat_select.html')) {
        const grid = await page.$('#seat-grid');
        if (grid) return true;
      } else if (url.includes('queue.html')) {
        if (chance(0.45)) {
          await page.mouse.move(randomInt(80, 900), randomInt(120, 600), { steps: randomInt(4, 11) });
        }
      }
    } catch (_) {
      // ignore transient navigation errors
    }

    const delayMs = chance(0.35)
      ? randomInt(profile.burstPollMinMs, profile.burstPollMaxMs)
      : randomInt(140, 360);
    await delay(delayMs);
  }
  return false;
}

async function solveCaptchaHybrid(page, profile) {
  await page.waitForSelector('#captcha-overlay', { visible: true, timeout: 5000 }).catch(() => {});
  const overlay = await page.$('#captcha-overlay:not(.captcha-hidden)');
  if (!overlay) return true;

  const text = await page
    .evaluate(() => window.currentCaptcha || '')
    .catch(() => '');
  if (!text) return false;

  const input = await page.$('#captcha-input');
  const submit = await page.$('#captcha-submit-btn');
  if (!input || !submit) return false;

  await clickElement(page, input, profile);
  for (const ch of String(text)) {
    const fast = chance(profile.captchaFastBurstChance);
    const d = fast
      ? randomInt(profile.captchaFastDelayMinMs, profile.captchaFastDelayMaxMs)
      : randomInt(profile.typingDelayMinMs, profile.typingDelayMaxMs);
    await page.keyboard.type(ch, { delay: d });
    if (chance(profile.captchaBackspaceChance)) {
      await page.keyboard.press('Backspace');
      await page.keyboard.type(ch, { delay: randomInt(12, 40) });
    }
  }
  await clickElement(page, submit, profile);
  await delay(randomInt(220, 700));
  return true;
}

async function pickSeat(page, profile, attempt) {
  const seats = await page.$$('.seat.available:not(.selected)');
  if (!seats.length) return null;

  const pool = Math.min(profile.seatPoolMax, seats.length);
  if (pool <= 0) return seats[0];

  if (chance(profile.deterministicSeatBias)) {
    const idx = Math.max(0, Math.min(pool - 1, (attempt * 3) % pool));
    return seats[idx];
  }

  return seats[randomInt(0, pool - 1)];
}

async function selectSeats(page, profile) {
  const targetSeats = randomInt(profile.targetSeatMin, profile.targetSeatMax);
  let selected = 0;
  let attempts = 0;

  while (selected < targetSeats && attempts < profile.maxSeatAttempts) {
    try {
      const overlay = await page.$('#alert-overlay');
      if (overlay) {
        const active = await page.evaluate((el) => el.classList.contains('active'), overlay).catch(() => false);
        if (active) {
          const confirm = await page.$('#alert-confirm-btn');
          if (confirm) await confirm.click();
          await delay(randomInt(120, 300));
        }
      }

      const seat = await pickSeat(page, profile, attempts);
      if (!seat) {
        attempts += 1;
        await delay(randomInt(80, 180));
        continue;
      }

      await clickElement(page, seat, profile);
      await delay(randomInt(profile.seatConfirmMinMs, profile.seatConfirmMaxMs));

      const isSelected = await page.evaluate((el) => el.classList.contains('selected'), seat).catch(() => false);
      if (isSelected) {
        selected += 1;
      } else {
        attempts += 1;
        const backoff = Math.min(profile.backoffCapMs, profile.backoffBaseMs + attempts * profile.backoffStepMs);
        await delay(backoff);
      }
    } catch (_) {
      attempts += 1;
    }
  }

  return selected > 0;
}

async function goCheckout(page, profile) {
  const next = await findVisibleButton(page, ['#next-btn']);
  if (!next) return false;
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 14000 }).catch(() => {}),
    clickElement(page, next, profile),
  ]);

  const discount = await findVisibleButton(page, ['button[onclick*="confirmDiscount"]']);
  if (!discount) return false;
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 14000 }).catch(() => {}),
    clickElement(page, discount, profile),
  ]);

  const order = await findVisibleButton(page, ['button[onclick*="confirmOrderInfo"]']);
  if (!order) return false;
  await page.evaluate((el) => el.scrollIntoView({ behavior: 'instant', block: 'center' }), order).catch(() => {});
  await delay(randomInt(140, 360));
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 14000 }).catch(() => {}),
    clickElement(page, order, profile),
  ]);

  const pay = await findVisibleButton(page, ['button[onclick*="processPayment"]']);
  if (!pay) return false;
  await clickElement(page, pay, profile);
  await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 22000 }).catch(() => {});
  return page.url().includes('booking_complete.html');
}

async function runIteration(iteration) {
  const profile = pickProfile();
  console.log(`\n[SIMUL-MACRO] Iteration ${iteration}/${LOOP_COUNT} | profile=${profile.name}`);

  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: null,
    args: ['--start-maximized'],
  });

  try {
    const pages = await browser.pages();
    const page = pages[0];
    await setupMouseTracking(page);

    page.on('console', (msg) => {
      const text = msg.text();
      if (!text.includes('HMR') && !text.includes('Hot')) {
        console.log(`[Browser ${msg.type()}] ${text}`);
      }
    });

    await page.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 30000 });
    await randomHumanWarmup(page, profile);
    await page.evaluate((botType) => {
      sessionStorage.setItem('bot_type', botType);
    }, BOT_TYPE);

    await maybeBypassNgrokInterstitial(page);
    await login(page, profile);
    await enterPerformanceDetail(page, profile);

    await page.evaluate((botType) => {
      if (typeof updateMetadata === 'function') {
        updateMetadata({ bot_type: botType });
      }
    }, BOT_TYPE);

    await performDetailEntry(page, profile);

    const seatReady = await waitUntilSeatPage(page, profile);
    if (!seatReady) throw new Error('seat page timeout');

    await solveCaptchaHybrid(page, profile);
    const seatOk = await selectSeats(page, profile);
    if (!seatOk) {
      console.log(`[SIMUL-MACRO] Iteration ${iteration}: no seat selected`);
      return;
    }

    const completed = await goCheckout(page, profile);
    if (completed) {
      console.log(`[SIMUL-MACRO] Iteration ${iteration}: booking complete`);
      await delay(4000);
    } else {
      console.log(`[SIMUL-MACRO] Iteration ${iteration}: checkout incomplete`);
    }
  } catch (e) {
    console.error(`[SIMUL-MACRO] Iteration ${iteration} error: ${e.message}`);
  } finally {
    await delay(1600);
    await safeCloseBrowser(browser);
  }

  await delay(randomInt(profile.sessionGapMinMs, profile.sessionGapMaxMs));
}

(async () => {
  for (let i = 1; i <= LOOP_COUNT; i += 1) {
    try {
      await runIteration(i);
    } catch (e) {
      console.error(`[SIMUL-MACRO] Iteration ${i} fatal error: ${e.message}`);
    }
  }
  console.log('[SIMUL-MACRO] all iterations finished');
})();

