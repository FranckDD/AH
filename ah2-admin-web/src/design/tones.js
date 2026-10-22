// Tonalités d'état de la refonte UX : rouge = urgent/erreur, orange = attention,
// vert = fait/validé, bleu = information, gris = neutre.
export const TONES = ['danger', 'warning', 'success', 'info', 'neutral'];

export function isTone(value) {
    return typeof value === 'string' && TONES.includes(value);
}

// Classes Tailwind issues des jetons de style.css ; repli sur 'neutral', jamais d'exception.
export function toneClasses(tone) {
    const t = isTone(tone) ? tone : 'neutral';
    return `bg-tone-${t}-bg text-tone-${t}-text border-tone-${t}-border`;
}
