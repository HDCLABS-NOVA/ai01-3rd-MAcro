// performance_detail.js - 공연 상세 페이지

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
    return { ok: false, message: "flow_id/session_id가 없어 대기열 입장 토큰을 발급할 수 없습니다." };
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
      return { ok: false, message: body?.detail || body?.message || "토큰 발급 실패" };
    }

    const token = String(body.start_token || "");
    if (!token) {
      return { ok: false, message: "토큰 값이 비어 있습니다." };
    }

    sessionStorage.setItem("booking_start_token", token);
    sessionStorage.setItem("booking_start_token_expires_epoch_ms", String(body.expires_epoch_ms || 0));
    return { ok: true, token };
  } catch (e) {
    return { ok: false, message: e?.message || "토큰 발급 요청 실패" };
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
      throw new Error("공연 데이터 요청 실패");
    }

    const payload = await response.json();
    currentPerformance = payload?.performance || null;
    if (!currentPerformance) {
      throw new Error("공연을 찾을 수 없습니다.");
    }

    // 요구사항: 상세 페이지 진입 시 항상 오픈 5초 전부터 시작
    currentPerformance.open_time = new Date(Date.now() + DETAIL_OPEN_DELAY_MS).toISOString();
    currentPerformance.status = "upcoming";

    displayPerformance();

    cardClickTimestamp = getCollectTimestamp();
    await initLogCollector(currentPerformance.id, currentPerformance.title);
    recordStageEntry("perf");
  } catch (error) {
    console.error(error);
    showAlert("공연 정보를 불러오는데 실패했습니다.", "error");
    setTimeout(() => navigateTo("index.html"), 1500);
  }
}

