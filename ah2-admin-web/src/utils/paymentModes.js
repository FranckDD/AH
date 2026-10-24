// Modes de paiement : liste officielle (codes stables du serveur, table payment_modes) et libelles lisibles.
// Les formulaires stockent le CODE (especes, orange_money, ...). Les anciennes lignes portent du texte libre
// (« Espèces », « Cash », « Mobile Money », vide) : modeLabel les rend lisibles avec la meme normalisation que
// le serveur (utils/cash_rules.py, normalize_mode).
import { ref, computed } from 'vue';
// Imports relatifs : ce module est aussi charge par les tests node (sans l'alias @). La passerelle HTTP
// est chargee a la demande dans loadPaymentModes (elle depend du routeur et du magasin d'authentification).
import i18n from '../i18n.js';

const mode = (code, source) => Object.freeze({ code, source });

// Repli hors ligne (ou si GET /payment-modes echoue) : la liste officielle de depart.
export const FALLBACK_PAYMENT_MODES = Object.freeze([
    mode('especes', 'physical'),
    mode('orange_money', 'operator_statement'),
    mode('mtn_money', 'operator_statement'),
    mode('autre_mobile', 'operator_statement'),
]);

export const CASH_MODE = 'especes';
export const UNCLASSIFIED_MODE = 'non_classe';

const fold = (raw) => String(raw)
    .normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[_-]/g, ' ').split(/\s+/).filter(Boolean).join(' ');

// Texte libre -> code officiel ; null si vide ; 'non_classe' si inconnu (comme le serveur).
export function normalizeMode(raw) {
    if (raw === null || raw === undefined) return null;
    const s = fold(raw);
    if (!s) return null;
    if (s === 'especes' || s === 'espece' || s === 'cash') return CASH_MODE;
    if (s.includes('orange')) return 'orange_money';
    if (s.includes('mtn')) return 'mtn_money';
    if (s.includes('mobile')) return 'autre_mobile';
    return UNCLASSIFIED_MODE;
}

const KNOWN = new Set([...FALLBACK_PAYMENT_MODES.map((m) => m.code), UNCLASSIFIED_MODE]);

// Libelle lisible d'une valeur stockee (code ou ancien texte). Une ancienne valeur inconnue (Virement, Cheque)
// reste affichee telle quelle : elle dit mieux ce qui s'est passe que « non classe ».
export function modeLabel(raw) {
    const code = normalizeMode(raw);
    if (code === null) return i18n.global.t('paymentModes.non_classe');
    if (code === UNCLASSIFIED_MODE && fold(raw) !== 'non classe') return String(raw).trim();
    return KNOWN.has(code) ? i18n.global.t(`paymentModes.${code}`) : String(raw);
}

// Modes actifs du serveur ({code, label, is_active, sort_order}) ; repli sur la liste figee hors ligne.
export async function loadPaymentModes() {
    try {
        const { default: api } = await import('@/services/api');
        const rows = (await api.get('/payment-modes')).data;
        if (!Array.isArray(rows)) return FALLBACK_PAYMENT_MODES;
        const active = rows
            .filter((m) => m && m.is_active !== false && typeof m.code === 'string')
            .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
            .map((m) => mode(m.code, m.code === CASH_MODE ? 'physical' : 'operator_statement'));
        return active.length ? active : FALLBACK_PAYMENT_MODES;
    } catch {
        return FALLBACK_PAYMENT_MODES;
    }
}

// Pour les formulaires : la liste figee tout de suite, remplacee par celle du serveur des qu'elle arrive.
// Chaque entree porte son libelle traduit (`label`).
export function usePaymentModes() {
    const list = ref(FALLBACK_PAYMENT_MODES);
    loadPaymentModes().then((rows) => { list.value = rows; });
    // computed : le libelle suit la langue choisie
    return computed(() => list.value.map((m) => ({ ...m, label: modeLabel(m.code) })));
}
