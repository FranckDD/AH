// Lecture de la table de routes (src/router/index.js) sans charger les composants : chemin complet + roles autorises.
import { readFileSync } from 'node:fs';

const ROLE_VALUES = {
    ADMIN: 'admin', PROMOTEUR: 'promoteur', PSYCHOLOGIST: 'Psychologist', SPIRITUAL: 'SpiritualCounsellor',
    TOXICO_MANAGER: 'ToxicoManager', ASSISTANT: 'Assistant', STOCK_CONTROLLER: 'StockController',
    PRODUCTION_MANAGER: 'ProductionManager', LABORANTIN: 'laborantin', MEDECIN: 'medecin', NURSE: 'nurse', SECRETAIRE: 'secretaire',
};

export function readRouterSource() {
    return readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8');
}

function rolesOf(chunk) {
    const m = chunk.match(/roles:\s*\[([^\]]*)\]/);
    if (!m) return null;
    return m[1].split(',').map((r) => r.trim()).filter(Boolean).map((r) => {
        const lit = r.match(/^'([^']+)'$/);
        return lit ? lit[1] : ROLE_VALUES[r.replace('ROLES.', '')];
    });
}

// Retourne [{ path: '/dashboard/stock', roles: [...]|null }]. Les enfants heritent du prefixe du parent
// (/dashboard, /medical, /secretariat) ; les enfants de "labo" ont le prefixe /dashboard/labo.
export function parseRoutes(src = readRouterSource()) {
    const body = src.slice(src.indexOf('const routes = ['), src.indexOf('const router = createRouter'));
    const re = /path:\s*'([^']*)'/g;
    const hits = [];
    let m;
    while ((m = re.exec(body))) hits.push({ raw: m[1], at: m.index });
    const out = [];
    let top = '';
    let nested = '';
    hits.forEach((h, i) => {
        const chunk = body.slice(h.at, i + 1 < hits.length ? hits[i + 1].at : body.length);
        if (h.raw.startsWith('/')) {
            if (/^\/(dashboard|medical|secretariat)$/.test(h.raw)) { top = h.raw; nested = ''; }
            else { top = ''; nested = ''; }
            if (!/^\/(dashboard|medical|secretariat)$/.test(h.raw) || /roles:/.test(chunk)) {
                out.push({ path: h.raw, roles: rolesOf(chunk) });
            }
            return;
        }
        if (!top) return;
        if (h.raw === 'labo') { nested = 'labo/'; out.push({ path: `${top}/labo`, roles: rolesOf(chunk), group: true }); return; }
        if (nested && h.raw === 'toxico') nested = '';
        const rel = h.raw === '' ? '' : `/${nested}${h.raw}`;
        out.push({ path: `${top}${rel}`, roles: rolesOf(chunk) });
    });
    return out;
}

export const routeAllows = (route, role) => {
    if (!route) return false;
    if (!route.roles) return true;
    const r = String(role).toLowerCase();
    return r === 'admin' || route.roles.some((x) => String(x).toLowerCase() === r);
};
