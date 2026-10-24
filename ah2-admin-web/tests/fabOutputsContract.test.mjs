import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/fabrication/FabLotDetail.vue', import.meta.url), 'utf8');
const gw = readFileSync(new URL('../src/services/FabricationGateway.js', import.meta.url), 'utf8');
const tpl = view.slice(0, view.indexOf('<script'));
const FORBIDDEN = /[—–…·•→←]|\p{Extended_Pictographic}/u;

const flat = (o, pre = '') => Object.entries(o).flatMap(([k, v]) => (typeof v === 'object' ? flat(v, `${pre}${k}.`) : [[`${pre}${k}`, v]]));

test('passerelle : trois routes, chemins et corps', () => {
    assert.match(gw, /async declareOutput\(batchId, \{ reason, quantity, note \}\)[\s\S]*?api\.post\(`\/fabrication\/batches\/\$\{batchId\}\/outputs`, clean\(\{ reason, quantity, note \}\)\)/);
    assert.match(gw, /async cancelOutput\(batchId, outputId, reason\)[\s\S]*?api\.post\(`\/fabrication\/batches\/\$\{batchId\}\/outputs\/\$\{outputId\}\/cancel`, \{ reason \}\)/);
    assert.match(gw, /async listOutputs\(\{ dateFrom, dateTo, reason \} = \{\}\)[\s\S]*?api\.get\('\/fabrication\/outputs', \{[\s\S]*?params: clean\(\{ date_from: dateFrom, date_to: dateTo, reason \}\)/);
});

test('passerelle : appel reel avec un api simule', async () => {
    const calls = [];
    const src = gw.replace("import api from '@/services/api';", 'const api = globalThis.__api;');
    globalThis.__api = {
        post: async (url, body) => { calls.push(['post', url, body]); return { data: {} }; },
        get: async (url, cfg) => { calls.push(['get', url, cfg]); return { data: [] }; },
    };
    const mod = await import(`data:text/javascript,${encodeURIComponent(src)}`);
    await mod.FabricationGateway.declareOutput(7, { reason: 'echantillon', quantity: 3, note: '' });
    await mod.FabricationGateway.cancelOutput(7, 9, 'erreur');
    await mod.FabricationGateway.listOutputs({ dateFrom: '2026-10-01', reason: 'autre' });
    assert.deepEqual(calls[0], ['post', '/fabrication/batches/7/outputs', { reason: 'echantillon', quantity: 3 }]);
    assert.deepEqual(calls[1], ['post', '/fabrication/batches/7/outputs/9/cancel', { reason: 'erreur' }]);
    assert.deepEqual(calls[2], ['get', '/fabrication/outputs', { params: { date_from: '2026-10-01', reason: 'autre' } }]);
});

test('section visible pour termine/expedie ou des sorties ; formulaire ProductionManager + termine', () => {
    assert.match(view, /const showOutputs = computed\(\(\) => !!batch\.value && \(\['termine', 'expedie'\]\.includes\(batch\.value\.status\) \|\| \(batch\.value\.outputs \|\| \[\]\)\.length > 0\)\);/);
    assert.match(view, /const canDeclare = computed\(\(\) => canWrite\.value && batch\.value\?\.status === 'termine'\);/);
    assert.match(tpl, /<AppCard v-if="showOutputs"/);
    // M2 : plus rien a sortir -> formulaire cache, avis a la place
    assert.match(tpl, /<form v-if="canDeclare && !nothingToShip" id="fab-output-form"/);
    assert.match(tpl, /<p v-if="canDeclare && allBottlesOut"[^>]*>\{\{ t\('fabrication\.outputs\.nothing_to_ship'\) \}\}/);
});

test('regle de la note pour autre ; quantite entiere bornee par qty_shipped', () => {
    assert.match(view, /const outputNoteMissing = computed\(\(\) => outputForm\.value\.reason === 'autre' && !\(outputForm\.value\.note \|\| ''\)\.trim\(\)\);/);
    assert.match(tpl, /:disabled="outputBusy \|\| outputBlocked"/);
    assert.match(view, /\/\^\\d\+\$\//);
    assert.match(view, /q > num\(batch\.value\.qty_shipped\)/);
    assert.match(tpl, /fabrication\.outputs\.note_required_autre/);
});

test('annulation : motif obligatoire, garde, rechargement', () => {
    const fn = view.slice(view.indexOf('const confirmCancelOutput'));
    assert.match(fn, /if \(!reason\) \{ outputCancelError\.value = t\('fabrication\.outputs\.err_cancel_reason'\); return; \}/);
    assert.match(fn, /if \(outputBusy\.value\) return;/);
    assert.match(fn, /await FabricationGateway\.cancelOutput\(batchId\.value, outputCancelTarget\.value\.id, reason\);[\s\S]*?await load\(\)/);
    assert.match(tpl, /v-if="canDeclare && o\.status === 'active'"/);
    assert.match(tpl, /id="fab-output-cancel-reason"[^>]*maxlength="500"/);
});

test('declaration : garde, erreur serveur visible, rechargement', () => {
    const fn = view.slice(view.indexOf('const confirmDeclareOutput'));
    assert.match(fn, /if \(outputBusy\.value\) return;/);
    assert.match(fn, /await FabricationGateway\.declareOutput\(batchId\.value,[\s\S]*?await load\(\)/);
    assert.match(fn, /outputError\.value = describeFabricationError\(err,/);
    assert.match(tpl, /v-if="outputError" role="alert"/);
});

test('ligne de bilan : valeurs du serveur, jamais recalculees', () => {
    assert.match(tpl, /t\('fabrication\.outputs\.bilan_line', \{ good: batch\.qty_good, outputs: batch\.qty_outputs, shipped: batch\.qty_shipped \}\)/);
    assert.doesNotMatch(view, /qty_good\s*-\s*|qty_good - /);
});

test('expedition : desactivee avec message quand qty_shipped <= 0, dialogue dit qty_shipped', () => {
    assert.match(tpl, /variant="success" :icon="TruckIcon" :disabled="busy \|\| nothingToShip"/);
    assert.match(view, /const nothingToShip = computed\(\(\) => num\(batch\.value\?\.qty_shipped\) <= 0\);/);
    // I2 : le message n'accuse les sorties que s'il y avait des bouteilles bonnes et des sorties
    assert.match(view, /const allBottlesOut = computed\(\(\) => num\(batch\.value\?\.qty_good\) > 0 && num\(batch\.value\?\.qty_outputs\) > 0 && nothingToShip\.value\);/);
    assert.match(tpl, /<p v-if="allBottlesOut" role="status" class="basis-full[^>]*>\{\{ t\('fabrication\.outputs\.nothing_to_ship'\) \}\}/);
    assert.doesNotMatch(tpl, /v-if="nothingToShip"/);
    assert.match(tpl, /t\('fabrication\.ship_help', \{ good: batch\.qty_shipped \}\)/);
    assert.equal(msgs.fr.fabrication.outputs.nothing_to_ship, 'Toutes les bouteilles sont sorties : rien à expédier.');
});

test('FR/EN : memes cles fabrication.outputs.*, sans caractere interdit, cles utilisees presentes', () => {
    const fr = flat(msgs.fr.fabrication.outputs);
    const en = flat(msgs.en.fabrication.outputs);
    assert.deepEqual(fr.map(([k]) => k).sort(), en.map(([k]) => k).sort());
    for (const [k, v] of [...fr, ...en]) assert.doesNotMatch(v, FORBIDDEN, k);
    // les cles dynamiques (`fabrication.outputs.reason.${...}`) sont verifiees plus bas
    for (const m of view.matchAll(/fabrication\.outputs\.([a-zA-Z_.]*[a-zA-Z_])(?![\w.$])/g)) {
        assert.ok(fr.some(([k]) => k === m[1]), m[1]);
    }
    assert.equal(msgs.fr.fabrication.outputs.reason.echantillon, 'Echantillon');
    assert.equal(msgs.fr.fabrication.outputs.reason.autre, 'Autre');
});

test('dates des sorties : formateur local inchange, le serveur envoie +00:00', () => {
    assert.match(view, /const formatDateTime = \(v\) => \(v \? new Date\(v\)\.toLocaleString\('fr-FR'/);
    assert.match(tpl, /formatDateTime\(o\.declared_at\)/);
    assert.match(tpl, /formatDateTime\(o\.cancelled_at\)/);
});

test('jetons, pas de toISOString, pas de texte < 13 px', () => {
    assert.doesNotMatch(view, /toISOString/);
    assert.doesNotMatch(gw, /toISOString/);
    assert.doesNotMatch(view, /#[0-9a-fA-F]{3,8}\b|rgb\(/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(tpl, FORBIDDEN);
});
