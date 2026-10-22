// Périodes affichées par le calendrier des rotations (fonctions pures, testées).
// Les semaines commencent le lundi (convention locale, comme le calendrier des rendez-vous).
import dayjs from 'dayjs';

const FORMAT = 'YYYY-MM-DD';

function mondayOf(date) {
    return date.subtract((date.day() + 6) % 7, 'day');
}

// Plage à charger pour la vue affichée : une semaine (lundi au dimanche) ou la grille complète du mois.
// Toute vue inconnue est traitée comme la semaine.
export function periodRange(view, anchor) {
    if (view === 'month') {
        const monthStart = anchor.startOf('month');
        const monthEnd = monthStart.endOf('month');
        return {
            start: mondayOf(monthStart).format(FORMAT),
            end: monthEnd.add(6 - ((monthEnd.day() + 6) % 7), 'day').format(FORMAT),
        };
    }
    const monday = mondayOf(anchor);
    return { start: monday.format(FORMAT), end: monday.add(6, 'day').format(FORMAT) };
}

// Avance (+1) ou recule (-1) d'une semaine ou d'un mois.
export function shiftAnchor(view, anchor, direction) {
    return view === 'month' ? anchor.add(direction, 'month') : anchor.add(direction * 7, 'day');
}

// Les sept dates (AAAA-MM-JJ) d'une semaine à partir de son lundi.
export function weekDays(mondayString) {
    return Array.from({ length: 7 }, (_, i) => dayjs(mondayString).add(i, 'day').format(FORMAT));
}
