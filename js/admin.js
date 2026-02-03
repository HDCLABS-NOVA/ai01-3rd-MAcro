// Admin Dashboard JavaScript

const API_BASE = window.location.origin;

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    loadPerformances();
    setupEventListeners();
    startCountdownUpdates();
});

// 이벤트 리스너 설정
function setupEventListeners() {
    // 새 공연 추가 버튼 (나중에 구현 가능)
    const addBtn = document.getElementById('addPerformanceBtn');
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            alert('새 공연 추가 기능은 추후 구현 예정입니다.');
        });
    }
}

// 공연 목록 불러오기
async function loadPerformances() {
    const container = document.getElementById('performancesContainer');

    try {
        container.innerHTML = '<div class="loading">공연 목록을 불러오는 중...</div>';

        const response = await fetch(`${API_BASE}/api/performances`);
        const data = await response.json();

        if (data.success && data.performances.length > 0) {
            container.innerHTML = '';
            data.performances.forEach(perf => {
                container.appendChild(createPerformanceCard(perf));
            });
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>등록된 공연이 없습니다</h3>
                    <p>새 공연을 추가해 주세요.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('공연 목록 로딩 실패:', error);
        container.innerHTML = `
            <div class="empty-state">
                <h3>오류가 발생했습니다</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// 공연 카드 생성
function createPerformanceCard(perf) {
    const card = document.createElement('div');
    card.className = 'performance-card';
    card.dataset.perfId = perf.id;

    const openTime = perf.open_time ? new Date(perf.open_time) : null;
    const now = new Date();
    const isUpcoming = openTime && openTime > now;
    const statusClass = perf.status === 'open' ? 'status-open' :
        perf.status === 'closed' ? 'status-closed' : 'status-upcoming';

    card.innerHTML = `
        <div class="performance-header">
            <div>
                <h3 class="performance-title">${perf.title}</h3>
                <span class="performance-category">${perf.category || '기타'}</span>
            </div>
            <span class="status-badge ${statusClass}">${getStatusText(perf.status)}</span>
        </div>
        
        <div class="performance-info">
            <div><strong>장소:</strong> ${perf.venue}</div>
            <div><strong>공연 ID:</strong> <code>${perf.id}</code></div>
        </div>
        
        <div class="open-time-section">
            <label>티켓 오픈 시간</label>
            <input 
                type="datetime-local" 
                class="datetime-input" 
                id="openTime_${perf.id}"
                value="${openTime ? formatDatetimeLocal(openTime) : ''}"
            />
            ${isUpcoming ? `<div class="countdown-timer" id="countdown_${perf.id}"></div>` : ''}
        </div>
        
        <div class="card-actions">
            <button class="btn btn-success" onclick="updateOpenTime('${perf.id}')">
                💾 저장
            </button>
            <button class="btn btn-secondary" onclick="viewPerformanceDetail('${perf.id}')">
                👁️ 상세
            </button>
        </div>
    `;

    return card;
}

// 상태 텍스트 변환
function getStatusText(status) {
    const statusMap = {
        'upcoming': '오픈 예정',
        'open': '판매중',
        'closed': '판매 종료'
    };
    return statusMap[status] || status;
}

// datetime-local 형식으로 변환
function formatDatetimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// 오픈 시간 업데이트
async function updateOpenTime(perfId) {
    const input = document.getElementById(`openTime_${perfId}`);
    const newOpenTime = input.value;

    if (!newOpenTime) {
        alert('오픈 시간을 선택해 주세요.');
        return;
    }

    // ✅ 수정: datetime-local 값을 한국 시간대로 올바르게 변환
    // datetime-local 형식: "2026-02-03T10:25"
    // 원하는 결과: "2026-02-03T10:25:00+09:00"
    const isoTime = newOpenTime + ':00+09:00';

    try {
        const response = await fetch(`${API_BASE}/api/admin/performances/${perfId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                open_time: isoTime
            })
        });

        const data = await response.json();

        if (data.success) {
            alert('✅ 오픈 시간이 업데이트되었습니다!');
            loadPerformances(); // 목록 새로고침
        } else {
            alert('❌ 업데이트 실패: ' + (data.detail || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('업데이트 오류:', error);
        alert('❌ 오류: ' + error.message);
    }
}

// 공연 상세 보기
function viewPerformanceDetail(perfId) {
    alert(`공연 ID: ${perfId}\n\n상세 정보 페이지는 추후 구현 예정입니다.`);
}

// 카운트다운 타이머 업데이트
function startCountdownUpdates() {
    setInterval(() => {
        const countdowns = document.querySelectorAll('.countdown-timer');
        countdowns.forEach(countdown => {
            const perfId = countdown.id.replace('countdown_', '');
            const input = document.getElementById(`openTime_${perfId}`);

            if (input && input.value) {
                const openTime = new Date(input.value);
                const now = new Date();
                const diff = openTime - now;

                if (diff > 0) {
                    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
                    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

                    let text = '⏰ 오픈까지: ';
                    if (days > 0) text += `${days}일 `;
                    text += `${hours}시간 ${minutes}분 ${seconds}초`;

                    countdown.textContent = text;

                    // 1시간 이내면 urgent 클래스 추가
                    if (diff < 3600000) {
                        countdown.classList.add('urgent');
                    }
                } else {
                    countdown.textContent = '🎉 판매 오픈!';
                    countdown.classList.add('urgent');
                }
            }
        });
    }, 1000); // 1초마다 업데이트
}

// 전역 함수로 노출
window.updateOpenTime = updateOpenTime;
window.viewPerformanceDetail = viewPerformanceDetail;
