import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/fabrication/FabIntrants.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : ${needle} est conserve`, () => {
            assert.ok(src.includes(needle), `${needle} a disparu de ${name}`);
        });
    }
}

check('FabIntrants', view, [
    // droits : ecriture ProductionManager seul, seuil admin seul
    "const canWrite = computed(() => authStore.hasRole(['ProductionManager']));",
    "const canSetThreshold = computed(() => authStore.hasRole(['admin']));",
    'v-if="canWrite"', 'v-if="canSetThreshold',
    // passerelle
    'FabricationGateway.listIntrants({ includeInactive: showInactive.value })',
    'FabricationGateway.listPurchases({ dateFrom: dateFrom.value || undefined, dateTo: dateTo.value || undefined })',
    'FabricationGateway.updateIntrant(',
    // intrants desactives, modification avant livraison, filtre de dates
    'v-model="showInactive"', 'v-if="editTarget"', 'v-if="toggleTarget"', '@submit.prevent="saveEdit"',
    'v-model="editForm.name"', 'v-model="editForm.unit"', 'v-model="editForm.is_container"',
    'v-model="dateFrom"', 'v-model="dateTo"', '@click="resetDates"', 'i.editable',
    'FabricationGateway.createIntrant(', 'FabricationGateway.createPurchase(',
    'FabricationGateway.cancelPurchase(', 'FabricationGateway.setThreshold(',
    'describeFabricationError(err,', 'onMounted(load);',
    // ecran
    'v-if="purchaseOpen"', 'v-if="cancelTarget"', '@submit.prevent="savePurchase"', '@submit.prevent="confirmCancel"',
    'v-model="form.mode"', 'v-model="form.is_container"', 'v-model="form.unit_cost"', 'v-model="form.quantity"',
    'i.below_threshold', 'p.status === \'actif\'', 'formatCurrency(',
]);

test('texte de seuil dit par un mot dans un StatusBadge', () => {
    assert.match(view, /<StatusBadge[^>]*:label="t\('fabrication\.below_threshold'\)"/);
});

test('intrant desactive : dit par un mot dans un StatusBadge', () => {
    assert.match(view, /<StatusBadge v-if="!i\.is_active"[^>]*:label="t\('fabrication\.intrant_inactive'\)"/);
});

test('actions par intrant : ProductionManager seul (v-if), Modifier seulement si modifiable, sinon verrou dit en mots', () => {
    const t = templateOf(view);
    assert.match(t, /<template v-if="canWrite" #actions="\{ row: i \}">/);
    assert.match(t, /<AppButton v-if="i\.editable"[^>]*@click="openEdit\(i\)"/);
    assert.match(t, /v-else[^>]*>\{\{ t\('fabrication\.intrant_locked'\) \}\}/);
    assert.match(t, /@click="openToggle\(i\)"/);
    assert.match(t, /fabrication\.intrant_deactivate/);
    assert.match(t, /fabrication\.intrant_reactivate/);
    assert.doesNotMatch(t, /:disabled="!i\.editable"/);
});

test('modification refusee (409) : message du serveur affiche dans une alerte', () => {
    assert.match(view, /editError\.value = describeFabricationError\(err,/);
    assert.match(templateOf(view), /v-if="editError" role="alert"/);
});

test('filtre de dates : debut <= fin verifie avant appel', () => {
    assert.match(view, /fabrication\.err_date_range/);
});

test('annulation : motif obligatoire, message du serveur (409) affiche', () => {
    assert.match(view, /fabrication\.err_reason_required/);
    assert.match(view, /modalError\.value = describeFabricationError/);
});

test('toutes les cles fabrication.*, stockOps.* citees existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:fabrication|stockOps)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 30, `seulement ${used.size} cles`);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(typeof v === 'string' && v !== '', `${locale}.${k} manquante`);
            assert.doesNotMatch(v, /[\u2014\u2013\u2026\u00b7\u2022\u2192]|\p{Extended_Pictographic}/u, `${locale}.${k} caractere interdit`);
        }
    }
});

test('FabIntrants : composants ui/, deux tableaux responsive a lignes alternees, champs etiquetes', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'ActionBar', 'AppCard']) {
        assert.match(view, new RegExp(String.raw`\b${c}\b`), c);
    }
    const t = templateOf(view);
    assert.equal((t.match(/<ResponsiveTable/g) || []).length, 2);
    assert.equal((t.match(/\bstriped\b/g) || []).length, 2);
    assert.equal((t.match(/<FullScreenPanel/g) || []).length, 5); // achat, modification d achat, annulation, intrant, activation
    assert.ok((t.match(/<FormField/g) || []).length >= 8);
    assert.match(view, /align: 'right'/);
});

test('FabIntrants : erreurs annoncees (alert), succes annonce (status), boutons varies', () => {
    const t = templateOf(view);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
    assert.match(t, /variant="danger"/);
    assert.match(t, /variant="secondary"/);
    assert.doesNotMatch(t, /fixed inset-0/);
});

test('FabIntrants : jetons du theme, texte >= 13 px, aucun caractere interdit ni texte en dur', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /#[0-9a-fA-F]{3,8}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    const t = templateOf(view);
    assert.doesNotMatch(t, /[\u2014\u2013\u2026\u00b7\u2022\u2192]|\p{Extended_Pictographic}/u);
    // aucun texte en dur entre balises
    const bare = [...t.matchAll(/>([^<>{}]*[A-Za-z]{3,}[^<>{}]*)</g)].map((m) => m[1].trim()).filter(Boolean);
    assert.deepEqual(bare, [], `texte en dur : ${bare.join(' | ')}`);
});

test('cles fabrication de l ecran en FR et EN avec memes noms', () => {
    const fr = Object.keys(msgs.fr.fabrication).sort();
    const en = Object.keys(msgs.en.fabrication).sort();
    assert.deepEqual(fr, en);
});
