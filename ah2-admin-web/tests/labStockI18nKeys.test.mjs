import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const FILES = [
    '../src/views/modules/labstock/LabStockProducts.vue',
    '../src/views/modules/labstock/LabStockRequests.vue',
    '../src/utils/labStockLabels.js',
    '../src/views/modules/labstock/LabStockReceipts.vue',
    '../src/views/modules/labstock/LabStockReceiptForm.vue',
    '../src/views/modules/labstock/LabStockCount.vue',
    '../src/utils/labReceiptLines.js',
    '../src/components/layout/MainLayout.vue',
    '../src/views/modules/labstock/LabStockAlerts.vue',
    '../src/views/modules/labstock/LabStockMovements.vue',
    '../src/views/modules/labstock/LabStockExpenses.vue',
];

const used = new Set();
for (const f of FILES) {
    const src = readFileSync(new URL(f, import.meta.url), 'utf8');
    for (const m of src.matchAll(/['"`]((?:labStock|notifications\.lab_stock)[\w.${}]*)['"`]/g)) used.add(m[1]);
}
// Cles dynamiques : expansion explicite des valeurs possibles.
const DYN = {
    'labStock.origin.': ['signalement', 'seuil', 'peremption'],
    'labStock.status.': ['a_commander', 'commande', 'recu', 'annule'],
    'labStock.level.': ['bientot_fini', 'fini'],
    'notifications.lab_stock_signal_': ['bientot_fini', 'fini', 'other'],
    'labStock.mv_type.': ['reception', 'comptage', 'annulation_reception'],
};
const keys = new Set();
for (const k of used) {
    if (k.includes('${')) {
        const prefix = k.slice(0, k.indexOf('${'));
        const vals = DYN[prefix];
        assert.ok(vals, `unmapped dynamic key ${k}`);
        vals.forEach((v) => keys.add(prefix + v));
    } else keys.add(k);
}
['stockOps.menu_group', 'labStock.menu_group', 'notifications.lab_stock_low', 'notifications.lab_stock_expiry', 'notifications.lab_stock_received',
 'notifications.lab_stock_count_reminder', 'notifications.lab_stock_count_reminder_never', 'notifications.lab_stock_other'].forEach((k) => keys.add(k));

const get = (obj, path) => path.split('.').reduce((o, p) => (o == null ? undefined : o[p]), obj);

for (const loc of ['fr', 'en']) {
    test(`all lab stock keys exist in ${loc}`, () => {
        const msgs = i18n.global.getLocaleMessage(loc);
        assert.ok(keys.size > 20);
        for (const k of keys) {
            // Prefixes passed to pick() (labStock.origin, ...) are groups; their leaves are checked via DYN.
            const isGroup = Object.keys(DYN).includes(`${k}.`);
            assert.equal(typeof get(msgs, k), isGroup ? 'object' : 'string', `missing ${loc}: ${k}`);
        }
    });
}
