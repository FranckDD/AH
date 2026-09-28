// src/stores/notificationStore.js
import { defineStore } from 'pinia';
import { NotificationGateway } from '@/services/NotificationGateway';

const POLL_INTERVAL_MS = 30000;

export const useNotificationStore = defineStore('notification', {
    state: () => ({
        notifications: [],
        seenIds: new Set(),
        pollTimer: null,
        popupQueue: [],
    }),

    getters: {
        unreadCount: (state) => state.notifications.length,
        unreadNotifications: (state) => state.notifications,
    },

    actions: {
        async fetchUnread() {
            try {
                const res = await NotificationGateway.listUnread();
                const fresh = res.data || [];
                // Nouvelle notification = jamais vue depuis le demarrage du store
                // (pas juste "pas dans la derniere liste recue", pour ne jamais
                // re-declencher un popup deja affiche une fois).
                const newlySeen = fresh.filter((n) => !this.seenIds.has(n.id));
                newlySeen.forEach((n) => {
                    this.seenIds.add(n.id);
                    this.popupQueue.push(n);
                });
                this.notifications = fresh;
            } catch (err) {
                console.error('Erreur chargement notifications:', err);
            }
        },

        startPolling() {
            if (this.pollTimer) return;
            this.fetchUnread();
            this.pollTimer = setInterval(() => this.fetchUnread(), POLL_INTERVAL_MS);
        },

        stopPolling() {
            if (this.pollTimer) {
                clearInterval(this.pollTimer);
                this.pollTimer = null;
            }
        },

        async markRead(id) {
            try {
                await NotificationGateway.markRead(id);
                this.notifications = this.notifications.filter((n) => n.id !== id);
            } catch (err) {
                console.error('Erreur marquage notification lue:', err);
            }
        },

        popNextPopup() {
            return this.popupQueue.shift() || null;
        },
    },
});
