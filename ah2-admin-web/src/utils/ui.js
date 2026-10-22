// Utilitaires purs de la bibliothèque components/ui (testés dans tests/uiComponents.test.mjs).

// Ids des textes d'aide/erreur à relier à un contrôle via aria-describedby.
export function describedBy(id, { help, error } = {}) {
    if (!id) return undefined;
    const ids = [];
    if (error) ids.push(`${id}-error`);
    if (help) ids.push(`${id}-help`);
    return ids.length ? ids.join(' ') : undefined;
}

const BUTTON_BASE =
    'inline-flex items-center justify-center gap-2 rounded-control border font-medium transition-colors ' +
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 ' +
    'disabled:cursor-not-allowed disabled:opacity-60';

const BUTTON_VARIANTS = {
    primary: 'bg-brand-600 text-white border-transparent hover:bg-brand-700',
    secondary: 'bg-white text-brand-700 border-brand-600 hover:bg-brand-50',
    danger: 'bg-tone-danger-text text-white border-transparent hover:opacity-90',
    ghost: 'bg-transparent text-ink-muted border-transparent hover:bg-tone-neutral-bg',
    // Boutons d'action de rubrique : meme couleur que l'onglet correspondant de la fiche patient.
    pharma: 'bg-tab-pharma text-white border-transparent hover:opacity-90',
    hospital: 'bg-tab-hospital text-white border-transparent hover:opacity-90',
    lab: 'bg-tab-lab text-white border-transparent hover:opacity-90',
    record: 'bg-tab-record text-white border-transparent hover:opacity-90',
    toxico: 'bg-tab-toxico text-white border-transparent hover:opacity-90',
    spirit: 'bg-tab-spirit text-white border-transparent hover:opacity-90',
};

// Zones tactiles >= 44 px (min-h-11) ; un peu plus compactes à partir de lg pour la souris.
const BUTTON_SIZES = {
    md: 'min-h-11 px-4 py-2 text-base lg:min-h-10',
    lg: 'min-h-12 px-6 py-3 text-base',
};

export function buttonClasses(variant = 'primary', size = 'md') {
    const v = BUTTON_VARIANTS[variant] ?? BUTTON_VARIANTS.primary;
    const s = BUTTON_SIZES[size] ?? BUTTON_SIZES.md;
    return `${BUTTON_BASE} ${v} ${s}`;
}

const ALIGNS = ['left', 'center', 'right'];

// Classes écrites en toutes lettres : Tailwind ne détecte pas les noms construits dynamiquement.
const ALIGN_CLASSES = { left: 'text-left', center: 'text-center', right: 'text-right' };

export function alignClass(align) {
    return ALIGN_CLASSES[align] ?? ALIGN_CLASSES.left;
}

// Colonnes de ResponsiveTable : [{ key, label, align?, class? }] ; les entrées sans clé sont ignorées.
export function normalizeColumns(columns) {
    if (!Array.isArray(columns)) return [];
    return columns
        .filter((c) => c && typeof c === 'object' && typeof c.key === 'string' && c.key)
        .map((c) => ({
            key: c.key,
            label: c.label ?? c.key,
            align: ALIGNS.includes(c.align) ? c.align : 'left',
            class: c.class ?? '',
        }));
}

// Piege de focus d'un panneau (touche Tab) : indice suivant dans la liste des elements focalisables,
// avec retour au debut ou a la fin. -1 si rien n'est focalisable ; un indice inconnu (-1) entre au debut
// (Tab) ou a la fin (Maj+Tab).
export function nextFocusIndex(index, count, backwards) {
    if (!count) return -1;
    if (index < 0 || index >= count) return backwards ? count - 1 : 0;
    return backwards ? (index - 1 + count) % count : (index + 1) % count;
}
