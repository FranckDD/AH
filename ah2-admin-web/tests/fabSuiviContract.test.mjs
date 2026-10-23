import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/fabrication/FabSuivi.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));
const FORBIDDEN = /[—–…·•→]|\p{Extended_Pictographic}/u;
const KINDS = ['hors_tolerance', 'intrant_sous_seuil', 'lot_trop_long', 'ecart_expedie_recu'];

for (const needle of [
    "const canEditSettings = computed(() => authStore.hasRole(['admin']));",
    'FabricationGateway.getSummary()', 'FabricationGateway.getAnomalies()',
    'FabricationGateway.getSettings()', 'FabricationGateway.updateSettings(',
    "name: 'fabrication-lot'",
    '@submit.prevent="saveSettings"', 'v-model="settingsForm.tolerance_pct"', 'v-model="settingsForm.stale_days"',
    'describeFabricationError(err,', 'onMounted(load);',
]) {
    test(`FabSuivi : ${needle} est conserve`, () => assert.ok(view.includes(needle), needle));
}

test('FabSuivi : lecture seule pour le promoteur, reglages derriere un v-if admin', () => {
    const t = templateOf(view);
    // la carte des reglages et son formulaire dependent de canEditSettings
    assert.match(t, /<AppCard[^>]*v-if="canEditSettings"/);
    // le formulaire d'ecriture n'existe qu'a l'interieur de cette carte
    const card = t.slice(t.search(/<AppCard[^>]*v-if="canEditSettings"/));
    assert.ok(card.includes('<form'), 'formulaire dans la carte admin');
    const before = t.slice(0, t.search(/<AppCard[^>]*v-if="canEditSettings"/));
    assert.doesNotMatch(before, /<form|<input|<textarea|<select/);
    // le garde de la fonction d'ecriture
    assert.match(view, /if \(!canEditSettings\.value\) return;/);
    // un seul appel d'ecriture, jamais de role promoteur ou ProductionManager pour l'ecriture
    assert.equal((view.match(/updateSettings\(/g) || []).length, 1);
    assert.doesNotMatch(view, /hasRole\(\[[^\]]*(promoteur|ProductionManager)/);
});

test('FabSuivi : validation des reglages (tolerance >= 0, delai entier > 0)', () => {
    assert.match(view, /fabrication\.err_tolerance/);
    assert.match(view, /fabrication\.err_stale_days/);
    assert.match(view, /days > 3650/);
    assert.match(view, /\\d\{1,2\}/);
    assert.match(view, /Number\.isInteger\(/);
});

test('FabSuivi : chaque nature d\'anomalie a un libelle FR et EN et une phrase de detail', () => {
    for (const k of KINDS) for (const l of ['fr', 'en']) {
        for (const base of ['anomaly_kind_', 'anomaly_detail_']) {
            const v = pick(msgs[l], `fabrication.${base}${k}`);
            assert.ok(typeof v === 'string' && v !== '', `${l}.${base}${k} manquante`);
            assert.doesNotMatch(v, FORBIDDEN);
        }
    }
    assert.match(view, /fabrication\.anomaly_kind_\$\{/);
    assert.match(view, /fabrication\.anomaly_detail_\$\{/);
});

test('FabSuivi : tuiles, listes, etat vide, role alert/status', () => {
    for (const c of ['PageHeader', 'StatTile', 'StatusBadge', 'EmptyState', 'AppCard', 'AppButton', 'FormField']) {
        assert.match(view, new RegExp(String.raw`\b${c}\b`), c);
    }
    const t = templateOf(view);
    assert.match(t, /role="alert"/);
    assert.match(t, /role="status"/);
    assert.match(view, /counts_by_status/);
    assert.match(view, /anomalies_count/);
    assert.match(t, /<EmptyState/);
});

test('FabSuivi : cles fabrication.* et common.* en FR et EN, sans caractere interdit', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:fabrication|stockOps|common)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 14, `seulement ${used.size} cles`);
    for (const k of used) for (const l of ['fr', 'en']) {
        const v = pick(msgs[l], k);
        assert.ok(typeof v === 'string' && v !== '', `${l}.${k} manquante`);
        assert.doesNotMatch(v, FORBIDDEN, `${l}.${k}`);
    }
});

test('FabSuivi : jetons, texte >= 13 px, cibles >= 44 px, aucun texte en dur', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /#[0-9a-fA-F]{3,8}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    const t = templateOf(view);
    assert.doesNotMatch(t, FORBIDDEN);
    assert.match(view, /min-h-11/);
    const bare = [...t.matchAll(/>([^<>{}]*[A-Za-z]{3,}[^<>{}]*)</g)].map((m) => m[1].trim()).filter(Boolean);
    assert.deepEqual(bare, [], `texte en dur : ${bare.join(' | ')}`);
});
