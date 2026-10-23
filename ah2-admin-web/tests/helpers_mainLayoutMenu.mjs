// Lecture de la configuration du menu de MainLayout.vue (données seulement, sans composants) pour les tests.
import { readFileSync } from 'node:fs';

const ROLE_VALUES = {
    ADMIN: 'admin', PSYCHOLOGIST: 'Psychologist', SPIRITUAL: 'SpiritualCounsellor', TOXICO_MANAGER: 'ToxicoManager',
    ASSISTANT: 'Assistant', LABORANTIN: 'laborantin', PROMOTEUR: 'promoteur', STOCK_CONTROLLER: 'StockController',
    PRODUCTION_MANAGER: 'ProductionManager',
};

export function readMainLayout() {
    return readFileSync(new URL('../src/components/layout/MainLayout.vue', import.meta.url), 'utf8');
}

export function parseMenuItems(src = readMainLayout()) {
    const start = src.indexOf('const menuItems = [');
    const end = src.indexOf('\n];', start);
    const body = src.slice(start, end);
    const blocks = body.match(/\{[^{}]*\}/g) || [];
    return blocks.map((b) => {
        const get = (re) => (b.match(re) || [])[1];
        const roles = (get(/roles:\s*\[([^\]]*)\]/) || '').split(',').map((r) => r.trim().replace('ROLES.', '')).filter(Boolean).map((k) => ROLE_VALUES[k]);
        return {
            path: get(/path:\s*'([^']+)'/),
            labelKey: get(/labelKey:\s*'([^']+)'/),
            group: get(/group:\s*'([^']+)'/),
            adminHidden: /adminHidden:\s*true/.test(b) || undefined,
            separator: /separator:\s*true/.test(b) || undefined,
            roles,
        };
    });
}

// Meme logique que authStore.hasRole (comparaison sans casse).
export const hasRoleFor = (role) => (allowed) => (allowed || []).some((r) => (r || '').toLowerCase() === role.toLowerCase());
