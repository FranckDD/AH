// Date du jour AAAA-MM-JJ en heure LOCALE (toISOString() donne la date UTC,
// fausse en soiree/debut de journee selon le fuseau).
// Date affichee jj/mm/aaaa (meme format partout, quelle que soit la langue du navigateur). Une date seule
// (AAAA-MM-JJ) n'est pas decalee par le fuseau ; une valeur illisible est rendue telle quelle.
export function formatDateDMY(value) {
    if (!value) return '';
    const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return `${m[3]}/${m[2]}/${m[1]}`;
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    const p = (n) => String(n).padStart(2, '0');
    return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`;
}

export function todayLocalISO(d = new Date()) {
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

// Date et heure affichees jj/mm/aaaa HH:MM en heure locale ; une valeur illisible est rendue telle quelle.
export function formatDateTimeDMY(value) {
    if (!value) return '';
    const d = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    const p = (n) => String(n).padStart(2, '0');
    return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
