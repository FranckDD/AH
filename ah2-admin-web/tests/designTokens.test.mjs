import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../src/style.css', import.meta.url), 'utf8');

const tokens = {};
for (const m of css.matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) {
    tokens[m[1]] = m[2];
}

function luminance(hex) {
    const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
    const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a, b) {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
}

function color(name) {
    if (name === 'white') return '#ffffff';
    assert.ok(tokens[name], `jeton --color-${name} absent de style.css`);
    return tokens[name];
}

const TONES = ['danger', 'warning', 'success', 'info', 'neutral'];

test('tous les jetons attendus sont déclarés', () => {
    const expected = [
        'brand-50', 'brand-100', 'brand-500', 'brand-600', 'brand-700', 'brand-800',
        'nav-800', 'nav-900', 'nav-text',
        'ink', 'ink-muted', 'page',
        ...TONES.flatMap((t) => [`tone-${t}-bg`, `tone-${t}-text`, `tone-${t}-border`]),
    ];
    for (const name of expected) color(name);
});

test('les autres jetons de forme et de police sont déclarés', () => {
    for (const name of ['--radius-card', '--radius-control', '--shadow-card', '--font-brand', '--text-base-app']) {
        assert.ok(css.includes(`${name}:`), `${name} absent de style.css`);
    }
});

// [texte, fond, seuil minimal]
const pairs = [
    ['nav-text', 'nav-800', 4.5],
    ['nav-text', 'nav-900', 4.5],
    ['white', 'brand-600', 4.5],
    ['white', 'brand-700', 4.5],
    ['brand-700', 'white', 4.5],
    ['brand-700', 'brand-50', 4.5],
    ['ink', 'white', 4.5],
    ['ink', 'page', 4.5],
    ['ink-muted', 'white', 4.5],
    ['ink-muted', 'page', 4.5],
    ...TONES.map((t) => [`tone-${t}-text`, `tone-${t}-bg`, 4.5]),
    ...TONES.map((t) => [`tone-${t}-text`, 'white', 4.5]),
    // composants et bordures : 3:1 suffit
    ...TONES.map((t) => [`tone-${t}-border`, 'white', 1.2]),
    ['brand-500', 'nav-900', 3],
    ['brand-600', 'white', 3],
];

for (const [fg, bg, min] of pairs) {
    test(`contraste ${fg} sur ${bg} >= ${min}`, () => {
        const ratio = contrast(color(fg), color(bg));
        assert.ok(ratio >= min, `${fg} (${color(fg)}) sur ${bg} (${color(bg)}) = ${ratio.toFixed(2)} < ${min}`);
    });
}

test('style.css ne contient que des ajouts : les règles historiques restent en place', () => {
    assert.ok(css.includes("@import 'tailwindcss';"));
    assert.ok(css.includes('border-color: var(--color-gray-200, currentcolor);'));
    assert.ok(css.includes('overflow: hidden;'));
});

test('le texte de base 15-16 px est limité au conteneur .app-refonte', () => {
    assert.match(css, /\.app-refonte\s*\{[^}]*font-size:\s*var\(--text-base-app\)/);
    const body = css.match(/html,\s*body,\s*#app\s*\{[^}]*\}/)[0];
    assert.ok(!body.includes('font-size'), 'la taille de base ne doit pas être posée globalement');
});
