// Urgence de renouvellement d'une prescription medicamenteuse selon sa date de fin (fonction pure, testee).
// Memes seuils que l'ancien ecran : echue, aujourd'hui ou 3 jours au plus = rouge, 7 jours = orange,
// 14 jours = information, au-dela = vert. Les jours sont comptes en jours calendaires locaux.
const DAY_MS = 24 * 60 * 60 * 1000;

export function endUrgency(endDate, now = new Date()) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(endDate || '');
    if (!m) return null;
    const end = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    if (Number.isNaN(end.getTime())) return null;
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const days = Math.round((end - today) / DAY_MS);

    if (days < 0) return { kind: 'expired', tone: 'neutral', days };
    if (days === 0) return { kind: 'today', tone: 'danger', days };
    if (days <= 3) return { kind: 'soon', tone: 'danger', days };
    if (days <= 7) return { kind: 'soon', tone: 'warning', days };
    if (days <= 14) return { kind: 'soon', tone: 'info', days };
    return { kind: 'later', tone: 'success', days };
}
