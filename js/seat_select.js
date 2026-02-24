// seat_select.js - 좌석 선택 페이지 전용 JavaScript

// 초기화
loadLogState();
recordStageEntry('captcha');

// 보안문자 관련 변수 (전역 접근을 위해 window에 할당)
window.currentCaptcha = '';
let isCaptchaVerified = false;

// 보안문자 생성 함수
function generateCaptcha() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ'; // 영어만! 숫자 제외!
    currentCaptcha = '';
    for (let i = 0; i < 6; i++) {
        currentCaptcha += chars.charAt(Math.floor(Math.random() * chars.length));
    }

    const canvas = document.getElementById('captcha-canvas');
    const ctx = canvas.getContext('2d');

    // 배경 그리기
    ctx.fillStyle = '#4a7c59';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 노이즈 추가
    for (let i = 0; i < 100; i++) {
        ctx.fillStyle = `rgba(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255}, 0.3)`;
        ctx.fillRect(Math.random() * canvas.width, Math.random() * canvas.height, 2, 2);
    }

    // 문자 그리기
    ctx.font = 'bold 40px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    for (let i = 0; i < currentCaptcha.length; i++) {
        ctx.save();
        const x = 50 + i * 40;
        const y = 50;
        ctx.translate(x, y);
        ctx.rotate((Math.random() - 0.5) * 0.4);
        ctx.fillStyle = `hsl(${Math.random() * 60 + 150}, 70%, ${Math.random() * 20 + 70}%)`;
        ctx.fillText(currentCaptcha[i], 0, 0);
        ctx.restore();
    }

    // 방해선 추가
    for (let i = 0; i < 3; i++) {
        ctx.strokeStyle = `rgba(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255}, 0.4)`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(Math.random() * canvas.width, Math.random() * canvas.height);
        ctx.lineTo(Math.random() * canvas.width, Math.random() * canvas.height);
        ctx.stroke();
    }

    // 입력 필드 초기화
    document.getElementById('captcha-input').value = '';
    updateCaptchaButton();
}

// 입력값에 따라 버튼 활성화/비활성화
function updateCaptchaButton() {
    const input = document.getElementById('captcha-input');
    const btn = document.getElementById('captcha-submit-btn');

    if (input.value.trim().length > 0) {
        btn.style.background = '#4f46e5';
        btn.style.color = 'white';
        btn.style.cursor = 'pointer';
    } else {
        btn.style.background = '#d0d0d0';
        btn.style.color = '#666';
        btn.style.cursor = 'not-allowed';
    }
}

// 보안문자 검증
function verifyCaptcha() {
    const input = document.getElementById('captcha-input').value.trim().toUpperCase();

    if (!input) {
        showAlert('문자를 입력해주세요.', 'warning');
        return;
    }

    if (input === currentCaptcha) {
        isCaptchaVerified = true;

        // 세션 동안 보안문자 통과 여부 저장
        sessionStorage.setItem('captchaVerified', 'true');

        document.getElementById('captcha-overlay').classList.add('captcha-hidden');
        showAlert('인증되었습니다! 좌석을 선택해주세요.', 'success');

        // [v2] 캡차 단계 종료 및 좌석 선택 단계 시작
        recordStageExit('captcha', { status: 'verified' });
        recordStageEntry('seat');
    } else {
        showAlert('문자가 일치하지 않습니다. 다시 시도해주세요.', 'error');
        generateCaptcha();
        // 자동 수집에 맡깁니다.
    }
}

// 입력 필드 변화 감지
document.addEventListener('DOMContentLoaded', () => {
    const captchaInput = document.getElementById('captcha-input');
    if (captchaInput) {
        captchaInput.addEventListener('input', updateCaptchaButton);
    }
});

// 페이지 로드 시 보안문자 팝업 표시 (항상 표시)
window.addEventListener('load', () => {
    // 세션 기록과 상관없이 무조건 보안문자 표시
    isCaptchaVerified = false; // 검증 상태 초기화

    // 오버레이 표시 및 캡차 생성
    setTimeout(() => {
        document.getElementById('captcha-overlay').classList.remove('captcha-hidden');
        generateCaptcha();
    }, 500);
});

// 페이지 진입 시 플로우 데이터 확인
const flowData = getFlowData();
if (!flowData || !flowData.performanceId) {
    navigateTo('index.html');
}

