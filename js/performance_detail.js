// performance_detail.js - 怨듭뿰 ?곸꽭 ?섏씠吏

let currentPerformance = null;
let selectedDate = "";
let selectedTime = "";
const DETAIL_OPEN_DELAY_MS = 5000;
const REALTIME_BLOCK_POPUP_MESSAGE = "비정상적인 접근으로 일시적으로 서비스 접속이 제한되었습니다.";

let cardClickTimestamp = null;
let dateSelectTimestamp = null;
let timeSelectTimestamp = null;

function getLogMetadata() {
  try {
    const raw = sessionStorage.getItem("bookingLog");
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed?.metadata || {};
  } catch (e) {
    return {};
  }
}

async function issueBookingStartToken(performanceId) {
  const meta = getLogMetadata();
  const flowId = String(meta.flow_id || "").trim();
  const sessionId = String(meta.session_id || "").trim();

  if (!flowId || !sessionId) {
    return { ok: false, message: "flow_id/session_id媛 ?놁뼱 ?湲곗뿴 ?낆옣 ?좏겙??諛쒓툒?????놁뒿?덈떎." };
  }

  const payload = {
    performance_id: performanceId,
    flow_id: flowId,
    session_id: sessionId,
    user_email: String(meta.user_email || ""),
    bot_type: String(meta.bot_type || ""),
  };

  try {
    const res = await fetch("/api/booking/start-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const body = await res.json().catch(() => ({}));
    const decision = String(body?.decision || body?.risk?.decision || "").toLowerCase();
    if (res.status === 403 && decision === "block") {
      alert(REALTIME_BLOCK_POPUP_MESSAGE);
      return { ok: false, message: REALTIME_BLOCK_POPUP_MESSAGE };
    }
    if (!res.ok || !body?.success) {
      return { ok: false, message: body?.detail || body?.message || "?좏겙 諛쒓툒 ?ㅽ뙣" };
    }

    const token = String(body.start_token || "");
    if (!token) {
      return { ok: false, message: "?좏겙 媛믪씠 鍮꾩뼱 ?덉뒿?덈떎." };
    }

    sessionStorage.setItem("booking_start_token", token);
    sessionStorage.setItem("booking_start_token_expires_epoch_ms", String(body.expires_epoch_ms || 0));
    return { ok: true, token };
  } catch (e) {
    return { ok: false, message: e?.message || "?좏겙 諛쒓툒 ?붿껌 ?ㅽ뙣" };
  }
}

async function loadPerformance() {
  const perfId = getQueryParam("id");
  if (!perfId) {
    navigateTo("index.html");
    return;
  }

  try {
    const response = await fetch(`/api/performances/${encodeURIComponent(perfId)}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("怨듭뿰 ?곗씠???붿껌 ?ㅽ뙣");
    }

    const payload = await response.json();
    currentPerformance = payload?.performance || null;
    if (!currentPerformance) {
      throw new Error("怨듭뿰??李얠쓣 ???놁뒿?덈떎.");
    }

    // ?붽뎄?ы빆: ?곸꽭 ?섏씠吏 吏꾩엯 ?쒕쭏????긽 5珥????ㅽ뵂?쇰줈 ?ъ꽕??
    currentPerformance.open_time = new Date(Date.now() + DETAIL_OPEN_DELAY_MS).toISOString();
    currentPerformance.status = "upcoming";

    displayPerformance();

    cardClickTimestamp = getCollectTimestamp();
    await initLogCollector(currentPerformance.id, currentPerformance.title);
    recordStageEntry("perf");
  } catch (error) {
    console.error(error);
    showAlert("怨듭뿰 ?뺣낫瑜?遺덈윭?ㅻ뒗 ???ㅽ뙣?덉뒿?덈떎.", "error");
    setTimeout(() => navigateTo("index.html"), 1500);
  }
}

function displayPerformance() {
  const detailDiv = document.getElementById("perf-detail");
  if (!detailDiv || !currentPerformance) return;

  const openTime = currentPerformance.open_time ? new Date(currentPerformance.open_time) : null;
  const now = new Date();
  const isOpen = !openTime || openTime <= now;

  const openTimeAlert = !isOpen && openTime
    ? `
      <div class="alert alert-warning" style="margin-bottom: var(--spacing-lg);">
        <h3 style="margin-bottom: var(--spacing-sm);">?덈ℓ ?ㅽ뵂 ?덉젙</h3>
        <p style="margin-bottom: var(--spacing-sm);">
          <strong>?ㅽ뵂 ?쒓컙:</strong> ${formatOpenTimeDisplay(openTime)}
        </p>
        <div class="countdown-timer-detail" id="countdown-detail" data-open-time="${openTime.toISOString()}"></div>
        <p style="margin-top: var(--spacing-sm); font-size: 14px; opacity: 0.9;">
          ?ㅽ뵂 ?쒓컙 ?댄썑 ?좎쭨? ?뚯감瑜??좏깮?????덉뒿?덈떎.
        </p>
      </div>
    `
    : "";

  detailDiv.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr 1.5fr; gap: var(--spacing-xl); margin-bottom: var(--spacing-xl);">
      <div class="card">
        <div style="width: 100%; height: 400px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: var(--border-radius); display: flex; align-items: center; justify-content: center; font-size: 72px;">
          ${getCategoryIcon(currentPerformance.category)}
        </div>
      </div>

      <div>
        <h1 class="page-title">${currentPerformance.title}</h1>
        <p class="page-subtitle">${currentPerformance.description || ""}</p>

        ${openTimeAlert}

        <div class="card mt-lg">
          <div style="margin-bottom: var(--spacing-md);">
            <strong>?μ냼:</strong> ${currentPerformance.venue || "-"}
          </div>
          <div style="margin-bottom: var(--spacing-md);">
            <strong>移댄뀒怨좊━:</strong> ${getCategoryName(currentPerformance.category)}
          </div>
          <div>
            <strong>媛寃?</strong> ${getPriceRangeText(currentPerformance)}
          </div>
        </div>

        <div class="card mt-lg">
          <h3 style="margin-bottom: var(--spacing-md);">?좎쭨 ?좏깮</h3>
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--spacing-sm);" id="date-selection">
            ${(currentPerformance.dates || []).map((date) => `
              <button class="btn btn-outline date-btn" data-date="${date}" ${!isOpen ? "disabled" : ""}>
                ${formatDateKorean(date)}<br>
                <small>(${getDayOfWeek(date)})</small>
              </button>
            `).join("")}
          </div>
        </div>

        <div class="card mt-lg" id="time-selection-section" style="display: none;">
          <h3 style="margin-bottom: var(--spacing-md);">?뚯감 ?좏깮</h3>
          <div style="display: flex; gap: var(--spacing-sm); flex-wrap: wrap;" id="time-selection">
            ${(currentPerformance.times || []).map((time) => `
              <button class="btn btn-outline time-btn" data-time="${time}" ${!isOpen ? "disabled" : ""}>
                ${time}
              </button>
            `).join("")}
          </div>
        </div>

        ${getBookingButton(isOpen, openTime)}
      </div>
    </div>
  `;

  if (isOpen) {
    attachEventListeners();
  } else {
    startDetailCountdown();
  }
}

function getPriceRangeText(performance) {
  const grades = performance?.grades || [];
  if (!grades.length) return "-";

  const sorted = [...grades].sort((a, b) => Number(a.price || 0) - Number(b.price || 0));
  const min = sorted[0]?.price ?? 0;
  const max = sorted[sorted.length - 1]?.price ?? 0;
  return `${formatPrice(min)} ~ ${formatPrice(max)}`;
}

function getBookingButton(isOpen, openTime) {
  if (!isOpen && openTime) {
    return `
      <button id="start-booking-btn" class="btn btn-primary btn-lg btn-block mt-xl" disabled style="cursor: not-allowed; opacity: 0.7;">
        ?ㅽ뵂 ?湲?以?(${formatOpenTimeDisplay(openTime)})
      </button>
    `;
  }

  return `
    <button id="start-booking-btn" class="btn btn-primary btn-lg btn-block mt-xl" style="display: none;">
      ?덈ℓ ?쒖옉
    </button>
  `;
}

function attachEventListeners() {
  document.querySelectorAll(".date-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectDate(btn.dataset.date, btn);
    });
  });

  document.querySelectorAll(".time-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectTime(btn.dataset.time, btn);
    });
  });

  const bookingBtn = document.getElementById("start-booking-btn");
  if (bookingBtn) {
    bookingBtn.addEventListener("click", startBooking);
  }
}

