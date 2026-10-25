// Regles pures du comptage du stock (testees). Aucune quantite du systeme ici : seules les saisies du compteur.
export const MAX_COUNT = 10000000;

// Saisie d'un champ de comptage : { blank } (non compte), { value } (entier JS) ou { error }.
export function parseCount(raw) {
    if (raw === null || raw === undefined) return { blank: true };
    if (typeof raw === 'number') {
        return Number.isInteger(raw) && raw >= 0 && raw <= MAX_COUNT ? { value: raw } : { error: true };
    }
    const s = String(raw).trim();
    if (!s) return { blank: true };
    if (!/^\d+$/.test(s)) return { error: true };
    const n = Number(s);
    return n <= MAX_COUNT ? { value: n } : { error: true };
}

// Lignes a envoyer : seuls les produits saisis. null si une saisie est invalide (envoi bloque).
export function buildLines(products, form) {
    const out = [];
    for (const p of products || []) {
        const entry = form?.[p.id];
        const parsed = parseCount(entry?.qty);
        if (parsed.error) return null;
        if (parsed.blank) continue;
        const line = { product_id: p.id, counted_qty: parsed.value };
        const obs = (entry?.observation || '').trim();
        if (obs) line.observation = obs;
        if (entry?.countedAt) line.counted_at = entry.countedAt;
        out.push(line);
    }
    return out;
}

// Frequence de comptage (admin) : entier de 1 a 365, sinon null.
export function parseInterval(raw) {
    const s = String(raw ?? '').trim();
    if (!/^\d+$/.test(s)) return null;
    const n = Number(s);
    return n >= 1 && n <= 365 ? n : null;
}

// Heure de comptage d'une ligne : un INSTANT (pas une date de calendrier), envoye en ISO UTC avec Z.
// Seule conversion ISO autorisee dans le comptage : la regle du projet vise les dates AAAA-MM-JJ.
export function instantISO(d = new Date()) {
    return d.toISOString();
}

const GAP_KEYS = { plus: 'stockCount.gap_plus', moins: 'stockCount.gap_moins', aucun: 'stockCount.gap_none' };
export const gapKey = (kind) => GAP_KEYS[kind] || 'stockCount.gap_none';
export const movementsKey = (n) => (!n ? null : (n === 1 ? 'stockCount.movements_one' : 'stockCount.movements_many'));

// Horodatages du serveur : ISO avec +00:00 explicite, affiches en heure locale.
// lang = langue active de vue-i18n (useI18n().locale.value), meme convention que AppShell / SystemLogs.
const dateLocale = (lang) => (lang === 'en' ? 'en-GB' : 'fr-FR');
export const formatLocalDate = (iso, lang) => (iso ? new Date(iso).toLocaleDateString(dateLocale(lang)) : '');
export const formatLocalDateTime = (iso, lang) => (iso ? new Date(iso).toLocaleString(dateLocale(lang), { dateStyle: 'short', timeStyle: 'short' }) : '');
