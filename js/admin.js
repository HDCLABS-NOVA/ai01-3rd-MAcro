// Admin Dashboard JavaScript

const API_BASE = window.location.origin;

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    loadPerformances();
    setupEventListeners();
    startCountdownUpdates();
});

// 이벤트 리스너 설정
// 이벤트 리스너 설정
function setupEventListeners() {
    // 새 공연 추가 버튼 (모달 열기)
    const addBtn = document.getElementById('addPerformanceBtn');
    const modal = document.getElementById('addPerformanceModal');
    const closeBtn = document.getElementById('closeModalBtn');
    const form = document.getElementById('addPerformanceForm');

    if (addBtn && modal) {
        addBtn.addEventListener('click', () => {
            modal.classList.add('active');
            // 날짜 기본값: 오늘 + 7일
            const nextWeek = new Date();
            nextWeek.setDate(nextWeek.getDate() + 7);
            document.getElementById('perf_open_time').value = formatDatetimeLocal(nextWeek);
        });
    }

    // 모달 닫기 버튼
    if (closeBtn && modal) {
        closeBtn.addEventListener('click', () => {
            closeAllModals();
        });
    }

    // 모달 외부 클릭 시 닫기
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAllModals();
            }
        });
    }

    // 폼 제출
    if (form) {
        form.addEventListener('submit', handleAddPerformance);
    }

    // --- 수정 모달 리스너 ---
    const editModal = document.getElementById('editPerformanceModal');
    const closeEditBtn = document.getElementById('closeEditModalBtn');
    const editForm = document.getElementById('editPerformanceForm');

    if (closeEditBtn) {
        closeEditBtn.addEventListener('click', closeAllModals);
    }

    if (editModal) {
        editModal.addEventListener('click', (e) => {
            if (e.target === editModal) closeAllModals();
        });
    }

    if (editForm) {
        editForm.addEventListener('submit', handleEditPerformance);
    }
}

// 모달 닫기
function closeAllModals() {
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    document.getElementById('addPerformanceForm')?.reset();
    document.getElementById('editPerformanceForm')?.reset();
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
                💾 시간 저장
            </button>
            <button class="btn btn-primary" onclick="openEditModal('${perf.id}')">
                ✏️ 수정
            </button>
            <button class="btn btn-danger" onclick="deletePerformance('${perf.id}')">
                🗑️ 삭제
            </button>
        </div>
    `;

    return card;
}

// 공연 삭제
async function deletePerformance(perfId) {
    if (!confirm('정말로 이 공연을 삭제하시겠습니까?\n삭제된 데이터는 복구할 수 없습니다.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/admin/performances/${perfId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            alert('✅ 공연이 삭제되었습니다.');
            loadPerformances();
        } else {
            alert('❌ 삭제 실패: ' + (result.detail || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('삭제 오류:', error);
        alert('❌ 오류: ' + error.message);
    }
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
window.openEditModal = openEditModal;
window.deletePerformance = deletePerformance;

// 새 공연 추가 처리
async function handleAddPerformance(e) {
    e.preventDefault();

    const formData = new FormData(e.target);

    // 날짜/시간 리스트 변환 (공백 제거 후 배열로)
    const dates = formData.get('dates').split(',').map(d => d.trim()).filter(d => d);
    const times = formData.get('times').split(',').map(t => t.trim()).filter(t => t);

    // 오픈 시간 포맷팅
    let openTime = formData.get('open_time');
    if (openTime && openTime.length === 16) { // YYYY-MM-DDTHH:mm
        openTime += ':00+09:00';
    }

    const newPerformance = {
        id: formData.get('id'),
        title: formData.get('title'),
        category: formData.get('category'),
        venue: formData.get('venue'),
        dates: dates,
        times: times,
        // 기본값 설정
        grades: [
            { "grade": "VIP", "price": 150000, "seats": 100 },
            { "grade": "R", "price": 120000, "seats": 200 },
            { "grade": "S", "price": 90000, "seats": 300 }
        ],
        image: "images/concert01.jpg", // 임시 이미지
        description: formData.get('description'),
        open_time: openTime,
        status: "upcoming"
    };

    try {
        const response = await fetch(`${API_BASE}/api/admin/performances`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newPerformance)
        });

        const result = await response.json();

        if (result.success) {
            alert('✅ 새 공연이 성공적으로 추가되었습니다!');
            closeAllModals();
            loadPerformances();
        } else {
            alert('❌ 추가 실패: ' + (result.detail || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('공연 추가 오류:', error);
        alert('❌ 오류: ' + error.message);
    }
}

// 수정 모달 열기
async function openEditModal(perfId) {
    try {
        const response = await fetch(`${API_BASE}/api/performances/${perfId}`);
        const data = await response.json();

        if (!data.success) {
            alert('공연 정보를 불러오는데 실패했습니다.');
            return;
        }

        const perf = data.performance;

        // 폼 채우기
        // Hidden Input 제거, 대신 edit_perf_id 사용

        document.getElementById('edit_perf_id').value = perf.id;
        document.getElementById('edit_perf_title').value = perf.title;
        document.getElementById('edit_perf_category').value = perf.category;
        document.getElementById('edit_perf_venue').value = perf.venue;
        document.getElementById('edit_perf_dates').value = perf.dates.join(', ');
        document.getElementById('edit_perf_times').value = perf.times.join(', ');
        document.getElementById('edit_perf_status').value = perf.status;
        document.getElementById('edit_perf_desc').value = perf.description || '';

        if (perf.open_time) {
            document.getElementById('edit_perf_open_time').value = perf.open_time.slice(0, 16);
        }

        document.getElementById('editPerformanceModal').classList.add('active');

    } catch (error) {
        console.error('상세 정보 로딩 실패:', error);
        alert('❌ 오류: ' + error.message);
    }
}

// 수정 사항 저장
async function handleEditPerformance(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const originalId = document.getElementById('edit_perf_id').value; // DOM에서 직접 값 읽기 (가장 확실함)

    // 날짜/시간 리스트
    const dates = formData.get('dates').split(',').map(d => d.trim()).filter(d => d);
    const times = formData.get('times').split(',').map(t => t.trim()).filter(t => t);

    // 오픈 시간
    let openTime = formData.get('open_time');
    if (openTime && openTime.length === 16) {
        openTime += ':00+09:00';
    }

    const updateData = {
        id: originalId,
        title: formData.get('title'),
        category: formData.get('category'),
        venue: formData.get('venue'),
        dates: dates,
        times: times,
        description: formData.get('description'),
        open_time: openTime,
        status: formData.get('status')
    };

    try {
        // 반드시 'originalId'를 사용하여 기존 리소스를 찾고, Body에는 새 정보를 담아 보냄
        const response = await fetch(`${API_BASE}/api/admin/performances/${originalId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });

        const result = await response.json();

        if (result.success) {
            alert('✅ 공연 정보가 수정되었습니다!');
            closeAllModals();
            loadPerformances();
        } else {
            alert('❌ 수정 실패: ' + (result.detail || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('수정 오류:', error);
        alert('❌ 오류: ' + error.message);
    }
}