function selectDate(date, btnElement) {
  if (!isCurrentlyOpen()) {
    showAlert("?ㅽ뵂 ?쒓컙 ?댄썑?먮쭔 ?좏깮?????덉뒿?덈떎.", "warning");
    return;
  }

  selectedDate = date;

  document.querySelectorAll(".date-btn").forEach((btn) => {
    btn.classList.remove("btn-primary");
    btn.classList.add("btn-outline");
  });

  const targetBtn = btnElement || document.querySelector(`.date-btn[data-date="${date}"]`);
  if (targetBtn) {
    targetBtn.classList.remove("btn-outline");
    targetBtn.classList.add("btn-primary");
  }

  const timeSection = document.getElementById("time-selection-section");
  if (timeSection) {
    timeSection.style.display = "block";
  }

  dateSelectTimestamp = getCollectTimestamp();
}

function selectTime(time, btnElement) {
  if (!isCurrentlyOpen()) {
    showAlert("?ㅽ뵂 ?쒓컙 ?댄썑?먮쭔 ?좏깮?????덉뒿?덈떎.", "warning");
    return;
  }

  selectedTime = time;

  document.querySelectorAll(".time-btn").forEach((btn) => {
    btn.classList.remove("btn-primary");
    btn.classList.add("btn-outline");
  });

  const targetBtn = btnElement || document.querySelector(`.time-btn[data-time="${time}"]`);
  if (targetBtn) {
    targetBtn.classList.remove("btn-outline");
    targetBtn.classList.add("btn-primary");
  }

  const bookingBtn = document.getElementById("start-booking-btn");
  if (bookingBtn) {
    bookingBtn.style.display = "block";
  }

  timeSelectTimestamp = getCollectTimestamp();
}