// *** 페이지 진입 시마다 좌석 선택 초기화 (뒤로가기 시 좌석 보류 없음) ***
console.log('Before clearSeatSelections:', flowData.selectedSeats);
clearSeatSelections();
console.log('After clearSeatSelections:', getFlowData().selectedSeats);

// 뒤로가기로 돌아왔을 때 페이지 강제 새로고침
window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        // bfcache에서 페이지가 복원된 경우 (뒤로가기)
        console.log('Page restored from bfcache - reloading to clear seats');
        window.location.reload();
    }
});

const selectedSeats = [];
const maxSeats = 4;
const seatsByGrade = {};

// 공연 정보 표시
document.getElementById('perf-info').textContent = flowData.performanceTitle;

// 등급별 색상 정의
const gradeColors = {
    'VIP': { bg: '#F1F5F9', border: '#E61E51', color: '#E61E51', hoverBg: '#E61E51' },
    'VIP석': { bg: '#F1F5F9', border: '#E61E51', color: '#E61E51', hoverBg: '#E61E51' },
    'R': { bg: '#FFF3E0', border: '#FF9800', color: '#FF9800', hoverBg: '#FF9800' },
    'R석': { bg: '#FFF3E0', border: '#FF9800', color: '#FF9800', hoverBg: '#FF9800' },
    'S': { bg: '#E8F5E9', border: '#4CAF50', color: '#4CAF50', hoverBg: '#4CAF50' },
    'S석': { bg: '#E8F5E9', border: '#4CAF50', color: '#4CAF50', hoverBg: '#4CAF50' },
    'A': { bg: '#E3F2FD', border: '#2196F3', color: '#2196F3', hoverBg: '#2196F3' },
    'A석': { bg: '#E3F2FD', border: '#2196F3', color: '#2196F3', hoverBg: '#2196F3' },
    '프리미엄석': { bg: '#F3E5F5', border: '#9C27B0', color: '#9C27B0', hoverBg: '#9C27B0' },
    '지정석': { bg: '#E0F2F1', border: '#009688', color: '#009688', hoverBg: '#009688' },
    '자유석': { bg: '#FFF9C4', border: '#FBC02D', color: '#F57F17', hoverBg: '#FBC02D' },
    '스탠딩': { bg: '#FFCCBC', border: '#FF5722', color: '#FF5722', hoverBg: '#FF5722' },
    '성인': { bg: '#E8EAF6', border: '#3F51B5', color: '#3F51B5', hoverBg: '#3F51B5' },
    '청소년': { bg: '#E1F5FE', border: '#03A9F4', color: '#03A9F4', hoverBg: '#03A9F4' }
};

