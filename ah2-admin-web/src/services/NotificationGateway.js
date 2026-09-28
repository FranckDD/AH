// src/services/NotificationGateway.js
import api from './api';

export const NotificationGateway = {
    async listUnread() {
        return api.get('/notifications', { params: { status: 'unread' } });
    },
    async markRead(id) {
        return api.post(`/notifications/${id}/read`);
    },
};
