// Date du jour AAAA-MM-JJ en heure LOCALE (toISOString() donne la date UTC,
// fausse en soiree/debut de journee selon le fuseau).
export function todayLocalISO(d = new Date()) {
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
