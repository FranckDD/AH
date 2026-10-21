import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildMenu, groupContainsPath } from '../src/utils/sidebarMenu.js';

const items = [
    { path: '/a', roles: ['admin'] },
    { path: '/s1', roles: ['admin', 'Assistant'], group: 'stock', adminHidden: true },
    { path: '/s2', roles: ['StockController', 'admin'], group: 'stock' },
    { path: '/s3', roles: ['admin'], group: 'stock' },
    { path: '/l1', roles: ['laborantin'], group: 'lab' },
    { path: '/l2', roles: ['StockController', 'promoteur'], group: 'lab', adminHidden: false },
    { path: '/l3', roles: ['x'], group: 'lab', adminHidden: true },
    { path: '/z', roles: ['promoteur'] },
];
const groups = { stock: { labelKey: 'g.s' }, lab: { labelKey: 'g.l' } };
const mk = (role) => ({
    isAdmin: role === 'admin',
    hasRole: (rs) => rs.map((r) => r.toLowerCase()).includes(role.toLowerCase()),
    groups,
});
const paths = (entries) => entries.map((e) => (e.type === 'link' ? e.item.path : `${e.key}:${e.children.map((c) => c.path).join(',')}`));

test('admin hides flagged items, keeps others', () => {
    const out = buildMenu(items, mk('admin'));
    // stock group: s2,s3 (s1 hidden); lab group: l1,l2 are not admin roles but admin sees all non-flagged
    assert.deepEqual(paths(out), ['/a', 'stock:/s2,/s3', 'lab:/l1,/l2', '/z']);
});

test('role with one child gets a flat link', () => {
    assert.deepEqual(paths(buildMenu(items, mk('Assistant'))), ['/s1']);
    assert.deepEqual(paths(buildMenu(items, mk('laborantin'))), ['/l1']);
});

test('role with several children gets a group', () => {
    assert.deepEqual(paths(buildMenu(items, mk('StockController'))), ['stock:/s2'].map(() => '/s2').concat(['/l2']));
    const out = buildMenu(items, mk('promoteur'));
    assert.deepEqual(paths(out), ['/l2', '/z']);
});

test('group hidden when no child visible', () => {
    assert.deepEqual(paths(buildMenu(items, mk('nobody'))), []);
});

test('stock controller sees control + movements-style children as group when 2+', () => {
    const its = [
        { path: '/stock-control', roles: ['StockController'], group: 'stock' },
        { path: '/stock-movements', roles: ['StockController'], group: 'stock' },
        { path: '/lab-stock-products', roles: ['StockController'], group: 'lab' },
    ];
    const out = buildMenu(its, mk('StockController'));
    assert.deepEqual(paths(out), ['stock:/stock-control,/stock-movements', '/lab-stock-products']);
    assert.ok(groupContainsPath(out[0], '/dashboard/stock-movements'.replace('/dashboard', '')));
});
