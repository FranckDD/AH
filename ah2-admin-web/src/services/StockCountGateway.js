import api from '@/services/api';

// Une fonction par route du routeur /stock-counts. Corps STRICTS cote serveur (extra=forbid, entiers stricts) :
// les quantites et l'intervalle partent en nombres JS, jamais en chaines.
const clean = (params) => Object.fromEntries(
    Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== ''),
);

export const StockCountGateway = {
    // { id, started_at, scope, products: [{ id, name }] } : aucune quantite (a l'aveugle)
    async start(scope = 'tous') { return (await api.post('/stock-counts', { scope })).data; },
    // clientNow : heure du navigateur a l'envoi (instant ISO), le serveur corrige le decalage d'horloge
    // lines = [{ product_id, counted_qty, observation?, counted_at? (ISO UTC de la saisie) }] ; renvoie le detail revele
    async submit(id, lines, clientNow) { return (await api.post(`/stock-counts/${id}/submit`, { client_now: clientNow, lines })).data; },
    async abandon(id) { return (await api.post(`/stock-counts/${id}/abandon`)).data; },
    // { interval_days, counts, products: [{ product_id, name, last_counted_at, days_since, status }] }
    async getStatus() { return (await api.get('/stock-counts/status')).data; },
    async getSettings() { return (await api.get('/stock-counts/settings')).data; },
    async setInterval(intervalDays) { return (await api.put('/stock-counts/settings', { interval_days: intervalDays })).data; },
    // dateFrom / dateTo : AAAA-MM-JJ locales ; status : en_cours | valide | abandonne ; mine : mes comptages seulement
    // renvoie { items, total, limit, offset }
    async list({ dateFrom, dateTo, status, limit, offset, mine } = {}) {
        return (await api.get('/stock-counts', {
            params: clean({ date_from: dateFrom, date_to: dateTo, status, limit, offset, mine }),
        })).data;
    },
    async get(id) { return (await api.get(`/stock-counts/${id}`)).data; },
};
