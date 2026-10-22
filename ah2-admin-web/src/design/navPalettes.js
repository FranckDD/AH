// Palette du menu lateral par espace. La valeur est la classe posee sur le cadre (AppShell) ; vide = bleu nuit
// par defaut (jetons nav-* de style.css). Les couleurs sont dans navPalettes.css.
export const NAV_PALETTES = {
    night: '',
    forest: 'nav-palette-forest',
    slate: 'nav-palette-slate',
    lagoon: 'nav-palette-lagoon',
    ember: 'nav-palette-ember',
    violet: 'nav-palette-violet',
};

export function navPaletteClass(name) {
    return NAV_PALETTES[name] ?? '';
}

// Palette de l'espace d'apres le role de l'utilisateur (cadre partage MainLayout) : admin et promoteur ardoise,
// laboratoire lagon, toxicologie braise, stock-control violet ; role inconnu : bleu nuit.
const PALETTE_BY_ROLE = {
    admin: 'slate',
    promoteur: 'slate',
    laborantin: 'lagoon',
    toxicomanager: 'ember',
    psychologist: 'ember',
    spiritualcounsellor: 'ember',
    assistant: 'ember',
    stockcontroller: 'violet',
};

export function paletteForRole(role) {
    return PALETTE_BY_ROLE[String(role || '').toLowerCase()] || 'night';
}
