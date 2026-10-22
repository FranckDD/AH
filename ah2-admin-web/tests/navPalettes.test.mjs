// Palettes du menu lateral par espace : contrastes, branchement dans AppShell et choix par espace.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { NAV_PALETTES, navPaletteClass } from '../src/design/navPalettes.js';

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const css = read('../src/style.css');
const paletteCss = read('../src/design/navPalettes.css');
const shell = read('../src/components/layout/AppShell.vue');

const tokens = Object.fromEntries([...css.matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)].map((m) => [m[1], m[2]]));
const lum = (hex) => {
    const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };

// {classe: {nav-800, nav-900}}
const palettes = Object.fromEntries([...paletteCss.matchAll(/\.(nav-palette-[a-z0-9-]+)\s*\{([^}]*)\}/g)].map((m) => [
    m[1], Object.fromEntries([...m[2].matchAll(/--color-(nav-(?:700|800|900)):\s*(#[0-9a-fA-F]{6})/g)].map((x) => [x[1], x[2]])),
]));

test('chaque palette nommée a sa classe CSS avec les deux fonds du menu', () => {
    for (const [name, cls] of Object.entries(NAV_PALETTES)) {
        if (!cls) continue;
        assert.ok(palettes[cls], `${name} : classe ${cls} absente de navPalettes.css`);
        assert.ok(palettes[cls]['nav-700'] && palettes[cls]['nav-800'] && palettes[cls]['nav-900'], `${name} : fonds incomplets`);
    }
});

test('chaque palette garde le texte du menu lisible (4,5:1) et le filet actif visible (3:1)', () => {
    const all = { night: { 'nav-700': tokens['nav-700'], 'nav-800': tokens['nav-800'], 'nav-900': tokens['nav-900'] }, ...Object.fromEntries(Object.entries(NAV_PALETTES).filter(([, c]) => c).map(([n, c]) => [n, palettes[c]])) };
    for (const [name, p] of Object.entries(all)) {
        for (const bg of ['nav-700', 'nav-800', 'nav-900']) {
            assert.ok(ratio(tokens['nav-text'], p[bg]) >= 4.5, `${name} : texte sur ${bg} ${ratio(tokens['nav-text'], p[bg]).toFixed(2)}`);
            // le filet de l'entree active se pose sur son propre fond (nav-800), pas sur le bas du degrade
            if (bg !== 'nav-700') assert.ok(ratio(tokens['brand-500'], p[bg]) >= 3, `${name} : filet actif sur ${bg}`);
        }
        assert.ok(ratio('#ffffff', p['nav-800']) >= 4.5, `${name} : texte blanc survolé sur nav-800`);
    }
});

test('navPaletteClass : palette connue, repli sur le bleu nuit par défaut', () => {
    assert.equal(navPaletteClass('night'), '');
    assert.equal(navPaletteClass('forest'), 'nav-palette-forest');
    assert.equal(navPaletteClass('inconnue'), '');
    assert.equal(navPaletteClass(undefined), '');
});

test('AppShell pose la classe de la palette et la propose en prop (défaut night)', () => {
    assert.match(shell, /navPaletteClass\(palette\)/);
    assert.match(shell, /palette: \{ type: String, default: 'night' \}/);
    assert.match(css, /@import '\.\/design\/navPalettes\.css';/);
});

test('chaque espace choisit sa palette : médical bleu nuit (défaut), secrétariat forêt', () => {
    assert.doesNotMatch(read('../src/components/layout/MedicalLayout.vue'), /palette=/);
    assert.match(read('../src/components/layout/SecretaireLayout.vue'), /palette="forest"/);
});

test('le menu est un dégradé vertical nav-900 vers nav-700, avec le survol (nav-800) plus sombre que le bas du menu', () => {
    assert.match(shell, /bg-linear-to-b from-nav-900 to-nav-700/);
    const all = { night: { 'nav-700': tokens['nav-700'], 'nav-800': tokens['nav-800'], 'nav-900': tokens['nav-900'] }, ...Object.fromEntries(Object.entries(NAV_PALETTES).filter(([, c]) => c).map(([n, c]) => [n, palettes[c]])) };
    for (const [name, p] of Object.entries(all)) {
        assert.ok(lum(p['nav-900']) < lum(p['nav-800']) && lum(p['nav-800']) < lum(p['nav-700']), `${name} : ordre 900 < 800 < 700`);
        assert.ok(ratio(p['nav-700'], p['nav-800']) >= 1.2, `${name} : survol distinct du bas du dégradé`);
    }
});
