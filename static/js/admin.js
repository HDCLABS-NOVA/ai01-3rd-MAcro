// 로그 뷰어 페이지(viewer.html) JavaScript

let currentLog = null;

async function loadLog(filename) {
  // 활성 상태 변경
  document.querySelectorAll('.log-item').forEach(el => el.classList.remove('active'));
  event.currentTarget.classList.add('active');

  const response = await fetch(`/api/logs/${filename}`);
  const data = await response.json();
  currentLog = data;

  renderDetail(data);
}

function renderDetail(data) {
  const container = document.getElementById('detailContent');

  const isBot = data.is_bot || false;
  const botScore = data.bot_score || 0;

  // 체류 시간 계산
  let durationMs = data.total_duration_ms || data.wait_duration_ms || 0;
  if (durationMs === 0) {
    if (data.page_entry_time && data.page_exit_time) {
      durationMs = new Date(data.page_exit_time) - new Date(data.page_entry_time);
    } else if (data.queue_start_time && data.queue_end_time) {
      durationMs = new Date(data.queue_end_time) - new Date(data.queue_start_time);
    } else if (data.booking_start_time && data.booking_end_time) {
      durationMs = new Date(data.booking_end_time) - new Date(data.booking_start_time);
    }
  }

  // 마우스 궤적 통합 - 실제 예매 흐름 순서: captcha → section → seats → discount → booker → payment
  let allTrajectory = [];
  if (data.mouse_trajectory) {
    allTrajectory = allTrajectory.concat(data.mouse_trajectory.map(p => ({ ...p, stage: '기타' })));
  }
  if (data.captcha?.mouse_trajectory) {
    allTrajectory = allTrajectory.concat(data.captcha.mouse_trajectory.map(p => ({ ...p, stage: '🔒 보안문자' })));
  }
  if (data.section_selection?.mouse_trajectory) {
    allTrajectory = allTrajectory.concat(data.section_selection.mouse_trajectory.map(p => ({ ...p, stage: '📍 구역선택' })));
  }
  if (data.mouse_trajectory_seats) {
    allTrajectory = allTrajectory.concat(data.mouse_trajectory_seats.map(p => ({ ...p, stage: '🎫 좌석선택' })));
  }
  if (data.mouse_trajectory_discount) {
    allTrajectory = allTrajectory.concat(data.mouse_trajectory_discount.map(p => ({ ...p, stage: '💳 할인권종' })));
  }
  if (data.mouse_trajectory_booker) {
    allTrajectory = allTrajectory.concat(data.mouse_trajectory_booker.map(p => ({ ...p, stage: '🚚 배송선택' })));
  }
  if (data.mouse_trajectory_payment) {
    allTrajectory = allTrajectory.concat(data.mouse_trajectory_payment.map(p => ({ ...p, stage: '💰 결제수단' })));
  }

  // 클릭 데이터 통합 (stage 정보 포함)
  let allClicks = [];

  // 기본 clicks
  if (data.clicks) {
    allClicks = allClicks.concat(data.clicks.map(c => ({ ...c, stage: '기타' })));
  }
  // 좌석 선택
  if (data.seat_selection?.clicks) {
    allClicks = allClicks.concat(data.seat_selection.clicks.map(c => ({ ...c, stage: '🎫 좌석선택' })));
  }
  // 캡차
  if (data.captcha?.clicks) {
    allClicks = allClicks.concat(data.captcha.clicks.map(c => ({ ...c, stage: '🔒 보안문자' })));
  }
  // 구역 선택
  if (data.section_selection?.clicks) {
    const validClicks = data.section_selection.clicks
      .filter(c => c.x !== undefined && c.y !== undefined)
      .map(c => ({ ...c, stage: '📍 구역선택', target: c.section }));
    allClicks = allClicks.concat(validClicks);
  }
  // 할인권종
  if (data.clicks_discount) {
    allClicks = allClicks.concat(data.clicks_discount.map(c => ({ ...c, stage: '💳 할인권종' })));
  }
  // 예매자정보
  if (data.clicks_booker) {
    allClicks = allClicks.concat(data.clicks_booker.map(c => ({ ...c, stage: '🚚 배송선택' })));
  }
  // 결제
  if (data.clicks_payment) {
    allClicks = allClicks.concat(data.clicks_payment.map(c => ({ ...c, stage: '💰 결제수단' })));
  }

  // 호버 횟수 계산 (actions에서 hover관련 이벤트 집계)
  let hoverCount = (data.hovers || []).length;
  if (data.seat_selection?.hovers) hoverCount += data.seat_selection.hovers.length;
  if (hoverCount === 0 && data.actions) {
    hoverCount = data.actions.filter(a => a.action && a.action.includes('hover')).length;
  }

  // 클릭 횟수 계산
  let clickCount = allClicks.length;
  if (clickCount === 0 && data.actions) {
    clickCount = data.actions.filter(a => a.action && (a.action.includes('click') || a.action.includes('select'))).length;
  }
  if (clickCount === 0 && data.card_clicks) {
    clickCount = data.card_clicks.length +
      (data.date_selections || []).length +
      (data.time_selections || []).length;
  }
  if (data.section_selection?.clicks) clickCount += data.section_selection.clicks.length;

  // 단계 표시
  const stageLabels = { 'perf': '🎭 공연창', 'que': '⏳ 대기열', 'book': '🎫 예매창' };
  const stageLabel = stageLabels[data.stage] || data.stage || '-';

  container.innerHTML = `
        <div class="detail-section">
            <h3 class="detail-title">세션 정보</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">세션 ID</div>
                    <div class="detail-value">${data.session_id || '-'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">사용자 ID</div>
                    <div class="detail-value">${data.user_email || data.user_id || '-'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">IP 주소</div>
                    <div class="detail-value">${data.user_ip || '-'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">단계</div>
                    <div class="detail-value">${stageLabel}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">체류 시간</div>
                    <div class="detail-value">${(durationMs / 1000).toFixed(1)}초</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">봇 스코어</div>
                    <div class="detail-value" style="color: ${botScore > 0.7 ? '#dc3545' : botScore > 0.4 ? '#ffc107' : '#28a745'}">
                        ${(botScore * 100).toFixed(0)}%
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">결제 완료</div>
                    <div class="detail-value" style="color: ${data.payment_completed ? '#28a745' : '#888'}">
                        ${data.payment_completed ? '✅ 완료' : '❌ 미완료'}
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">예매번호</div>
                    <div class="detail-value" style="font-weight: 700; color: ${data.booking_id ? '#6b4fbb' : '#888'}">
                        ${data.booking_id || '-'}
                    </div>
                </div>
            </div>
            
            ${isBot ? `
                <div style="background: #fff5f5; border: 1px solid #ffcdd2; padding: 12px; border-radius: 8px; margin-bottom: 20px;">
                    <strong style="color: #d32f2f;">🤖 봇 탐지</strong>
                    <p style="margin-top: 4px; font-size: 13px; color: #666;">
                        유형: ${data.bot_type || '-'} (${data.bot_description || '-'})
                    </p>
                </div>
            ` : ''}
            
            <h3 class="detail-title">마우스 궤적</h3>
            <div class="trajectory-controls">
                <button onclick="zoomTrajectory(1.2)">🔍+ 확대</button>
                <button onclick="zoomTrajectory(0.8)">🔍- 축소</button>
                <button onclick="resetZoom()">↺ 리셋</button>
                <span id="zoomLevel">100%</span>
            </div>
            <div class="trajectory-container">
                <canvas class="trajectory-canvas" id="trajectoryCanvas"></canvas>
                <div class="trajectory-info" id="trajectoryInfo">해상도: - | 포인트: -</div>
                <div class="click-tooltip" id="clickTooltip"></div>
            </div>
            
            <h3 class="detail-title">행동 통계</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">마우스 궤적 포인트</div>
                    <div class="detail-value">${allTrajectory.length}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">클릭/선택 횟수</div>
                    <div class="detail-value">${clickCount}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">호버 횟수</div>
                    <div class="detail-value">${hoverCount}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">선택 좌석</div>
                    <div class="detail-value">${(data.selected_seats || data.seat_selection?.seats || data.seats?.selected || []).join(', ') || '-'}</div>
                </div>
            </div>
            
            <h3 class="detail-title">원본 데이터</h3>
            <div class="json-view">${JSON.stringify(data, null, 2)}</div>
        </div>
    `;

  // 궤적 그리기 - 통합된 궤적과 클릭 사용
  drawTrajectory(allTrajectory, allClicks);
}

