import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const store = read('../src/stores/dashboardStore.js');
const view = read('../src/views/dashboards/DashboardOverview.vue');
const tpl = view.slice(0, view.indexOf('<script'));

test('le magasin du tableau de bord n appelle que les routes permises au promoteur', () => {
    assert.ok(store.includes("hasRole(['promoteur'])"));
    const start = store.indexOf('if (restricted)');
    assert.ok(start > 0);
    const block = store.slice(start, store.indexOf('const dateParams'));
    assert.ok(block.includes('ToxicoGateway.getDashboardStats()') && block.includes('HospitalizationGateway.fetchKpiCount()'));
    for (const forbidden of ['FinanceGateway', "api.get('/users/'"]) assert.ok(!block.includes(forbidden), forbidden);
});
test('la page masque les tuiles argent et comptes pour le promoteur et change les actions rapides', () => {
    assert.ok(view.includes('isPromoteur'));
    assert.ok(tpl.includes('v-if="!isPromoteur"'));
    assert.ok(tpl.includes('v-if="isPromoteur"'));
    for (const route of ["'/dashboard/reports'", "'/dashboard/cash-closures'", "'/dashboard/discount-review'"]) assert.ok(tpl.includes(route), route);
});
