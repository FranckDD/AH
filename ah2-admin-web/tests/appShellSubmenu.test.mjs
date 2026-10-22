// AppShell : sous-menus repliables et séparateur (pour les espaces qui passent de MainLayout au cadre commun).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildMenu, toShellGroups, groupContainsPath } from '../src/utils/sidebarMenu.js';

const shell = readFileSync(new URL('../src/components/layout/AppShell.vue', import.meta.url), 'utf8');

const items = [
    { path: '/a', labelKey: 'a', icon: 'IA', roles: ['admin'] },
    { path: '/s1', labelKey: 's1', icon: 'I1', roles: ['admin'], group: 'stock' },
    { path: '/s2', labelKey: 's2', icon: 'I2', roles: ['admin'], group: 'stock' },
    { path: '/l1', labelKey: 'l1', icon: 'IL', roles: ['admin'], group: 'lab' },
    { path: '/cfg', labelKey: 'cfg', icon: 'IC', roles: ['admin'], separator: true },
];
const groups = { stock: { labelKey: 'g.stock', icon: 'GS' }, lab: { labelKey: 'g.lab', icon: 'GL' } };
const entries = buildMenu(items, { isAdmin: true, hasRole: () => true, groups });

test('toShellGroups : lien plat, sous-menu, groupe à un seul enfant devenu lien, séparateur conservé', () => {
    const [g] = toShellGroups(entries);
    assert.equal(g.key, 'main');
    assert.equal(g.labelKey, undefined);
    assert.deepEqual(g.items.map((i) => i.path || i.key), ['/a', 'g-stock', '/l1', '/cfg']);
    const stock = g.items[1];
    assert.equal(stock.labelKey, 'g.stock');
    assert.equal(stock.icon, 'GS');
    assert.deepEqual(stock.children.map((c) => c.path), ['/s1', '/s2']);
    assert.equal(g.items[2].children, undefined, 'un groupe à un enfant est un lien plat');
    assert.equal(g.items[3].separator, true);
    assert.equal(g.items[0].separator, undefined);
});

test('toShellGroups : liste vide ou absente donne aucun groupe ; intertitre facultatif', () => {
    assert.deepEqual(toShellGroups([]), []);
    assert.deepEqual(toShellGroups(undefined), []);
    assert.equal(toShellGroups(entries, { labelKey: 'x.title' })[0].labelKey, 'x.title');
});

test('un item de sous-menu est reconnu actif par groupContainsPath (ouverture d’office)', () => {
    const stock = toShellGroups(entries)[0].items[1];
    assert.equal(groupContainsPath(stock, '/dashboard/s2/detail'), true);
    assert.equal(groupContainsPath(stock, '/other'), false);
});

test('AppShell : sous-menu accessible, ouvert d’office, navigation au premier enfant quand le menu est réduit', () => {
    assert.match(shell, /v-if="item\.children"/);
    assert.match(shell, /:aria-expanded="isGroupOpen\(item\)"/);
    assert.match(shell, /groupContainsPath\(item, route\.path\)/);
    assert.match(shell, /router\.push\(item\.children\[0\]\.path\)/);
    assert.match(shell, /if \(groupActive\(item\)\) return;/);
});

test('AppShell : séparateur et intertitre facultatif ; entrées et badge de quarantaine d’origine conservés', () => {
    assert.match(shell, /<hr v-if="item\.separator"/);
    assert.match(shell, /<p v-if="group\.labelKey"/);
    assert.match(shell, /item\.onlyWhenQuarantine/);
    assert.match(shell, /isActive\(item\)/);
    assert.match(shell, /key="item\.path \|\| item\.key"|:key="item\.path \|\| item\.key"/);
});

test('AppShell : pas de couleur brute ni de texte < 13 px dans le sous-menu', () => {
    assert.doesNotMatch(shell, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
    assert.doesNotMatch(shell, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
});
