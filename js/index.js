// index.js - 메인 페이지 (공연 목록)

let performances = [];
let currentFilter = 'all';

async function loadPerformances() {
    try {
        const response = await fetch('data/performances.json');
        const data = await response.json();
        performances = data.performances;
        displayPerformances();
    } catch (error) {
        console.error('공연 데이터 로드 실패:', error);
        showAlert('공연 정보를 불러오는데 실패했습니다.', 'error');
    }
}

function displayPerformances() {
    const listDiv = document.getElementById('performance-list');
    const filtered = currentFilter === 'all'
        ? performances
        : performances.filter(p => p.category === currentFilter);

    const now = new Date();

    listDiv.innerHTML = filtered.map(perf => {
        const openTime = perf.open_time ? new Date(perf.open_time) : null;
        const isOpen = !openTime || openTime <= now;
        const statusBadge = getStatusBadge(perf, openTime, now);

        // ✅ 변경: 오픈 전이어도 클릭 가능 (모두 selectPerformance로 이동)
        const clickAction = `selectPerformance('${perf.id}')`;
        const cardClass = 'performance-card'; // 잠금 스타일 제거

        return `
            <div class="${cardClass}" onclick="${clickAction}">
              <div class="performance-card-image" style="background-image: url('${encodeURI(perf.image)}'); background-size: cover; background-position: center; background-repeat: no-repeat; background-color: var(--primary-color);">
                <div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-size: 48px; background: ${perf.image ? 'transparent' : 'rgba(0,0,0,0.2)'};">
                  ${perf.image ? '' : getCategoryIcon(perf.category)}
                </div>
                ${statusBadge}
              </div>
              <div class="performance-card-content">
                <span class="performance-card-category">${getCategoryName(perf.category)}</span>
                <h3 class="performance-card-title">${perf.title}</h3>
                <p class="performance-card-venue">📍 ${perf.venue}</p>
                <p class="performance-card-date">📅 ${formatDateKorean(perf.dates[0])} ${perf.dates.length > 1 ? '외 ' + (perf.dates.length - 1) + '일' : ''}</p>
                ${getOpenTimeInfo(perf, openTime, now)}
              </div>
            </div>
        `;
    }).join('');

    // 카운트다운 타이머 시작
    startCountdowns();
}

function getStatusBadge(perf, openTime, now) {
    if (!openTime) return '';

    if (openTime > now) {
        return '<div class="performance-status-badge badge-upcoming">🔒 오픈 예정</div>';
    } else {
        return '<div class="performance-status-badge badge-open">✅ 판매중</div>';
    }
}

function getOpenTimeInfo(perf, openTime, now) {
    if (!openTime) return '';

    if (openTime > now) {
        return `
            <div class="open-time-info">
                <p class="open-time-label">⏰ 티켓 오픈</p>
                <p class="open-time-date">${formatOpenTime(openTime)}</p>
                <div class="countdown-timer" id="countdown_${perf.id}" data-open-time="${openTime.toISOString()}"></div>
            </div>
        `;
    }
    return '';
}

function formatOpenTime(date) {
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const hours = date.getHours();
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? '오후' : '오전';
    const displayHours = hours > 12 ? hours - 12 : (hours === 0 ? 12 : hours);

    return `${year}.${month}.${day} ${ampm} ${displayHours}:${minutes}`;
}

function startCountdowns() {
    const countdownElements = document.querySelectorAll('.countdown-timer');

    if (countdownElements.length === 0) return;

    // 기존 인터벌 클리어
    if (window.countdownInterval) {
        clearInterval(window.countdownInterval);
    }

    // 1초마다 업데이트
    window.countdownInterval = setInterval(() => {
        const now = new Date();
        let shouldReload = false;

        countdownElements.forEach(elem => {
            const openTime = new Date(elem.dataset.openTime);
            const diff = openTime - now;

            if (diff <= 0) {
                elem.textContent = '🎉 판매 시작!';
                elem.classList.add('countdown-finished');
                shouldReload = true;
            } else {
                const days = Math.floor(diff / (1000 * 60 * 60 * 24));
                const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((diff % (1000 * 60)) / 1000);

                let text = '';
                if (days > 0) text += `${days}일 `;
                text += `${hours}시간 ${minutes}분 ${seconds}초`;

                elem.textContent = text;

                // 1시간 미만이면 강조
                if (diff < 3600000) {
                    elem.classList.add('countdown-urgent');
                }
            }
        });

        // 오픈 시간이 된 항목이 있으면 페이지 새로고침
        if (shouldReload) {
            setTimeout(() => {
                loadPerformances();
            }, 2000);
        }
    }, 1000);
}

function getCategoryIcon(category) {
    const icons = {
        concert: `<svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path><path d="M19 10v1a7 7 0 0 1-14 0v-1"></path><line x1="12" y1="19" x2="12" y2="22"></line><line x1="8" y1="22" x2="16" y2="22"></line></svg>`,
        musical: `<svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4.5V12"></path><path d="M18.5 7v5a6.5 6.5 0 0 1-13 0V7"></path><path d="M12 4.5l6.5 2.5a1 1 0 0 1 .5.87V12a7 7 0 0 1-14 0V7.87a1 1 0 0 1 .5-.87l6.5-2.5z"></path></svg>`,
        sports: `<svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M6.06 6.06l11.88 11.88"></path><path d="M17.94 6.06l-11.88 11.88"></path><circle cx="12" cy="12" r="4"></circle></svg>`,
        exhibition: `<svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>`
    };
    return icons[category] || `<svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h18l1 10H2L3 7z"></path><path d="M12 4v4"></path></svg>`;
}

function getCategoryName(category) {
    const names = {
        concert: '콘서트',
        musical: '뮤지컬',
        sports: '스포츠',
        exhibition: '전시'
    };
    return names[category] || '공연';
}

function getRandomGradient() {
    const gradients = [
        '#667eea 0%, #764ba2 100%',
        '#f093fb 0%, #f5576c 100%',
        '#4facfe 0%, #00f2fe 100%',
        '#43e97b 0%, #38f9d7 100%',
        '#fa709a 0%, #fee140 100%',
        '#30cfd0 0%, #330867 100%'
    ];
    return gradients[Math.floor(Math.random() * gradients.length)];
}

function selectPerformance(perfId) {
    navigateTo(`performance_detail.html?id=${perfId}`);
}

// 필터 버튼 이벤트
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        currentFilter = this.dataset.category;
        displayPerformances();
    });
});

// 페이지 로드
loadPerformances();
