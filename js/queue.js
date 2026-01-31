// queue.js - 대기열 페이지

loadLogFromSession();
logStageEntry('queue');

let currentPosition = Math.floor(Math.random() * 80) + 20; // 20-100
const totalQueue = 8000;
const waitTime = 3000 + Math.random() * 2000; // 3-5초
const initialPosition = currentPosition;

document.getElementById('queue-position').textContent = currentPosition;
document.getElementById('queue-total').textContent = `전체 대기: ${totalQueue.toLocaleString()} 명`;

// 대기번호 줄어드는 애니메이션
const updateInterval = 200;
const decreaseAmount = Math.ceil(currentPosition / (waitTime / updateInterval));

const countdownInterval = setInterval(() => {
    currentPosition = Math.max(0, currentPosition - decreaseAmount);
    document.getElementById('queue-position').textContent = currentPosition;

    if (currentPosition === 0) {
        clearInterval(countdownInterval);
    }
}, updateInterval);

setTimeout(() => {
    clearInterval(countdownInterval);
    currentPosition = 0;
    document.getElementById('queue-position').textContent = '통과!';

    logStageExit('queue', {
        initial_position: initialPosition,
        final_position: 0,
        total_queue: totalQueue,
        wait_duration_ms: Math.floor(waitTime),
        position_updates: [
            { position: 0, status: 'ready', timestamp: getISOTimestamp() }
        ]
    });

    setTimeout(() => {
        navigateTo('seat_select.html');
    }, 1000);
}, waitTime);
