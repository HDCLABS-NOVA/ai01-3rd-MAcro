const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer");

const BASE_URL = (process.env.BASE_URL || "http://localhost:8000/").replace(/\/+$/, "") + "/";
const LOOP_COUNT = Number(process.env.LOOP_COUNT || 30);
const HEADLESS_MODE = process.env.HEADLESS_MODE
  ? String(process.env.HEADLESS_MODE).toLowerCase() === "true"
  : false;

const USER_EMAIL = process.env.USER_EMAIL || "macro@email.com";
const USER_PASS = process.env.USER_PASS || "1";
const BOT_TYPE = process.env.BOT_TYPE || "realtime_block_bot";

// The stronger these values are, the easier it is to push soft rule/model score up.
const BURST_START = Number(process.env.BURST_START || 40);
const BURST_STEP = Number(process.env.BURST_STEP || 35);
const MAX_POST_TRIES = Number(process.env.MAX_POST_TRIES || 3);
const INTER_TRY_DELAY_MS = Number(process.env.INTER_TRY_DELAY_MS || 350);

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const randomInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const randomId = (prefix = "", len = 6) => prefix + Math.random().toString(36).slice(2, 2 + len);

function resolveLocalPath(filePath) {
  const raw = String(filePath || "").trim();
  if (!raw) return "";
  if (path.isAbsolute(raw)) return raw;
  return path.resolve(__dirname, "..", raw);
}

function loadJsonSafe(filePath) {
  try {
    if (!filePath || !fs.existsSync(filePath)) return null;
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
}

function printLLMRealtimeReportFromResult(result) {
  const reportPathFromRisk = String(result?.body?.risk?.realtime_report_path || "").trim();
  if (!reportPathFromRisk) {
    console.log("[REALTIME-BLOCK][REPORT] no realtime_report_path in response risk.");
    return;
  }

  const reportPath = resolveLocalPath(reportPathFromRisk);
  const report = loadJsonSafe(reportPath);
  if (!report) {
    console.log(`[REALTIME-BLOCK][REPORT] failed to read report file: ${reportPath}`);
    return;
  }

  const llmReportPathFromReport = String(report.llm_report_path || "").trim();
  const llmReportPath = resolveLocalPath(llmReportPathFromReport);
  const llmReport = loadJsonSafe(llmReportPath);

  // Prefer dedicated llm report file. Fallback to base report payload.
  const llmUsed = !!(llmReport?.llm_analysis?.used ?? report?.llm_analysis?.used);
  const summary =
    String(llmReport?.llm_analysis?.summary_ko || report?.llm_analysis?.summary_ko || report?.user_message || "").trim();
  const reasons =
    llmReport?.llm_analysis?.top_reasons ||
    report?.llm_analysis?.top_reasons ||
    report?.ui_fields?.suspicion_reasons ||
    [];
  const markdown = String(llmReport?.markdown_report || report?.markdown_report || "").trim();

  console.log(`[REALTIME-BLOCK][REPORT] report_path=${reportPath}`);
  if (llmReportPath) {
    console.log(`[REALTIME-BLOCK][REPORT] llm_report_path=${llmReportPath}`);
  }
  console.log(`[REALTIME-BLOCK][REPORT] llm_used=${llmUsed}`);
  if (!llmUsed) {
    console.log(
      "[REALTIME-BLOCK][REPORT] LLM report was not generated. Check OPENAI_API_KEY / LLM_REPORT_ENABLED on server."
    );
    return;
  }
  if (summary) {
    console.log(`[REALTIME-BLOCK][REPORT] summary=${summary}`);
  }
  if (Array.isArray(reasons) && reasons.length) {
    console.log(`[REALTIME-BLOCK][REPORT] top_reasons=${reasons.slice(0, 3).join(" | ")}`);
  }
  if (markdown) {
    console.log("[REALTIME-BLOCK][REPORT] markdown_begin");
    console.log(markdown);
    console.log("[REALTIME-BLOCK][REPORT] markdown_end");
  }
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
      await delay(200 * (i + 1));
    }
  }
  try {
    const proc = browser.process();
    if (proc && !proc.killed) proc.kill("SIGKILL");
  } catch (_) {
    // ignore hard-close errors
  }
}

