import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/fabrication/FabLots.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));
const FORBIDDEN = /[—–…·•→]|\p{Extended_Pictographic}/u;

for (const needle of [
    "const canWrite = computed(() => authStore.hasRole(['ProductionManager']));",
    'v-if="canWrite"',
    'FabricationGateway.listBatches(', 'FabricationGateway.createBatch(',
    'FabricationGateway.listProducts()',
    "name: 'fabrication-lot'",
    'v-model="statusFilter"', 'v-if="createOpen"', '@submit.prevent="saveBatch"',
    'v-model="form.product_id"', 'v-model="form.production_date"',
    'describeFabricationError(err,', 'onMounted(load);',
]) {
    test(`FabLots : ${needle} est conserve`, () => assert.ok(view.includes(needle), needle));
}

test('FabLots : filtre par date de production a cote du statut, envoye a la passerelle', () => {
    assert.ok(view.includes('v-model="dateFrom"') && view.includes('v-model="dateTo"'));
    assert.ok(view.includes('@click="resetDates"'));
    assert.ok(view.includes('dateFrom: dateFrom.value || undefined, dateTo: dateTo.value || undefined'));
    assert.match(view, /fabrication\.err_date_range/);
});

test('passerelle : listPurchases et listBatches transmettent date_from et date_to', () => {
    const gw = readFileSync(new URL('../src/services/FabricationGateway.js', import.meta.url), 'utf8');
    assert.match(gw, /listPurchases\(\{ intrantId, dateFrom, dateTo \} = \{\}\)/);
    assert.match(gw, /listBatches\(\{ status, dateFrom, dateTo \} = \{\}\)/);
    assert.equal((gw.match(/date_from: dateFrom, date_to: dateTo/g) || []).length, 2);
});

test('FabLots : catalogue lu par la Fabrication, pas par le stock', () => {
    assert.doesNotMatch(view, /StockOpsGateway/);
});

test('FabLots : le statut de chaque lot est dit par un mot dans un StatusBadge', () => {
    assert.match(view, /<StatusBadge[^>]*:label="t\(`fabrication\.batch_status_\$\{/);
    for (const s of ['brouillon', 'en_production', 'termine', 'expedie', 'annule']) {
        for (const l of ['fr', 'en']) assert.ok(pick(msgs[l], `fabrication.batch_status_${s}`), `${l} ${s}`);
    }
});

test('FabLots : composants ui/, tableau responsive alterne, panneau plein ecran', () => {
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar']) {
        assert.match(view, new RegExp(String.raw`\b${c}\b`), c);
    }
    const t = templateOf(view);
    assert.match(t, /<ResponsiveTable[^>]*striped/s);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
});

test('FabLots : cles fabrication.* et stockOps.* en FR et EN, sans caractere interdit', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:fabrication|stockOps|common)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 12, `seulement ${used.size} cles`);
    for (const k of used) for (const l of ['fr', 'en']) {
        const v = pick(msgs[l], k);
        assert.ok(typeof v === 'string' && v !== '', `${l}.${k} manquante`);
        assert.doesNotMatch(v, FORBIDDEN, `${l}.${k}`);
    }
});

test('FabLots : jetons, texte >= 13 px, aucun texte en dur', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /#[0-9a-fA-F]{3,8}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    const t = templateOf(view);
    assert.doesNotMatch(t, FORBIDDEN);
    const bare = [...t.matchAll(/>([^<>{}]*[A-Za-z]{3,}[^<>{}]*)</g)].map((m) => m[1].trim()).filter(Boolean);
    assert.deepEqual(bare, [], `texte en dur : ${bare.join(' | ')}`);
});