async function startBooking() {
  if (!requireLogin()) return;

  if (!isCurrentlyOpen()) {
    showAlert("?ㅽ뵂 ?쒓컙 ?댄썑?먮쭔 ?덈ℓ?????덉뒿?덈떎.", "warning");
    return;
  }

  if (!selectedDate || !selectedTime) {
    showAlert("?좎쭨? ?뚯감瑜?癒쇱? ?좏깮??二쇱꽭??", "warning");
    return;
  }

  startBookingFlow(currentPerformance.id, currentPerformance.title);

  initFlow(currentPerformance);
  updateFlowData({
    selectedDate,
    selectedTime,
  });

  updateMetadata({
    selected_date: selectedDate,
    selected_time: selectedTime,
  });

  const tokenResult = await issueBookingStartToken(currentPerformance.id);
  if (!tokenResult.ok) {
    showAlert(tokenResult.message || "?湲곗뿴 ?좏겙 諛쒓툒???ㅽ뙣?덉뒿?덈떎.", "error");
    return;
  }

  const bookingStartTimestamp = getCollectTimestamp();

  recordStageExit("perf", {
    card_clicks: [
      {
        performance_id: currentPerformance.id,
        performance_title: currentPerformance.title,
        timestamp: cardClickTimestamp || bookingStartTimestamp,
      },
    ],
    date_selections: [
      {
        date: selectedDate,
        timestamp: dateSelectTimestamp || bookingStartTimestamp,
      },
    ],
    time_selections: [
      {
        time: selectedTime,
        timestamp: timeSelectTimestamp || bookingStartTimestamp,
      },
    ],
    actions: [
      {
        action: "card_click",
        target: currentPerformance.id,
        timestamp: cardClickTimestamp || bookingStartTimestamp,
      },
      {
        action: "date_select",
        target: selectedDate,
        timestamp: dateSelectTimestamp || bookingStartTimestamp,
      },
      {
        action: "time_select",
        target: selectedTime,
        timestamp: timeSelectTimestamp || bookingStartTimestamp,
      },
      {
        action: "booking_start",
        target: currentPerformance.id,
        date: selectedDate,
        time: selectedTime,
        timestamp: bookingStartTimestamp,
      },
    ],
  });

  navigateTo("queue.html");
}

