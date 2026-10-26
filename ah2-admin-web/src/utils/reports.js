// Utilitaires purs de la page Rapports (testes dans tests/reportsContract.test.mjs).
// Dates seules : AAAA-MM-JJ construites a partir des parties LOCALES, jamais par conversion UTC.

export const PAGE_SIZE = 50;
export const MAX_PERIOD_DAYS = 366;

// Disposition A : une carte par indicateur, quatre blocs. 'people' = carte 12 (nouveaux patients et
// consultations), 'sales' = carte 13 (ventes comparees a la periode precedente).
export const CARD_BLOCKS = Object.freeze([
    { key: 'money', cards: ['collected', 'cash_gaps', 'withdrawals_and_cancellations', 'discounts', 'per_secretary'] },
    { key: 'products', cards: ['sold_vs_received', 'stock_count', 'low_stock'] },
    { key: 'production', cards: ['batches', 'bottles', 'loss_and_cost'] },
    { key: 'growth', cards: ['people', 'sales'] },
]);

export const ANOMALY_KINDS = Object.freeze([
    'cloture_auto', 'ecart_caisse', 'commentaire_manquant', 'ventes_annulees', 'prix_different', 'sortie_autre',
    'lot_hors_tolerance', 'lot_trop_long', 'ecart_expedie_recu', 'comptage_retard', 'comptage_jamais',
    'ajustement_en_attente', 'ajustement_caisse_en_attente', 'intrant_sous_seuil',
]);

const pad = (n) => String(n).padStart(2, '0');
export function localISO(d) {
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function parseLocal(s) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s || ''));
    return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}

// preset : today | 7d | 30d | custom ({ from, to } fournis tels quels)
export function periodRange(preset, now = new Date(), custom = {}) {
    if (preset === 'custom') return { from: custom.from || '', to: custom.to || '' };
    const back = preset === '7d' ? 6 : preset === '30d' ? 29 : 0;
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - back);
    return { from: localISO(start), to: localISO(now) };
}

// Cle i18n de l'erreur d'une periode libre, '' si elle est valide.
export function customPeriodError(from, to) {
    const a = parseLocal(from);
    const b = parseLocal(to);
    if (!a || !b) return 'reports.period.err_missing';
    if (b < a) return 'reports.period.err_order';
    const days = Math.round((Date.UTC(b.getFullYear(), b.getMonth(), b.getDate())
        - Date.UTC(a.getFullYear(), a.getMonth(), a.getDate())) / 86400000) + 1;
    if (days > MAX_PERIOD_DAYS) return 'reports.period.err_too_long';
    return '';
}

export function formatLocalDate(s, locale = 'fr') {
    const d = parseLocal(s);
    if (!d) return s || '';
    return d.toLocaleDateString(locale === 'en' ? 'en-GB' : 'fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
}

// Instant ISO (as_of) affiche en heure locale du poste.
export function formatInstant(iso, locale = 'fr') {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toLocaleString(locale === 'en' ? 'en-GB' : 'fr-FR', {
        day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
}

// Montant venu du serveur en chaine a 2 decimales : groupement des milliers par espace, virgule, FCFA.
// Aucun passage par un flottant : les grands montants restent exacts.
export function formatMoney(value) {
    if (value === null || value === undefined || value === '') return '';
    const s = String(value).trim();
    const m = s.match(/^(-?)(\d+)(?:\.(\d+))?$/);
    if (!m) return s;
    const [, sign, int, dec] = m;
    const grouped = int.replace(/^0+(?=\d)/, '').replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    const cents = (dec || '').slice(0, 2);
    const shown = /^0*$/.test(cents) ? '' : `,${cents.padEnd(2, '0')}`;
    return `${sign}${grouped}${shown} FCFA`;
}

export function formatCount(n) {
    if (n === null || n === undefined || n === '') return '';
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

// Donnees d'une carte dans la reponse /reports/overview.
export function cardData(overview, id) {
    if (!overview) return null;
    if (id === 'people') {
        const np = overview.growth?.new_patients;
        const cs = overview.growth?.consultations;
        if (!np || !cs) return null;
        return { id, period: np.period, source: `${np.source} ; ${cs.source}`, new_patients: np, consultations: cs };
    }
    for (const block of ['money', 'products', 'production', 'growth']) {
        const c = overview[block]?.[id];
        if (c) return c;
    }
    return null;
}

export function currentStateOf(card) {
    return card && card.current_state ? { current: true, asOf: card.as_of || '' } : { current: false, asOf: '' };
}

export function controlState(control) {
    return control && Array.isArray(control.items) && control.items.length ? 'watch' : 'nothing';
}

export function seriesValues(series) {
    return (series || []).map((p) => Number(p.value));
}

export function partialIndex(series) {
    const list = series || [];
    const i = list.length - 1;
    return i >= 0 && list[i].partial ? i : -1;
}

export function pageRange(offset, count, total) {
    if (!count || !total) return { from: 0, to: 0, total: total || 0 };
    return { from: offset + 1, to: offset + count, total };
}

const BOUNDS = { cancelled_sales_threshold: [1, 1000], adjustment_pending_days: [1, 365] };

// Erreurs de saisie des reglages : { champ: cle i18n } ; {} si tout est valide.
export function settingsErrors(form) {
    const out = {};
    for (const [k, [lo, hi]] of Object.entries(BOUNDS)) {
        const raw = String(form?.[k] ?? '').trim();
        const n = Number(raw);
        if (!/^\d+$/.test(raw) || !Number.isInteger(n) || n < lo || n > hi) out[k] = `reports.settings.err_${k}`;
    }
    return out;
}

// Meme regle que la garde du routeur (router/index.js) : meta.roles absent = permis ; sinon le role de
// l'utilisateur (casse ignoree) doit y figurer, l'admin passe toujours. resolved = router.resolve(link).
export function linkAllowed(resolved, userRole) {
    if (!resolved || !resolved.matched || !resolved.matched.length) return false;
    const roles = resolved.meta?.roles;
    if (!roles) return true;
    const role = String(userRole || '').toLowerCase();
    if (!role) return false;
    return role === 'admin' || roles.map((r) => String(r).toLowerCase()).includes(role);
}

// Libelle d'un point du controle quotidien dans la langue courante : construit a partir du type et du detail
// stockes (le texte francais du serveur ne sert que de repli pour un type inconnu).
export function anomalyLabel(item, t, te) {
    const kind = item?.kind;
    if (!kind || !te(`reports.anomalies.${kind}`)) return item?.label || '';
    const d = item.detail || {};
    const params = {
        mode: d.mode ?? '', difference: d.difference ?? '', count: d.count ?? d.total ?? '', threshold: d.threshold ?? '',
        id: d.transaction_id ?? d.request_id ?? d.correction_id ?? item.ref ?? '', quantity: d.quantity ?? '',
        batch: d.batch_number ?? item.ref ?? '', days: d.days ?? '', name: d.intrant_name ?? item.ref ?? '',
    };
    return t(`reports.anomalies.${kind}`, params, Number(params.quantity) || 1);
}

// Source d'une carte : traduite par identifiant de carte, texte serveur en repli.
export function cardSource(cardId, card, t, te) {
    return te(`reports.sources.${cardId}`) ? t(`reports.sources.${cardId}`) : (card?.source || '');
}
