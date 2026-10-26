// Boutons pleins en dégradé : la couleur de base (déjà validée en contraste avec le blanc) vers la même couleur assombrie.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buttonClasses } from '../src/utils/ui.js';

const css = readFileSync(new URL('../src/style.css', import.meta.url), 'utf8');
const tokens = Object.fromEntries([...css.matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)].map((m) => [m[1], m[2]]));
const lum = (hex) => {
    const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratioWhite = (hex) => 1.05 / (lum(hex) + 0.05);

const FILLED = { brand: 'brand-600', primary: 'action-600', success: 'action-success', info: 'action-info', danger: 'tone-danger-solid', pharma: 'tab-pharma', hospital: 'tab-hospital', lab: 'tab-lab', record: 'tab-record', toxico: 'tab-toxico', spirit: 'tab-spirit' };

test('chaque bouton plein a un dégradé diagonal avec sa couleur de base en haut et un repli de couleur unie', () => {
    for (const [variant, base] of Object.entries(FILLED)) {
        const c = buttonClasses(variant, 'md');
        assert.match(c, /bg-linear-to-br/, variant);
        assert.ok(` ${c} `.includes(` from-${base} `), `${variant} : départ ${base}`);
        assert.match(c, /\bto-/, `${variant} : arrivée`);
        assert.ok(` ${c} `.includes(` bg-${base} `), `${variant} : couleur de repli`);
        assert.match(c, /text-white/, variant);
    }
});

test('les boutons secondaire et discret restent sans dégradé', () => {
    for (const variant of ['secondary', 'ghost']) assert.doesNotMatch(buttonClasses(variant, 'md'), /bg-linear/, variant);
});

test('le texte blanc reste lisible sur la couleur de base de chaque bouton plein (le bas du dégradé est plus sombre)', () => {
    for (const [variant, base] of Object.entries(FILLED)) {
        assert.ok(ratioWhite(tokens[base]) >= 4.5, `${variant} : ${ratioWhite(tokens[base]).toFixed(2)}`);
    }
    assert.ok(ratioWhite(tokens['brand-800']) >= 4.5);
    // le texte du bouton secondaire (indigo foncé) reste lisible sur blanc et sur son fond de survol
    assert.ok(1.05 / (lum(tokens['action-700']) + 0.05) >= 4.5, 'action-700 sur blanc');
    const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };
    assert.ok(ratio(tokens['action-700'], tokens['action-50']) >= 4.5, 'action-700 sur action-50');
});

test('le dégradé assombrit peu (10 %) : les boutons restent clairs et modernes, avec une ombre douce', () => {
    for (const variant of Object.keys(FILLED)) {
        const c = buttonClasses(variant, 'md');
        assert.doesNotMatch(c, /black_(?:[2-9]\d)%/, `${variant} : fin de dégradé trop sombre`);
        assert.match(c, /shadow-sm/, variant);
    }
});

test('connexion et tableau de bord admin/promoteur gardent le vert sarcelle en dégradé (demande de l’utilisateur)', () => {
    const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
    assert.match(read('../src/views/LoginView.vue'), /<AppButton type="submit" variant="brand" size="lg"/);
    const dash = read('../src/views/dashboards/DashboardOverview.vue');
    assert.equal((dash.match(/variant="brand"/g) || []).length, 3, 'Filtrer, Encaisser un paiement et Ouvrir les rapports (promoteur)');
    assert.equal((dash.match(/variant="brandOutline"/g) || []).length, 6, 'les quatre boutons de contour + deux actions du promoteur');
    assert.doesNotMatch(dash, /variant="secondary"/);
    assert.match(buttonClasses('brand', 'md'), /bg-linear-to-br from-brand-600/);
    assert.match(buttonClasses('brandOutline', 'md'), /border-brand-600/);
});