let currentZoom = 1;
let currentTrajectory = [];
let currentClicks = [];
let panOffsetX = 0;
let panOffsetY = 0;
let isPanning = false;
let panStartX = 0;
let panStartY = 0;

function zoomTrajectory(factor) {
  currentZoom *= factor;
  currentZoom = Math.max(0.5, Math.min(10, currentZoom));
  document.getElementById('zoomLevel').textContent = Math.round(currentZoom * 100) + '%';
  drawTrajectory(currentTrajectory, currentClicks);
}

function resetZoom() {
  currentZoom = 1;
  panOffsetX = 0;
  panOffsetY = 0;
  document.getElementById('zoomLevel').textContent = '100%';
  drawTrajectory(currentTrajectory, currentClicks);
}

function drawTrajectory(trajectory, clicks) {
  currentTrajectory = trajectory;
  currentClicks = clicks;

  const canvas = document.getElementById('trajectoryCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * 2; // 고해상도
  canvas.height = rect.height * 2;
  ctx.scale(2, 2);

  const displayWidth = rect.width;
  const displayHeight = rect.height;

  // 배경
  ctx.fillStyle = '#1a1a2e';
  ctx.fillRect(0, 0, displayWidth, displayHeight);

  if (trajectory.length === 0) {
    ctx.fillStyle = '#666';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('궤적 데이터 없음', displayWidth / 2, displayHeight / 2);
    return;
  }

  // 원본 해상도 계산 (데이터 기반)
  const allPoints = [...trajectory, ...clicks.filter(c => c.x !== undefined)];
  const maxX = Math.max(...allPoints.map(p => p.x || 0), 1920);
  const maxY = Math.max(...allPoints.map(p => p.y || 0), 1080);

  // 화면 비율 유지 (16:9 또는 데이터 기반)
  const aspectRatio = maxX / maxY;
  const padding = 30;

  let drawWidth, drawHeight;
  if ((displayWidth - padding * 2) / (displayHeight - padding * 2) > aspectRatio) {
    drawHeight = (displayHeight - padding * 2) * currentZoom;
    drawWidth = drawHeight * aspectRatio;
  } else {
    drawWidth = (displayWidth - padding * 2) * currentZoom;
    drawHeight = drawWidth / aspectRatio;
  }

  const offsetX = (displayWidth - drawWidth) / 2 + panOffsetX;
  const offsetY = (displayHeight - drawHeight) / 2 + panOffsetY;
  const scaleX = drawWidth / maxX;
  const scaleY = drawHeight / maxY;

  // 격자선 그리기
  ctx.strokeStyle = 'rgba(255,255,255,0.1)';
  ctx.lineWidth = 0.5;
  const gridStep = 200;
  for (let gx = 0; gx <= maxX; gx += gridStep) {
    const x = gx * scaleX + offsetX;
    ctx.beginPath();
    ctx.moveTo(x, offsetY);
    ctx.lineTo(x, offsetY + drawHeight);
    ctx.stroke();
  }
  for (let gy = 0; gy <= maxY; gy += gridStep) {
    const y = gy * scaleY + offsetY;
    ctx.beginPath();
    ctx.moveTo(offsetX, y);
    ctx.lineTo(offsetX + drawWidth, y);
    ctx.stroke();
  }

  // 테두리 (화면 영역 표시)
  ctx.strokeStyle = 'rgba(255,255,255,0.3)';
  ctx.lineWidth = 1;
  ctx.strokeRect(offsetX, offsetY, drawWidth, drawHeight);

  // 궤적 그리기
  ctx.strokeStyle = '#667eea';
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();

  trajectory.forEach((point, i) => {
    const x = point.x * scaleX + offsetX;
    const y = point.y * scaleY + offsetY;

    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // 클릭 포인트 (빨간 점)
  clicks.forEach(click => {
    if (click.x === undefined || click.y === undefined) return;
    const x = click.x * scaleX + offsetX;
    const y = click.y * scaleY + offsetY;

    ctx.fillStyle = '#ff6b6b';
    ctx.beginPath();
    ctx.arc(x, y, 8, 0, Math.PI * 2);
    ctx.fill();

    // 클릭 테두리
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();
  });

  // 시작점 (녹색)
  if (trajectory.length > 0) {
    const startX = trajectory[0].x * scaleX + offsetX;
    const startY = trajectory[0].y * scaleY + offsetY;
    ctx.fillStyle = '#2ecc71';
    ctx.beginPath();
    ctx.arc(startX, startY, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  // 끝점 (주황색)
  if (trajectory.length > 1) {
    const endX = trajectory[trajectory.length - 1].x * scaleX + offsetX;
    const endY = trajectory[trajectory.length - 1].y * scaleY + offsetY;
    ctx.fillStyle = '#f39c12';
    ctx.beginPath();
    ctx.arc(endX, endY, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  // 정보 표시
  const info = document.getElementById('trajectoryInfo');
  if (info) {
    info.textContent = `해상도: ${maxX}x${maxY} | 포인트: ${trajectory.length} | 클릭: ${clicks.length}`;
  }

  // 툴팁 및 패닝 이벤트 설정
  setupTooltipAndPan(canvas, clicks, trajectory, scaleX, scaleY, offsetX, offsetY);
}

let tooltipHandler = null;
let panHandlers = { mousedown: null, mousemove: null, mouseup: null };

function setupTooltipAndPan(canvas, clicks, trajectory, scaleX, scaleY, offsetX, offsetY) {
  const tooltip = document.getElementById('clickTooltip');
  if (!tooltip) return;

  // 기존 이벤트 제거
  if (tooltipHandler) {
    canvas.removeEventListener('mousemove', tooltipHandler);
  }
  if (panHandlers.mousedown) {
    canvas.removeEventListener('mousedown', panHandlers.mousedown);
    canvas.removeEventListener('mousemove', panHandlers.mousemove);
    canvas.removeEventListener('mouseup', panHandlers.mouseup);
    canvas.removeEventListener('mouseleave', panHandlers.mouseup);
  }

  // 시작점/끝점 정보
  const startPoint = trajectory.length > 0 ? trajectory[0] : null;
  const endPoint = trajectory.length > 1 ? trajectory[trajectory.length - 1] : null;

  // 패닝 핸들러
  panHandlers.mousedown = (e) => {
    if (currentZoom <= 1) return; // 줌인 상태에서만 패닝
    isPanning = true;
    panStartX = e.clientX - panOffsetX;
    panStartY = e.clientY - panOffsetY;
    canvas.style.cursor = 'grabbing';
  };

  panHandlers.mousemove = (e) => {
    if (isPanning) {
      panOffsetX = e.clientX - panStartX;
      panOffsetY = e.clientY - panStartY;
      drawTrajectory(currentTrajectory, currentClicks);
      return;
    }

    // 툴팁 처리
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    let found = null;
    let pointType = null;

    // 시작점 감지 (녹색)
    if (startPoint) {
      const sx = startPoint.x * scaleX + offsetX;
      const sy = startPoint.y * scaleY + offsetY;
      if (Math.sqrt((mouseX - sx) ** 2 + (mouseY - sy) ** 2) < 15) {
        found = startPoint;
        pointType = '🟢 시작점';
      }
    }

    // 끝점 감지 (주황색)
    if (!found && endPoint) {
      const ex = endPoint.x * scaleX + offsetX;
      const ey = endPoint.y * scaleY + offsetY;
      if (Math.sqrt((mouseX - ex) ** 2 + (mouseY - ey) ** 2) < 15) {
        found = endPoint;
        pointType = '🟠 끝점';
      }
    }

    // 클릭 포인트 감지 (빨간색)
    if (!found) {
      for (const click of clicks) {
        if (click.x === undefined || click.y === undefined) continue;
        const cx = click.x * scaleX + offsetX;
        const cy = click.y * scaleY + offsetY;
        const dist = Math.sqrt((mouseX - cx) ** 2 + (mouseY - cy) ** 2);
        if (dist < 15) {
          found = click;
          pointType = '🔴 클릭';
          break;
        }
      }
    }

    if (found) {
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
      tooltip.style.top = (e.clientY - rect.top - 10) + 'px';

      // 시간 정보 포맷팅 (ISO 기준 hh:mm:ss.ff)
      let timeStr = '';
      const formatISOTime = (date) => {
        const h = String(date.getHours()).padStart(2, '0');
        const m = String(date.getMinutes()).padStart(2, '0');
        const s = String(date.getSeconds()).padStart(2, '0');
        const f = String(Math.floor(date.getMilliseconds() / 10)).padStart(2, '0');
        return `${h}:${m}:${s}.${f}`;
      };

      // 기준 시간 (booking_start_time 또는 queue_start_time 등)
      const baseTime = currentLog.booking_start_time || currentLog.queue_start_time || currentLog.page_entry_time || currentLog.created_at;
      const baseDate = baseTime ? new Date(baseTime) : null;

      if (found.timestamp !== undefined) {
        if (typeof found.timestamp === 'number' && baseDate) {
          // ms 단위 상대 시간 → 절대 시간
          const actualTime = new Date(baseDate.getTime() + found.timestamp);
          timeStr = `<div class="coords">시간: ${formatISOTime(actualTime)}</div>`;
        } else if (typeof found.timestamp === 'string') {
          // ISO 시간
          timeStr = `<div class="coords">시간: ${formatISOTime(new Date(found.timestamp))}</div>`;
        } else if (typeof found.timestamp === 'number') {
          // 기준 시간 없으면 상대 표시
          const sec = (found.timestamp / 1000).toFixed(1);
          timeStr = `<div class="coords">시간: +${sec}초</div>`;
        }
      } else if (found.t !== undefined && baseDate) {
        // 궤적 포인트 (ms 단위) → 절대 시간
        const actualTime = new Date(baseDate.getTime() + found.t);
        timeStr = `<div class="coords">시간: ${formatISOTime(actualTime)}</div>`;
      } else if (found.t !== undefined) {
        const sec = (found.t / 1000).toFixed(1);
        timeStr = `<div class="coords">시간: +${sec}초</div>`;
      }

      tooltip.innerHTML = `
                <div class="stage">${pointType} | ${found.stage || '기타'}</div>
                <div class="coords">좌표: (${Math.round(found.x)}, ${Math.round(found.y)})</div>
                ${timeStr}
                ${found.target ? `<div class="target">대상: ${found.target}</div>` : ''}
            `;
      canvas.style.cursor = 'pointer';
    } else {
      tooltip.style.display = 'none';
      canvas.style.cursor = currentZoom > 1 ? 'grab' : 'default';
    }
  };

  panHandlers.mouseup = () => {
    isPanning = false;
    canvas.style.cursor = currentZoom > 1 ? 'grab' : 'default';
  };

  canvas.addEventListener('mousedown', panHandlers.mousedown);
  canvas.addEventListener('mousemove', panHandlers.mousemove);
  canvas.addEventListener('mouseup', panHandlers.mouseup);
  canvas.addEventListener('mouseleave', () => {
    tooltip.style.display = 'none';
    isPanning = false;
  });
}
