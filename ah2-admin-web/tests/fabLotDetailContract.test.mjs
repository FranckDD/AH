import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/fabrication/FabLotDetail.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));
const tpl = templateOf(view);
const FORBIDDEN = /[—–…·•→]|\p{Extended_Pictographic}/u;

for (const needle of [
    // droits
    "const canWrite = computed(() => authStore.hasRole(['ProductionManager']));",
    // passerelle
    'FabricationGateway.getBatch(', 'FabricationGateway.updateBatch(', 'FabricationGateway.startBatch(',
    'FabricationGateway.finishBatch(', 'FabricationGateway.reopenBatch(', 'FabricationGateway.cancelBatch(',
    'FabricationGateway.shipBatch(', 'FabricationGateway.listPurchases()',
    'consumptions: draft.value.map((d) => ({ purchase_id: d.purchase_id, quantity: String(d.quantity).trim() }))',
    'describeFabricationError(err,', 'onMounted(load);',
    // ecran
    'route.params.id', '@submit.prevent="confirmShip"', '@submit.prevent="confirmFinish"', '@submit.prevent="confirmCancel"',
    'v-model="shipForm.delivery_date"', 'v-model="shipForm.expiry_date"', 'v-model="shipForm.justification"',
    'batch.out_of_tolerance', 'batch.production_lot_number', 'batch.product_name', 'formatCurrency(',
]) {
    test(`FabLotDetail : ${needle} est conserve`, () => assert.ok(view.includes(needle), needle));
}

test('actions par statut, toutes sous canWrite', () => {
    assert.match(tpl, /v-if="canWrite && batch\.status === 'brouillon'"/);
    assert.match(tpl, /v-if="canWrite && batch\.status === 'en_production'"/);
    assert.match(tpl, /v-if="canWrite && batch\.status === 'termine'"/);
    // aucun bouton d'action hors de ces blocs : le seul groupe d'actions est garde par canWrite
    assert.doesNotMatch(tpl, /:disabled="!canWrite"/);
    for (const fn of ['saveDraft', 'startBatch', 'openFinish', 'reopenBatch', 'openCancel', 'openShip']) {
        assert.match(tpl, new RegExp(`@click="${fn}`), fn);
    }
});

test('brouillon seul : editeur des consommations', () => {
    assert.match(tpl, /v-if="canWrite && batch\.status === 'brouillon'"[\s\S]*v-model="d\.quantity"/);
    assert.match(tpl, /v-model="d\.quantity"[^>]*inputmode="decimal"/);
    assert.doesNotMatch(tpl, /v-model\.number="d\.quantity"/);
});

test('justification : visible si hors tolerance OU si le serveur la demande, expedition desactivee tant que vide', () => {
    assert.match(view, /const needsJustification = computed\(\(\) => !!batch\.value\?\.out_of_tolerance \|\| justificationAsked\.value\);/);
    assert.match(tpl, /<FormField v-if="needsJustification" id="fab-ship-justification"/);
    assert.match(view, /const shipBlocked = computed\(\(\) => !shipForm\.value\.delivery_date \|\| \(needsJustification\.value && !\(shipForm\.value\.justification \|\| ''\)\.trim\(\)\)\);/);
    assert.match(tpl, /form="fab-ship-form"[^>]*:disabled="busy \|\| shipBlocked"/);
    // la justification n'est envoyee que si elle est demandee
    assert.match(view, /justification: needsJustification\.value \? shipForm\.value\.justification\.trim\(\) : undefined/);
});

test('422 du serveur demandant une justification : champ revele, panneau garde ouvert, message en alerte', () => {
    assert.match(view, /const isJustificationRequired = \(err\) => err\?\.response\?\.status === 422 && err\?\.response\?\.data\?\.detail\?\.code === 'justification_required';/);
    const ship = view.slice(view.indexOf('const confirmShip'));
    const catchBlock = ship.slice(ship.indexOf('} catch (err) {'), ship.indexOf('} finally {'));
    assert.match(catchBlock, /if \(isJustificationRequired\(err\)\) justificationAsked\.value = true;/);
    assert.match(catchBlock, /modalError\.value = describeFabricationError\(err,/);
    assert.doesNotMatch(catchBlock, /shipOpen\.value = false/);
    // ouverture du panneau : on repart sans demande du serveur
    assert.match(view, /const openShip = \(\) => \{[\s\S]*?justificationAsked\.value = false;/);
});

test('expedier masque sans bouteille bonne ; passer en production sans message de brouillon', () => {
    assert.match(tpl, /v-if="batch\.qty_good > 0" variant="success"/);
    assert.match(view, /const saveDraft = async \(\{ silent = false \} = \{\}\)/);
    assert.match(view, /if \(!\(await saveDraft\(\{ silent: true \}\)\)\) return;/);
});

test('hors tolerance dit par un mot ; valeurs du serveur relues apres terminer et expedier', () => {
    assert.match(tpl, /<StatusBadge v-if="batch\.out_of_tolerance" tone="danger" :label="t\('fabrication\.out_of_tolerance'\)"/);
    assert.match(view, /await FabricationGateway\.finishBatch\([\s\S]*?await load\(\)/);
    assert.match(view, /await FabricationGateway\.shipBatch\([\s\S]*?await load\(\)/);
    // aucun calcul local du bilan en flottant
    assert.doesNotMatch(view, /parseFloat|\/ batch\.value\.expected_qty/);
});

test('nom du produit et numero du lot de production, jamais un #id', () => {
    assert.doesNotMatch(view, /StockOpsGateway/);
    assert.doesNotMatch(tpl, /#\{\{/);
    assert.match(tpl, /fabrication\.tolerance_current/);
});

test('annulation en production : on dit que le stock est rendu', () => {
    assert.match(tpl, /fabrication\.cancel_restores_stock/);
});

test('composants ui/, StatTile pour bilan et cout, etats annonces', () => {
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar', 'AppCard', 'StatTile']) {
        assert.match(view, new RegExp(String.raw`\b${c}\b`), c);
    }
    assert.match(tpl, /<ResponsiveTable[^>]*striped/s);
    assert.match(tpl, /role="alert"/);
    assert.match(tpl, /role="status"/);
    assert.match(tpl, /variant="danger"/);
    assert.match(tpl, /variant="secondary"/);
    assert.match(tpl, /variant="success"/);
    assert.ok((tpl.match(/<FullScreenPanel/g) || []).length >= 3);
});

test('cles fabrication.* et stockOps.* en FR et EN, sans caractere interdit', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:fabrication|stockOps|common)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 40, `seulement ${used.size} cles`);
    for (const k of used) for (const l of ['fr', 'en']) {
        const v = pick(msgs[l], k);
        assert.ok(typeof v === 'string' && v !== '', `${l}.${k} manquante`);
        assert.doesNotMatch(v, FORBIDDEN, `${l}.${k}`);
    }
    assert.deepEqual(Object.keys(msgs.fr.fabrication).sort(), Object.keys(msgs.en.fabrication).sort());
});

test('jetons, texte >= 13 px, aucun texte en dur', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /#[0-9a-fA-F]{3,8}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(tpl, FORBIDDEN);
    const bare = [...tpl.matchAll(/>([^<>{}]*[A-Za-z]{3,}[^<>{}]*)</g)].map((m) => m[1].trim()).filter(Boolean);
    assert.deepEqual(bare, [], `texte en dur : ${bare.join(' | ')}`);
});
