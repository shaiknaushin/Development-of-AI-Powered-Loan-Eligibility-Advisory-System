function connectWebSocket() {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user'));
    if (!token || !user) return;

    const socket = io("ws://127.0.0.1:8000", { auth: { userId: user.id } });

    socket.on('connect', () => showNotification('Real-time connection established.'));
    socket.on('disconnect', () => showNotification('Connection lost.', true));
    socket.on('notification', (data) => {
        showNotification(data.message);
        if (data.report_url || data.message.includes('review')) {
            if (window.location.pathname.includes('customer.html')) loadUserApplications();
            if (window.location.pathname.includes('admin.html')) loadAdminApplications();
        }
    });
}

function showNotification(message, isError = false) {
    const container = document.getElementById('notifications');
    const notification = document.createElement('div');
    notification.className = `notification ${isError ? 'error' : ''}`;
    notification.textContent = message;
    container.appendChild(notification);
    speakText(message);
    setTimeout(() => notification.remove(), 5000);
}

if (window.location.pathname.includes('customer.html') || window.location.pathname.includes('admin.html')) {
    connectWebSocket();
}