function buildClicks({
  count,
  x0 = 200,
  y0 = 200,
  dtMin = 1,
  dtMax = 3,
  duration = 0,
  trusted = false,
}) {
  const clicks = [];
  let t = 0;
  for (let i = 0; i < count; i += 1) {
    t += randomInt(dtMin, dtMax);
    const x = x0 + i;
    const y = y0;
    clicks.push({
      x,
      y,
      nx: Number((x / 1280).toFixed(4)),
      ny: Number((y / 720).toFixed(4)),
      timestamp: t,
      is_trusted: trusted,
      duration,
      button: 0,
      target: `seat_${i + 1}`,
    });
  }
  return clicks;
}

function buildTrajectory({
  points,
  x0 = 100,
  y0 = 100,
  dx = 12,
  dy = 0,
  dt = 2,
}) {
  const path = [];
  let t = 0;
  for (let i = 0; i < points; i += 1) {
    t += dt;
    path.push([x0 + i * dx, y0 + i * dy, t, Number(((x0 + i * dx) / 1280).toFixed(4)), Number(((y0 + i * dy) / 720).toFixed(4))]);
  }
  return path;
}

function buildSyntheticBrowserLog(iteration, attempt) {
  const now = new Date();
  const ymd = now.toISOString().slice(0, 10).replace(/-/g, "");
  const flowId = `flow_${ymd}_${randomId("", 6)}`;
  const sessionId = `sess_${randomId("", 7)}`;
  const perfId = process.env.TARGET_PERF_ID || "perf001";

  const perfClicks = buildClicks({ count: 12 + attempt * 2, x0: 140, y0: 210, trusted: false });
  const seatClicks = buildClicks({ count: 18 + attempt * 6, x0: 320, y0: 280, trusted: false });

  const perfTrajectory = buildTrajectory({ points: 5 + attempt, x0: 120, y0: 210, dx: 18, dy: 0, dt: 2 });
  const seatTrajectory = buildTrajectory({ points: 8 + attempt, x0: 260, y0: 300, dx: 20, dy: 0, dt: 2 });

  return {
    metadata: {
      flow_id: flowId,
      session_id: sessionId,
      bot_type: BOT_TYPE,
      user_email: USER_EMAIL,
      performance_id: perfId,
      performance_title: "Realtime Block Test",
      created_at: now.toISOString(),
      flow_start_time: now.toISOString(),
      flow_end_time: now.toISOString(),
      total_duration_ms: 1200 + attempt * 120,
      is_completed: true,
      completion_status: "success",
      booking_id: `M${randomInt(10000000, 99999999)}`,
      booking_flow_started: true,
      browser_info: {
        userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        platform: "Win32",
        language: "ko-KR",
        webdriver: true,
        hardwareConcurrency: 64,
        screen: { w: 1280, h: 720, ratio: 1 },
      },
    },
    stages: {
      perf: {
        entry_time: now.toISOString(),
        exit_time: now.toISOString(),
        duration_ms: 180 + attempt * 10,
        mouse_trajectory: perfTrajectory,
        clicks: perfClicks,
        actions: ["date_select", "time_select", "start_booking_click"],
      },
      queue: {
        entry_time: now.toISOString(),
        exit_time: now.toISOString(),
        duration_ms: 90,
        mouse_trajectory: [],
        clicks: [],
        initial_position: 8500,
        final_position: 0,
        total_queue: 8500,
        position_updates: [{ t: 1, pos: 8500 }, { t: 2, pos: 0 }],
      },
      captcha: {
        entry_time: now.toISOString(),
        exit_time: now.toISOString(),
        duration_ms: 60,
        mouse_trajectory: [[400, 330, 3]],
        clicks: buildClicks({ count: 1, x0: 420, y0: 340, trusted: false }),
        status: "verified",
      },
      seat: {
        entry_time: now.toISOString(),
        exit_time: now.toISOString(),
        duration_ms: 220 + attempt * 15,
        mouse_trajectory: seatTrajectory,
        clicks: seatClicks,
        selected_seats: ["A-1"],
        seat_details: [{ id: "A-1", grade: "VIP", price: 120000 }],
      },
    },
  };
}

async function maybeBypassNgrokInterstitial(page) {
  const btn = await page.$("button");
  if (!btn) return;
  const text = await page.evaluate((el) => (el.textContent || "").trim(), btn);
  if (text.includes("Visit Site")) {
    await btn.click();
    await page.waitForNavigation({ waitUntil: "networkidle0", timeout: 20000 }).catch(() => {});
  }
}

