// Menu et routeur doivent dire la meme chose : aucune entree de menu vers une route interdite au role,
// aucune route ouverte a un role sans entree de menu (sauf ecarts voulus, listes ci-dessous).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseRoutes, routeAllows } from './helpers_routerRoutes.mjs';
import { parseMenuItems } from './helpers_mainLayoutMenu.mjs';

const routes = parseRoutes();
const byPath = new Map(routes.map((r) => [r.path, r]));
const menu = parseMenuItems();

test('menu admin/labo/toxico/stock : chaque entree a une route que ses roles peuvent ouvrir', () => {
    const bad = [];
    for (const it of menu) {
        const r = byPath.get(it.path);
        if (!r) { bad.push(`pas de route: ${it.path}`); continue; }
        for (const role of it.roles) if (!routeAllows(r, role)) bad.push(`${it.path} interdit a ${role}`);
    }
    assert.deepEqual(bad, []);
});

for (const [file, prefix] of [['MedicalLayout', '/medical'], ['SecretaireLayout', '/secretariat']]) {
    test(`${file} : chaque lien du menu existe dans le routeur`, () => {
        const src = readFileSync(new URL(`../src/components/layout/${file}.vue`, import.meta.url), 'utf8');
        const missing = [];
        for (const m of src.matchAll(/path:\s*'(\/[^']*)'/g)) {
            const p = m[1].length > 1 ? m[1].replace(/\/$/, '') : m[1];
            if (!byPath.has(p) && !byPath.has(m[1])) missing.push(m[1]);
        }
        assert.deepEqual(missing, []);
    });
}

// Ecarts voulus : l'admin n'a pas de menu pour les saisies de terrain (adminHidden), la route reste ouverte pour lui.
// Decision du proprietaire (2026-10-26) : l'assistant n'a pas besoin de la reception du labo, la route lui est fermee.
const KNOWN_GAPS = new Set([]);

test('route ouverte a un role : une entree de menu la lui montre (hors ecarts voulus)', () => {
    const gaps = [];
    for (const r of routes) {
        if (!r.path.startsWith('/dashboard') || !r.roles || r.path.includes(':') || r.path.endsWith('/new')) continue;
        for (const role of r.roles) {
            const items = menu.filter((m) => m.path === r.path);
            const covered = items.some((m) => (role === 'admin' ? !m.adminHidden : m.roles.includes(role)));
            const viaLabo = r.path.startsWith('/dashboard/labo/') && menu.some((m) => m.path === '/dashboard/labo' && (role === 'admin' || m.roles.includes(role)));
            const adminDesignedHidden = role === 'admin' && items.some((m) => m.adminHidden);
            const key = `${role} ${r.path}`;
            if (!covered && !viaLabo && !adminDesignedHidden && !KNOWN_GAPS.has(key)) gaps.push(key);
        }
    }
    assert.deepEqual(gaps, []);
});

test('le promoteur atterrit sur /dashboard/overview et l y retrouve par le menu', () => {
    const item = menu.find((m) => m.path === '/dashboard/overview');
    assert.ok(item.roles.includes('promoteur'));
    assert.ok(routeAllows(byPath.get('/dashboard/overview'), 'promoteur'));
});
