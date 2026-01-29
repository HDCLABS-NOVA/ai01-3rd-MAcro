// 로그인 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 탭 전환
    const tabs = document.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.form-panel');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;
            
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            panels.forEach(p => p.classList.remove('active'));
            document.getElementById(`${target}-panel`).classList.add('active');
        });
    });
});

// URL 파라미터로 탭 전환 함수 (Jinja에서 호출)
function switchToRegisterTab() {
    const registerTab = document.querySelector('[data-tab="register"]');
    if (registerTab) {
        registerTab.click();
    }
}