async function tryLogin(page) {
  try {
    await page.goto(`${BASE_URL}login.html`, { waitUntil: "networkidle0", timeout: 30000 });
    await page.waitForSelector("#email", { timeout: 5000 });
    await page.type("#email", USER_EMAIL, { delay: randomInt(2, 10) });
    await page.type("#password", USER_PASS, { delay: randomInt(2, 10) });
    const submit = await page.$('button[type="submit"]');
    if (submit) {
      await submit.click();
      await page.waitForNavigation({ waitUntil: "networkidle0", timeout: 20000 }).catch(() => {});
    }
    return true;
  } catch (_) {
    return false;
  }
}

async function sendRealtimeBlockProbe(page, payload, burstCount) {
  return page.evaluate(
    async ({ payloadInPage, burstCountInPage, botTypeInPage }) => {
      try {
        sessionStorage.setItem("bot_type", botTypeInPage);
      } catch (_) {
        // ignore storage errors
      }

      // Raise requests_last_1s and requests_last_10s just before /api/logs.
      const burstPromises = [];
      for (let i = 0; i < burstCountInPage; i += 1) {
        const u = `/api/realtime_probe_${i}?ts=${Date.now()}_${i}`;
        burstPromises.push(fetch(u, { method: "GET", cache: "no-store" }).catch(() => null));
      }
      await Promise.allSettled(burstPromises);

      const res = await fetch("/api/logs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payloadInPage),
      });
      const text = await res.text();
      let body = null;
      try {
        body = JSON.parse(text);
      } catch (_) {
        body = { raw: text.slice(0, 500) };
      }
      return { status: res.status, body };
    },
    { payloadInPage: payload, burstCountInPage: burstCount, botTypeInPage: BOT_TYPE }
  );
}

async function runIteration(iteration) {
  console.log(`\n[REALTIME-BLOCK] iteration ${iteration}/${LOOP_COUNT}`);
  const browser = await puppeteer.launch({
    headless: HEADLESS_MODE,
    defaultViewport: { width: 1280, height: 720 },
    args: ["--start-maximized"],
  });

  try {
    const [page] = await browser.pages();
    page.on("console", (msg) => {
      const text = msg.text();
      if (!text.includes("HMR") && !text.includes("hot")) {
        console.log(`[Browser ${msg.type()}] ${text}`);
      }
    });

    await page.goto(BASE_URL, { waitUntil: "networkidle0", timeout: 30000 });
    await maybeBypassNgrokInterstitial(page);
    await tryLogin(page);
    await page.goto(`${BASE_URL}index.html`, { waitUntil: "networkidle0", timeout: 30000 }).catch(() => {});

    let finalResult = null;
    let blocked = false;

    for (let attempt = 1; attempt <= MAX_POST_TRIES; attempt += 1) {
      const burstCount = BURST_START + BURST_STEP * (attempt - 1);
      const payload = buildSyntheticBrowserLog(iteration, attempt);
      const result = await sendRealtimeBlockProbe(page, payload, burstCount);
      finalResult = result;

      const decision = result?.body?.decision || result?.body?.risk?.decision || "";
      const message = result?.body?.message || "";

      console.log(
        `[REALTIME-BLOCK] try=${attempt} burst=${burstCount} status=${result.status} decision=${decision} message=${message}`
      );

      if (result.status === 403 || decision === "block") {
        blocked = true;
        break;
      }
      await delay(INTER_TRY_DELAY_MS);
    }

    if (!blocked) {
      const maybeChallenge = finalResult?.status === 202;
      const blockRecommended = !!finalResult?.body?.risk?.block_recommended;
      if (maybeChallenge && blockRecommended) {
        console.log(
          "[REALTIME-BLOCK] got challenge; model-only block may be downgraded by server policy (check RISK_BLOCK_AUTOMATION)."
        );
      } else {
        console.log("[REALTIME-BLOCK] no block detected on this iteration.");
      }
    } else {
      console.log("[REALTIME-BLOCK] realtime block response confirmed.");
      printLLMRealtimeReportFromResult(finalResult);
    }
  } catch (e) {
    console.error(`[REALTIME-BLOCK] iteration ${iteration} error:`, e.message);
  } finally {
    await delay(1200);
    await safeCloseBrowser(browser);
  }
}

(async () => {
  for (let i = 1; i <= LOOP_COUNT; i += 1) {
    try {
      await runIteration(i);
    } catch (e) {
      console.error(`[REALTIME-BLOCK] fatal on iteration ${i}:`, e.message);
    }
    await delay(randomInt(700, 1800));
  }
  console.log("[REALTIME-BLOCK] all iterations finished");
})();
