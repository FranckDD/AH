import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/caisse/DiscountRequestsHistory.vue', import.meta.url), 'utf8');
const protocolPath = new URL('../../docs/superpowers/usability-test-protocol-secretariat.md', import.meta.url);
const protocol = existsSync(protocolPath) ? readFileSync(protocolPath, 'utf8') : '';

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

check('DiscountRequestsHistory', view, [
    'DiscountRequestGateway.getHistory({ ...currentParams(), page: pagination.page, per_page: pagination.per_page })',
    'DiscountRequestGateway.getKpi(currentParams())', 'Object.assign(kpi, resp.data)',
    'rows.value = resp.data.data || [];', 'pagination.total = resp.data.total || 0;',
    'Math.ceil(pagination.total / pagination.per_page) || 1',
    'const day = today.getDay() || 7;', 'monday.setDate(today.getDate() - day + 1);',
    "const first = new Date(today.getFullYear(), today.getMonth(), 1);", "if (key !== 'custom') fetchAll();",
    "activePreset.value = 'custom';", "applyPreset('month');", 'pagination.page = 1;',
    'if (page < 1 || page > pagination.total_pages) return;',
    '@click="applyPreset(preset.key)"', 'v-model="dateFrom"', 'v-model="dateTo"', '@change="onCustomDateChange"',
    'v-model="statusFilter"', '@change="fetchAll"', 'value="approved"', 'value="refused"', 'value="pending"', 'value="cancelled"',
    "currency: 'XAF'", ".replace('XOF', 'FCFA')", "toLocaleString('fr-FR')",
    'kpi.approved_count', 'kpi.refused_count', 'kpi.pending_count', 'formatCurrency(kpi.total_reduced_amount)',
    'r.patient_label', 'r.requested_by_name', 'r.decided_by_name', 'formatCurrency(r.original_amount)',
    '`${r.decision_percent}%`', 'formatCurrency(r.reduced_amount)', 'r.status',
    "'discount_history.preset.week'", "'discount_history.preset.month'", "'discount_history.preset.custom'",
    "t('discount_history.title')", "t('discount_history.results')", "t('discount_history.empty')",
    "t('discount_history.kpi.approved')", "t('discount_history.kpi.refused')", "t('discount_history.kpi.pending')", "t('discount_history.kpi.total_reduced')",
    "t('discount_history.table.date')", "t('discount_history.table.requested_by')", "t('discount_history.table.decided_by')",
    "t('discount_history.table.invoice_amount')", "t('discount_history.table.reduced_amount')", "t('caisse.table.patient')", "t('caisse.table.status')",
    "t('caisse.status.all')", "t('discount_history.from')", "t('discount_history.to')", "t('caisse.table.date')",
    "t(`discount_history.status.${r.status}`)", 'pagination.total_pages',
]);

test('toutes les clés discount_history.* et caisse.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:discount_history|caisse)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size > 20);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

test('clés ajoutées en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        for (const k of ['prev_page', 'next_page', 'filters']) {
            assert.equal(typeof msgs[locale].discountScreens?.[k], 'string', `${locale}.discountScreens.${k}`);
        }
    }
});

// --- Refonte ---
test('composants ui/, tableau responsive, pastilles de période en boutons annoncés aux lecteurs d’écran', () => {
    assert.match(view, /@\/components\/ui/);
    assert.match(view, /ResponsiveTable/);
    assert.match(view, /StatTile/);
    assert.match(view, /StatusBadge/);
    assert.match(view, /:aria-pressed="activePreset === preset\.key"/);
});

test('statuts écrits en toutes lettres avec une tonalité (approuvé vert, refusé rouge, en attente orange)', () => {
    assert.match(view, /approved:\s*'success'/);
    assert.match(view, /refused:\s*'danger'/);
    assert.match(view, /pending:\s*'warning'/);
});

test('couleurs par jetons, texte >= 13 px, aucun caractère typographique interdit', () => {
    assert.doesNotMatch(view, /#[0-9a-fA-F]{6}\b/);
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view.slice(0, view.indexOf('<script')), /[—–…·]/);
    assert.doesNotMatch(view.slice(view.indexOf('<script')), /\|\| '[—–]'|: '[—–]'/);
});

// --- Protocole de test d'utilisation avec la secrétaire ---
test('protocole du test d’utilisation de la secrétaire : cinq tâches types, grille, synthèse, consignes', () => {
    assert.ok(protocol.length > 500, 'protocole absent');
    for (let i = 1; i <= 5; i++) assert.match(protocol, new RegExp(`Tâche ${i}\\b`), `Tâche ${i} absente`);
    assert.match(protocol, /Grille d'observation/);
    assert.match(protocol, /Modèle de synthèse/);
    assert.match(protocol, /penser à voix haute/i);
    assert.doesNotMatch(protocol, /facture|encaisser|retrait/i, 'les tâches de caisse relèvent de la phase 3');
});