// 좌석 그리드 생성 (여러 등급 통합)
async function createSeatGrid() {
    const grid = document.getElementById('seat-grid');
    const response = await fetch('data/performances.json');
    const data = await response.json();
    const perf = data.performances.find(p => p.id === flowData.performanceId);

    // 등급별로 구역 생성
    perf.grades.forEach((grade, gradeIdx) => {
        // [FIX] JSON 데이터에 따라 name 또는 grade 키 사용
        const gradeName = grade.name || grade.grade;

        const gradeSection = document.createElement('div');
        gradeSection.style.marginBottom = 'var(--spacing-xl)';

        // 등급 헤더
        const gradeHeader = document.createElement('div');
        const gradeColor = gradeColors[gradeName] || gradeColors['A'];
        gradeHeader.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-md); padding: var(--spacing-sm) var(--spacing-md); background: ${gradeColor.bg}; border-left: 4px solid ${gradeColor.border}; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: var(--spacing-md);">
                    <div style="width: 24px; height: 24px; background: ${gradeColor.border}; border-radius: 4px;"></div>
                    <span style="font-weight: 700; color: ${gradeColor.color}; font-size: 18px;">${gradeName.endsWith('석') ? gradeName : gradeName + '석'}</span>
                </div>
                <span style="font-weight: 700; color: ${gradeColor.color}; font-size: 20px;">${formatPrice(grade.price)}</span>
            </div>
        `;
        gradeSection.appendChild(gradeHeader);

        // 좌석 그리드
        const seatContainer = document.createElement('div');
        seatContainer.style.background = 'rgba(255,255,255,0.02)';
        seatContainer.style.padding = 'var(--spacing-md)';
        seatContainer.style.borderRadius = 'var(--border-radius)';

        const rows = gradeIdx === 0 ? ['A', 'B', 'C'] : gradeIdx === 1 ? ['D', 'E', 'F'] : gradeIdx === 2 ? ['G', 'H'] : ['I', 'J'];
        const seatsPerRow = 32;
        const aislePosition = 16;

        rows.forEach((row) => {
            const rowContainer = document.createElement('div');
            rowContainer.style.cssText = 'display: flex; gap: 2px; margin-bottom: 2px; justify-content: center; align-items: center;';

            // 행 레이블 (왼쪽)
            const leftLabel = document.createElement('div');
            leftLabel.textContent = row;
            leftLabel.style.cssText = 'width: 25px; text-align: center; color: #999; font-weight: 700; font-size: 12px;';
            rowContainer.appendChild(leftLabel);

            // 좌석들
            for (let col = 1; col <= seatsPerRow; col++) {
                if (col === aislePosition + 1) {
                    const aisle = document.createElement('div');
                    aisle.style.width = '16px';
                    rowContainer.appendChild(aisle);
                }

                const seatId = `${gradeName}-${row}${col}`;
                const seat = document.createElement('div');

                const isTaken = Math.random() > 0.75;
                seat.className = 'seat ' + (isTaken ? 'taken' : 'available');
                seat.textContent = col;
                seat.dataset.seat = seatId;
                seat.dataset.grade = gradeName;
                seat.dataset.price = grade.price;
                seat.dataset.row = row;
                seat.dataset.col = col;
                seat.style.cssText = `width: 14px; height: 14px; line-height: 14px; font-size: 7px;`;

                if (!isTaken) {
                    // 등급별 색상 적용
                    seat.style.background = gradeColor.bg;
                    seat.style.borderColor = gradeColor.border;
                    seat.style.color = gradeColor.color;

                    seat.onmouseenter = function (event) {
                        if (!this.classList.contains('selected')) {
                            this.style.background = gradeColor.hoverBg;
                            this.style.color = 'white';
                        }
                        // Track hover event for ML analysis
                        if (typeof trackHover === 'function') {
                            trackHover(event, {
                                target: 'seat',
                                seat_id: seatId,
                                grade: gradeName,
                                row: row,
                                col: col
                            });
                        }
                    };
                    seat.onmouseleave = function () {
                        if (!this.classList.contains('selected')) {
                            this.style.background = gradeColor.bg;
                            this.style.color = gradeColor.color;
                        }
                    };

                    seat.onclick = function (event) { toggleSeat(seatId, gradeName, grade.price, this, event); };
                }

                rowContainer.appendChild(seat);
            }

            // 행 레이블 (오른쪽)
            const rightLabel = document.createElement('div');
            rightLabel.textContent = row;
            rightLabel.style.cssText = 'width: 25px; text-align: center; color: #999; font-weight: 700; font-size: 12px;';
            rowContainer.appendChild(rightLabel);

            seatContainer.appendChild(rowContainer);
        });

        gradeSection.appendChild(seatContainer);
        grid.appendChild(gradeSection);
    });
}

function toggleSeat(seatId, grade, price, element, event) {
    const idx = selectedSeats.findIndex(s => s.id === seatId);

    if (idx > -1) {
        // 선택 해제
        selectedSeats.splice(idx, 1);
        element.classList.remove('selected');
        element.classList.add('available');

        const gradeColor = gradeColors[grade];
        element.style.color = gradeColor.color;
        element.style.boxShadow = 'none';

        // 자동 수집에 맡깁니다.
    } else {
        // 선택 시도 - 35% 확률로 이미 선택된 좌석으로 변경
        if (Math.random() < 0.35) {
            // 다른 사람이 먼저 선택한 것처럼 처리
            showSeatAlert('선택 불가', '이미 선택된 좌석입니다.<br>다른 좌석을 선택해주세요.');

            // 좌석을 매진 상태로 변경
            element.classList.remove('available');
            element.classList.add('taken');
            element.onclick = null;
            element.onmouseenter = null;
            element.onmouseleave = null;
            element.style.background = '';
            element.style.color = '';
            element.style.boxShadow = '';

            // 자동 수집에 맡깁니다.
            return;
        }

        // 선택 성공
        if (selectedSeats.length >= maxSeats) {
            showAlert(`최대 ${maxSeats}개까지 선택할 수 있습니다.`, 'warning');
            return;
        }
        selectedSeats.push({ id: seatId, grade, price });
        element.classList.remove('available');
        element.classList.add('selected');

        element.style.background = '#E61E51';
        element.style.color = 'white';
        element.style.boxShadow = '0 4px 12px rgba(255, 61, 127, 0.4)';

        // 자동 수집에 맡깁니다.
    }

    updateSummary();
}

function updateSummary() {
    const listDiv = document.getElementById('selected-seats-list');
    const seatsSpan = document.getElementById('summary-seats');
    const priceSpan = document.getElementById('summary-price');
    const sectionSpan = document.getElementById('summary-section');
    const nextBtn = document.getElementById('next-btn');

    if (selectedSeats.length > 0) {
        // 등급별로 그룹화
        const gradeGroups = {};
        selectedSeats.forEach(seat => {
            if (!gradeGroups[seat.grade]) {
                gradeGroups[seat.grade] = [];
            }
            gradeGroups[seat.grade].push(seat);
        });

        // 등급별로 표시
        listDiv.innerHTML = Object.keys(gradeGroups).map(grade => {
            const seats = gradeGroups[grade];
            const gradeColor = gradeColors[grade];
            return seats.map(s => {
                const seatLabel = String(s.id).includes('-') ? s.id.split('-').pop() : s.id;
                return `<div style="display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; background: ${gradeColor.border}; color: white; border-radius: 16px; margin: 4px; font-weight: 600; font-size: 13px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
                        <span style="font-size: 10px; opacity: 0.9;">${grade}</span>
                        <span>${seatLabel}</span>
                    </div>`;
            }).join('');
        }).join('');

        // 등급 요약
        const gradesSummary = Object.keys(gradeGroups).map(g => `${g}석 ${gradeGroups[g].length}개`).join(', ');
        sectionSpan.textContent = gradesSummary;

        seatsSpan.textContent = selectedSeats.length + '석';

        // 총 가격 계산
        const totalPrice = selectedSeats.reduce((sum, seat) => sum + seat.price, 0);
        priceSpan.textContent = formatPrice(totalPrice);
        nextBtn.style.display = 'block';
    } else {
        listDiv.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: var(--spacing-lg) 0;">좌석을 선택해주세요<br><small>(최대 4석)</small></p>';
        sectionSpan.textContent = '-';
        seatsSpan.textContent = '-';
        priceSpan.textContent = '-';
        nextBtn.style.display = 'none';
    }
}

function confirmSeats() {
    if (selectedSeats.length === 0) {
        showAlert('좌석을 선택해주세요.', 'warning');
        return;
    }

    // 선택된 좌석 정보를 플로우에 저장
    const totalSeatPrice = selectedSeats.reduce((sum, seat) => sum + seat.price, 0);

    updateFlowData({
        selectedSeats: selectedSeats.map(s => s.id),
        seatDetails: selectedSeats, // 등급, 가격 정보 포함
        seatPrice: totalSeatPrice // 총 좌석 가격
    });

    // 메타데이터 업데이트
    updateMetadata({
        final_seats: selectedSeats.map(s => s.id),
        seat_grades: selectedSeats.map(s => ({ seat: s.id, grade: s.grade, price: s.price }))
    });

    recordStageExit('seat', {
        selected_seats: selectedSeats.map(s => s.id),
        seat_details: selectedSeats
    });

    navigateTo('discount.html');
}

createSeatGrid();

// --- Custom Alert Modal Logic ---
function showSeatAlert(title, message, callback) {
    const overlay = document.getElementById('alert-overlay');
    const titleEl = document.getElementById('alert-modal-title');
    const msgEl = document.getElementById('alert-modal-message');
    const btn = document.getElementById('alert-confirm-btn');

    if (overlay && titleEl && msgEl && btn) {
        titleEl.textContent = title;
        msgEl.innerHTML = message; // Allow HTML for newlines

        // Remove old event listeners by cloning
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);

        newBtn.addEventListener('click', () => {
            overlay.classList.remove('active');
            if (callback) callback();
        });

        overlay.classList.add('active');
    } else {
        // Fallback
        alert(message);
        if (callback) callback();
    }
}

// Close alert on click outside
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('alert-overlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    }
});
