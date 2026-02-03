// section_select.js - 구역 선택 페이지

loadLogFromSession();
logStageEntry('section');
enableMouseTracking();

// 뒤로가기로 돌아온 경우 좌석 정보 초기화
clearSeatSelections();

const flowData = getFlowData();
let selectedSection = '';
let selectedGrade = '';

if (!flowData) {
    navigateTo('index.html');
}

// 요약 정보 표시
document.getElementById('summary-perf').textContent = flowData.performanceTitle;
document.getElementById('summary-datetime').textContent = `${formatDateKorean(flowData.selectedDate)} ${flowData.selectedTime}`;

// 구역 버튼 생성
async function loadGrades() {
    const response = await fetch('data/performances.json');
    const data = await response.json();
    const perf = data.performances.find(p => p.id === flowData.performanceId);

    const gradesDiv = document.getElementById('grade-options');
    gradesDiv.innerHTML = perf.grades.map(grade => `
        <div class="card" style="cursor: pointer; transition: all 0.3s;" onclick="selectGrade('${grade.name}', ${grade.price})">
          <h3 style="color: var(--primary-color);">${grade.name}</h3>
          <p style="font-size: 24px; font-weight: 700; margin-top: var(--spacing-sm);">${formatPrice(grade.price)}</p>
          <p style="color: var(--text-secondary); margin-top: var(--spacing-sm);">잔여석 있음</p>
        </div>
      `).join('');

    // 간단한 SVG 구역 맵
    drawSectionMap(perf.grades);
}

function drawSectionMap(grades) {
    const svg = document.getElementById('section-map');
    const width = svg.clientWidth;
    const height = 400;

    // 무대
    svg.innerHTML = `
        <rect x="${width / 2 - 100}" y="20" width="200" height="30" fill="#FF3D7F" rx="4"/>
        <text x="${width / 2}" y="40" text-anchor="middle" fill="white" font-weight="bold">무대</text>
      `;

    // 구역들
    grades.forEach((grade, idx) => {
        const y = 80 + idx * 80;
        const rect = `<rect x="${width / 2 - 150}" y="${y}" width="300" height="60" fill="#E3F2FD" stroke="#2196F3" stroke-width="2" rx="8" style="cursor: pointer;" onclick="selectSection('${grade.name}-L', '${grade.name}', ${grade.price})"/>`;
        const text = `<text x="${width / 2}" y="${y + 35}" text-anchor="middle" font-size="16" font-weight="bold" fill="#1976D2">${grade.name}</text>`;
        svg.innerHTML += rect + text;
    });
}

function selectSection(section, grade, price) {
    selectedSection = section;
    selectedGrade = grade;

    updateFlowData({
        selectedSection: section,
        selectedGrade: grade,
        seatPrice: price
    });

    document.getElementById('summary-section').textContent = grade;
    document.getElementById('next-btn').style.display = 'block';

    trackClick(event, { section, grade, price });
}

function selectGrade(grade, price) {
    selectSection(`${grade}-L`, grade, price);
}

function goToSeatSelect() {
    if (!selectedSection) {
        showAlert('구역을 선택해주세요.', 'warning');
        return;
    }

    logStageExit('section', {
        final_section: selectedSection,
        final_grade: selectedGrade,
        clicks: []
    });

    disableMouseTracking();
    navigateTo('seat_select.html');
}

loadGrades();
