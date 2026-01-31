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

    listDiv.innerHTML = filtered.map(perf => `
        <div class="performance-card" onclick="selectPerformance('${perf.id}')">
          <div class="performance-card-image" style="background: linear-gradient(135deg, ${getRandomGradient()})">
            <div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-size: 48px;">
              ${getCategoryIcon(perf.category)}
            </div>
          </div>
          <div class="performance-card-content">
            <span class="performance-card-category">${getCategoryName(perf.category)}</span>
            <h3 class="performance-card-title">${perf.title}</h3>
            <p class="performance-card-venue">📍 ${perf.venue}</p>
            <p class="performance-card-date">📅 ${formatDateKorean(perf.dates[0])} ${perf.dates.length > 1 ? '외 ' + (perf.dates.length - 1) + '일' : ''}</p>
          </div>
        </div>
      `).join('');
}

function getCategoryIcon(category) {
    const icons = {
        concert: '🎤',
        musical: '🎭',
        sports: '⚽',
        exhibition: '🖼️'
    };
    return icons[category] || '🎫';
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
