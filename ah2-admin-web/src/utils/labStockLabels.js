// Libelles du stock labo : retournent une cle i18n (+ parametres), ou { key: null, raw }
// pour une valeur inconnue -> jamais un chemin de cle brut affiche a l'ecran.
const ORIGINS = ['signalement', 'seuil', 'peremption'];
const STATUSES = ['a_commander', 'commande', 'recu', 'annule'];
const LEVELS = ['bientot_fini', 'fini'];

const pick = (known, prefix, value, emptyRaw) => {
    if (known.includes(value)) return { key: `${prefix}.${value}` };
    return { key: null, raw: value || emptyRaw };
};

export const requestOriginLabel = (origin) => pick(ORIGINS, 'labStock.origin', origin, '?');
export const requestStatusLabel = (status) => pick(STATUSES, 'labStock.status', status, '?');
export const levelLabel = (level) => pick(LEVELS, 'labStock.level', level, '');

export function labNotificationLabel(type, payload) {
    const p = payload || {};
    const product = p.product_name || '?';
    switch (type) {
    case 'lab_stock_signal': {
        const suffix = LEVELS.includes(p.level) ? p.level : 'other';
        return { key: `notifications.lab_stock_signal_${suffix}`, params: { product } };
    }
    case 'lab_stock_low':
        return { key: 'notifications.lab_stock_low',
            params: { product, quantity: p.quantity ?? '?', threshold: p.alert_threshold ?? '?' } };
    case 'lab_stock_expiry':
        return { key: 'notifications.lab_stock_expiry',
            params: { product, lot: p.lot_number || '?', days: p.days_left ?? '?' } };
    case 'lab_stock_received':
        return { key: 'notifications.lab_stock_received',
            params: { supplier: p.supplier || '?', count: Array.isArray(p.products) ? p.products.length : 0 } };
    case 'lab_stock_count_reminder':
        if (p.days_since === undefined || p.days_since === null) return { key: 'notifications.lab_stock_count_reminder_never', params: {} };
        return { key: 'notifications.lab_stock_count_reminder', params: { days: p.days_since ?? '?' } };
    default:
        return { key: 'notifications.lab_stock_other', params: { type: String(type || '?') } };
    }
}
