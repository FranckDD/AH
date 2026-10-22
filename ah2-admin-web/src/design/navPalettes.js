// Palette du menu lateral par espace. La valeur est la classe posee sur le cadre (AppShell) ; vide = bleu nuit
// par defaut (jetons nav-* de style.css). Les couleurs sont dans navPalettes.css.
export const NAV_PALETTES = {
    night: '',
    forest: 'nav-palette-forest',
};

export function navPaletteClass(name) {
    return NAV_PALETTES[name] ?? '';
}