function displayPerformance() {
  const detailDiv = document.getElementById("perf-detail");
  if (!detailDiv || !currentPerformance) return;

  const openTime = currentPerformance.open_time ? new Date(currentPerformance.open_time) : null;
  const now = new Date();
  const isOpen = !openTime || openTime <= now;
  const imagePath = resolvePerformanceImagePath(currentPerformance);
  const imageUrl = imagePath ? encodeURI(imagePath) : "";
  const imageAlt = escapeHtmlAttr(currentPerformance.title || "공연 이미지");

  // 오픈 시간 안내 메시지
  const openTimeAlert = !isOpen ? `
        <div class="alert alert-warning" style="margin-bottom: var(--spacing-lg);">
            <h3 style="margin-bottom: var(--spacing-sm); display: flex; align-items: center; gap: 8px;">
                🔒 티켓 오픈 예정
            </h3>
            <p style="margin-bottom: var(--spacing-sm);">
                <strong>오픈 시간:</strong> ${formatOpenTimeDisplay(openTime)}
            </p>
            <div class="countdown-timer-detail" id="countdown-detail" data-open-time="${openTime.toISOString()}"></div>
            <p style="margin-top: var(--spacing-sm); font-size: 14px; opacity: 0.9;">
                오픈 시간 이후에 날짜와 시간을 선택할 수 있습니다.
            </p>
        </div>
    ` : '';

  detailDiv.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr 1.5fr; gap: var(--spacing-xl); margin-bottom: var(--spacing-xl);">
      <div class="card">
        <div style="position: relative; width: 100%; height: 400px; background: var(--primary-color); border-radius: var(--border-radius); overflow: hidden;">
          ${imageUrl ? `<img src="${imageUrl}" alt="${imageAlt}" loading="lazy" decoding="async" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.remove(); const fallback = this.parentElement.querySelector('.detail-image-fallback'); if (fallback) fallback.style.display = 'flex';">` : ""}
          <div class="detail-image-fallback" style="position: absolute; inset: 0; display: ${imageUrl ? "none" : "flex"}; align-items: center; justify-content: center; color: #fff; font-size: 72px;">
            ${getCategoryIcon(currentPerformance.category)}
          </div>
        </div>
      </div>

      <div>
        <h1 class="page-title">${currentPerformance.title}</h1>
        <p class="page-subtitle">${currentPerformance.description || ""}</p>

        ${openTimeAlert}

        <div class="card mt-lg">
          <div style="margin-bottom: var(--spacing-md);">
            <strong>장소:</strong> ${currentPerformance.venue || "-"}
          </div>
          <div style="margin-bottom: var(--spacing-md);">
            <strong>카테고리:</strong> ${getCategoryName(currentPerformance.category)}
          </div>
          <div>
            <strong>가격:</strong> ${getPriceRangeText(currentPerformance)}
          </div>
        </div>

        <div class="card mt-lg">
          <h3 style="margin-bottom: var(--spacing-md);">날짜 선택</h3>
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
          <h3 style="margin-bottom: var(--spacing-md);">회차 선택</h3>
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

function escapeHtmlAttr(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function resolvePerformanceImagePath(performance) {
  const raw = typeof performance?.image === "string" ? performance.image.trim() : "";
  if (!raw) return "";

  const normalized = raw.replace(/\\/g, "/");
  const fileName = normalized.split("/").pop();
  if (!fileName) return "";

  return `image/${fileName}`;
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
        오픈 대기 중 (${formatOpenTimeDisplay(openTime)})
      </button>
    `;
  }

  return `
    <button id="start-booking-btn" class="btn btn-primary btn-lg btn-block mt-xl" style="display: none;">
      예매 시작
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
    showAlert("오픈 시간 이후에만 선택할 수 있습니다.", "warning");
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
    showAlert("오픈 시간 이후에만 선택할 수 있습니다.", "warning");
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
    showAlert("오픈 시간 이후에만 예매할 수 있습니다.", "warning");
    return;
  }

  if (!selectedDate || !selectedTime) {
    showAlert("날짜와 회차를 먼저 선택해 주세요.", "warning");
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
    showAlert(tokenResult.message || "대기열 토큰 발급에 실패했습니다.", "error");
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
    concert: `<svg viewBox="0 0 24 24" width="72" height="72" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path><path d="M19 10v1a7 7 0 0 1-14 0v-1"></path><line x1="12" y1="19" x2="12" y2="22"></line><line x1="8" y1="22" x2="16" y2="22"></line></svg>`,
    musical: `<svg viewBox="0 0 24 24" width="72" height="72" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4.5V12"></path><path d="M18.5 7v5a6.5 6.5 0 0 1-13 0V7"></path><path d="M12 4.5l6.5 2.5a1 1 0 0 1 .5.87V12a7 7 0 0 1-14 0V7.87a1 1 0 0 1 .5-.87l6.5-2.5z"></path></svg>`,
    sports: `<svg viewBox="0 0 24 24" width="72" height="72" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M6.06 6.06l11.88 11.88"></path><path d="M17.94 6.06l-11.88 11.88"></path><circle cx="12" cy="12" r="4"></circle></svg>`,
    exhibition: `<svg viewBox="0 0 24 24" width="72" height="72" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>`
  };
  return icons[category] || `<svg viewBox="0 0 24 24" width="72" height="72" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h18l1 10H2L3 7z"></path><path d="M12 4v4"></path></svg>`;
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
  const ampm = hours >= 12 ? "오후" : "오전";
  const displayHours = hours > 12 ? hours - 12 : (hours === 0 ? 12 : hours);
  const dayOfWeek = getDayOfWeek(`${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
  return `${year}.${month}.${day} (${dayOfWeek}) ${ampm} ${displayHours}:${minutes}`;
}

function startDetailCountdown() {
  const countdownEl = document.getElementById("countdown-detail");
  if (!countdownEl) return;

  if (window.detailCountdownInterval) {
    clearInterval(window.detailCountdownInterval);
    window.detailCountdownInterval = null;
  }

  const updateCountdown = () => {
    const openTime = new Date(countdownEl.dataset.openTime);
    const now = new Date();
    const diff = openTime - now;
    const totalSec = Math.max(0, Math.ceil(diff / 1000));

    if (totalSec <= 0) {
      countdownEl.textContent = "예매 시작!";
      countdownEl.style.background = "#E61E51";
      clearInterval(window.detailCountdownInterval);
      window.detailCountdownInterval = null;

      setTimeout(() => {
        activateBookingPage();
      }, 600);
      return;
    }

    const days = Math.floor(totalSec / (60 * 60 * 24));
    const hours = Math.floor((totalSec % (60 * 60 * 24)) / (60 * 60));
    const minutes = Math.floor((totalSec % (60 * 60)) / 60);
    const seconds = Math.floor(totalSec % 60);

    let text = "오픈까지 ";
    if (days > 0) text += `${days}일 `;
    text += `${hours}시간 ${minutes}분 ${seconds}초`;
    countdownEl.textContent = text;

    // 1시간 미만이면 색상 강조
    if (diff < 3600000) {
      countdownEl.style.background = "#ef4444";
      countdownEl.style.animation = "pulse 2s infinite";
    } else {
      countdownEl.style.background = "";
      countdownEl.style.animation = "";
    }
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
    bookingBtn.textContent = "예매 시작";
    bookingBtn.style.display = "none";
  }

  attachEventListeners();
  showAlert("예매가 시작되었습니다. 날짜와 회차를 선택해 주세요.", "success");
}

loadPerformance();
