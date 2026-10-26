// Palette du menu lateral par espace. La valeur est la classe posee sur le cadre (AppShell) ; vide = bleu nuit
// par defaut (jetons nav-* de style.css). Les couleurs sont dans navPalettes.css.
export const NAV_PALETTES = {
    night: '',
    forest: 'nav-palette-forest',
    slate: 'nav-palette-slate',
    lagoon: 'nav-palette-lagoon',
    ember: 'nav-palette-ember',
    violet: 'nav-palette-violet',
    gold: 'nav-palette-gold',
    rose: 'nav-palette-rose',
    indigo: 'nav-palette-indigo',
    burgundy: 'nav-palette-burgundy',
    olive: 'nav-palette-olive',
    sky: 'nav-palette-sky',
};

export function navPaletteClass(name) {
    return NAV_PALETTES[name] ?? '';
}

// Palette du menu d'apres le role de l'utilisateur : une couleur par role (le chef infirmier est un infirmier).
// admin ardoise, promoteur or, secretaire foret (SecretaireLayout), medecin bleu nuit, infirmier rose,
// laboratoire lagon, psychologue indigo, conseiller spirituel bordeaux, toxicologie braise, assistant olive,
// stock-control violet, production ciel ; role inconnu : bleu nuit.
const PALETTE_BY_ROLE = {
    admin: 'slate',
    promoteur: 'gold',
    secretaire: 'forest',
    medecin: 'night',
    nurse: 'rose',
    laborantin: 'lagoon',
    psychologist: 'indigo',
    spiritualcounsellor: 'burgundy',
    toxicomanager: 'ember',
    assistant: 'olive',
    stockcontroller: 'violet',
    productionmanager: 'sky',
};

export function paletteForRole(role) {
    return PALETTE_BY_ROLE[String(role || '').toLowerCase()] || 'night';
}