function getCategoryIcon(category) {
  const icons = {
    concert: "C",
    musical: "M",
    sports: "S",
    exhibition: "E",
  };
  return icons[category] || "P";
}

function getCategoryName(category) {
  const names = {
    concert: "콘서트",
    musical: "뮤지컬",
    sports: "스포츠",
    exhibition: "전시",
  };
  return names[category] || "공연";
}

function isCurrentlyOpen() {
  if (!currentPerformance || !currentPerformance.open_time) return true;
  const openTime = new Date(currentPerformance.open_time);
  return new Date() >= openTime;
}

function formatOpenTimeDisplay(date) {
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const ampm = hours >= 12 ? "?ㅽ썑" : "?ㅼ쟾";
  const displayHours = hours > 12 ? hours - 12 : (hours === 0 ? 12 : hours);
  const dayOfWeek = getDayOfWeek(`${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
  return `${year}.${month}.${day} (${dayOfWeek}) ${ampm} ${displayHours}:${minutes}`;
}

function startDetailCountdown() {
  const countdownEl = document.getElementById("countdown-detail");
  if (!countdownEl) return;

  const updateCountdown = () => {
    const openTime = new Date(countdownEl.dataset.openTime);
    const now = new Date();
    const diff = openTime - now;
    const totalSec = Math.max(0, Math.ceil(diff / 1000));

    if (totalSec <= 0) {
      countdownEl.textContent = "?덈ℓ ?쒖옉!";
      countdownEl.style.background = "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)";
      clearInterval(window.detailCountdownInterval);

      setTimeout(() => {
        activateBookingPage();
      }, 600);
      return;
    }

    const days = Math.floor(totalSec / (60 * 60 * 24));
    const hours = Math.floor((totalSec % (60 * 60 * 24)) / (60 * 60));
    const minutes = Math.floor((totalSec % (60 * 60)) / 60);
    const seconds = Math.floor(totalSec % 60);

    let text = "?ㅽ뵂源뚯? ";
    if (days > 0) text += `${days}??`;
    text += `${hours}시간 ${minutes}분 ${seconds}초`;
    countdownEl.textContent = text;
  };

  updateCountdown();
  window.detailCountdownInterval = setInterval(updateCountdown, 1000);
}

function activateBookingPage() {
  const alertBox = document.querySelector(".alert-warning");
  if (alertBox) {
    alertBox.style.transition = "opacity 0.4s";
    alertBox.style.opacity = "0";
    setTimeout(() => alertBox.remove(), 400);
  }

  document.querySelectorAll(".date-btn").forEach((btn) => btn.removeAttribute("disabled"));
  document.querySelectorAll(".time-btn").forEach((btn) => btn.removeAttribute("disabled"));

  const bookingBtn = document.getElementById("start-booking-btn");
  if (bookingBtn) {
    bookingBtn.removeAttribute("disabled");
    bookingBtn.style.cursor = "pointer";
    bookingBtn.style.opacity = "1";
    bookingBtn.textContent = "?덈ℓ ?쒖옉";
    bookingBtn.style.display = "none";
  }

  attachEventListeners();
  showAlert("?덈ℓ媛 ?쒖옉?섏뿀?듬땲?? ?좎쭨? ?뚯감瑜??좏깮??二쇱꽭??", "success");
}

loadPerformance();

