// Notes du conseiller spirituel : formulaire vide et validation (fonctions pures, testees).
// Les valeurs d'erreur sont des cles i18n (spiritualNotes.err_*).
export const VERSE_MAX = 120;
export const CONTENT_MAX = 5000;
export const MAX_DAYS_BACK = 365;

export const CHECK_FIELDS = ['counsel', 'prayer', 'verse_read', 'discussion', 'text_given', 'qa'];

export function emptyNote(todayIso) {
    return {
        meeting_date: todayIso,
        counsel: false, prayer: false, verse_read: false, discussion: false, text_given: false, qa: false,
        no_one_spoke: false,
        verse_reference: '',
        content: '',
    };
}

// Numero de jour d'une date AAAA-MM-JJ (calcul en UTC : pas de decalage d'heure d'ete) ; null si illisible.
function dayNumber(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    if (!m) return null;
    const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    if (new Date(t).getUTCMonth() !== Number(m[2]) - 1) return null; // 31 fevrier, etc.
    return Math.round(t / 86400000);
}

// originalDate (facultatif) : date deja enregistree d'une note en modification ; si elle est inchangee,
// la limite des 365 jours dans le passe ne s'applique pas (une ancienne note reste modifiable).
export function validateNote(form, todayIso, originalDate) {
    const errors = {};
    const unchanged = !!originalDate && form?.meeting_date === originalDate;
    const day = dayNumber(form?.meeting_date);
    const today = dayNumber(todayIso);
    if (day === null) errors.meeting_date = 'spiritualNotes.err_date_required';
    else if (today !== null && day > today) errors.meeting_date = 'spiritualNotes.err_date_future';
    else if (!unchanged && today !== null && today - day > MAX_DAYS_BACK) errors.meeting_date = 'spiritualNotes.err_date_old';
    if (String(form?.verse_reference || '').length > VERSE_MAX) errors.verse_reference = 'spiritualNotes.err_verse_long';
    if (String(form?.content || '').length > CONTENT_MAX) errors.content = 'spiritualNotes.err_content_long';
    return { ok: Object.keys(errors).length === 0, errors };
}
