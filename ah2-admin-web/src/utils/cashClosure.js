// Regles pures de l'ecran de cloture de caisse (testees par tests/cashClosureContract.test.mjs).

// La cloture n'est possible qu'en ligne et file d'envoi PowerSync vide : une vente ou un retrait saisi hors
// ligne et pas encore envoye manquerait dans l'attendu. Entree : l'etat de useConnectionStatus.
export function queueBlockReason({ state, pending } = {}) {
    if (state === 'offline') return 'cashClosure.blocked_offline';
    if (state === 'error') return 'cashClosure.blocked_error';
    if (state === 'syncing' || state === 'pending' || (Number(pending) || 0) > 0) return 'cashClosure.blocked_pending';
    return null;
}

// Le serveur refuse (422) un ecart non nul sans commentaire et nomme le mode concerne
// (utils/cash_rules.py, require_comment_if_gap). Renvoie ce code, sinon null.
export function commentRequiredMode(detail) {
    if (typeof detail !== 'string') return null;
    const m = detail.match(/Commentaire obligatoire pour l'ecart du mode (\S+)/);
    return m ? m[1] : null;
}

// Montant saisi -> chaine decimale positive (2 decimales au plus), sinon null. Espaces retires, virgule acceptee.
export function normalizeAmount(value) {
    if (value === null || value === undefined) return null;
    const s = String(value).replace(/\s/g, '').replace(',', '.');
    return /^\d+(\.\d{1,2})?$/.test(s) ? s : null;
}

// Montant de regularisation : signe (+ ou -), non nul, 2 decimales au plus -> chaine, sinon null.
export function normalizeSignedAmount(value) {
    if (value === null || value === undefined) return null;
    const s = String(value).replace(/\s/g, '');
    const negative = s.startsWith('-');
    const abs = normalizeAmount(s.replace(/^[+-]/, ''));
    if (abs === null || Number(abs) === 0) return null;
    return negative ? `-${abs}` : abs;
}

// Corps du comptage : un element par mode, montant en chaine, commentaire seulement s'il est non vide.
export function buildCounts(modes, form) {
    return modes.map((m) => {
        const entry = form[m.code] || {};
        const item = { mode: m.code, counted: normalizeAmount(entry.counted) };
        const comment = (entry.comment || '').trim();
        if (comment) item.comment = comment;
        return item;
    });
}

// Ecart dit par un mot (jamais la couleur seule). difference = compte - attendu, chaine Decimal ou null.
export function gapWords(difference) {
    if (difference === null || difference === undefined) return { key: 'cashClosure.gap_not_counted', amount: null };
    const s = String(difference).trim();
    const negative = s.startsWith('-');
    const abs = negative ? s.slice(1) : s;
    if (Number(abs) === 0) return { key: 'cashClosure.gap_none', amount: '0' };
    return { key: negative ? 'cashClosure.gap_under' : 'cashClosure.gap_over', amount: abs };
}

// ---------- ecran de revue (promoteur / admin, tache 10) ----------

// Date LOCALE AAAA-MM-JJ (jamais via UTC : apres 23 h, la date UTC serait celle du lendemain ou de la veille).
export function localDateISO(d) {
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const nonZero = (d) => d !== null && d !== undefined && Number(d) !== 0;

// Etats d'une cloture lus sur son detail : non declaree (automatique, rien compte), ecart, commentaire
// manquant (drapeau comment_missing pose par le serveur, seule source de verite).
export function closureFlags(closure) {
    const lines = closure?.lines || [];
    return {
        undeclared: closure?.kind === 'auto',
        withGap: lines.some((l) => nonZero(l.difference)),
        commentMissing: closure?.comment_missing === true,
    };
}

// Montant Decimal (chaine) -> "1 500,50 FCFA" sans passer par Number : les decimales sont gardees.
export function formatAmountFcfa(value) {
    if (value === null || value === undefined || value === '') return '';
    const s = String(value).trim();
    const m = s.match(/^(-?)(\d+)(?:\.(\d+))?$/);
    if (!m) return s;
    const [, sign, int, dec] = m;
    const grouped = int.replace(/^0+(?=\d)/, '').replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    const cents = (dec || '').slice(0, 2).replace(/0+$/, '');
    return `${sign}${grouped}${cents ? `,${cents.padEnd(2, '0')}` : ''} FCFA`;
}

// Les especes sont le seul mode compte physiquement : jamais desactivables (le serveur refuse aussi).
export function canDeactivateMode(code) {
    return code !== 'especes';
}

// Annulations de ventes de la periode et regularisations approuvees appliquees a cette periode, lues dans le
// detail d'une cloture. Lecture defensive : cles absentes = listes vides, noms de champs avec repli.
const pickFirst = (o, keys) => {
    for (const k of keys) if (o && o[k] !== undefined && o[k] !== null && o[k] !== '') return o[k];
    return '';
};

export function closureCancellations(detail) {
    const list = Array.isArray(detail?.cancellations) ? detail.cancellations : [];
    return list.map((c, i) => ({
        key: String(pickFirst(c, ['transaction_id', 'id', 'reference']) || i),
        author: pickFirst(c, ['cancelled_by_name', 'author_name', 'author', 'cancelled_by']),
        amount: pickFirst(c, ['amount', 'total', 'paid_amount']),
        justification: pickFirst(c, ['justification', 'reason', 'cancel_justification']),
        reference: pickFirst(c, ['transaction_id', 'reference', 'sale_reference', 'id']),
    }));
}

export function closureAppliedCorrections(detail) {
    const list = Array.isArray(detail?.corrections_applied) ? detail.corrections_applied : [];
    return list.map((c, i) => ({
        key: String(pickFirst(c, ['id']) || i),
        mode: pickFirst(c, ['mode', 'mode_code']),
        amount: pickFirst(c, ['amount_delta', 'amount']),
        reason: pickFirst(c, ['reason']),
    }));
}
