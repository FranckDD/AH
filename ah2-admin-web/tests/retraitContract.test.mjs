import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const list = read('../src/views/modules/finance/RetraitList.vue');
const modal = read('../src/components/caisse/RetraitModal.vue');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : tout ce que l'écran fait aujourd'hui ---
check('RetraitList', list, [
    'retraitStore.fetchRetraits()', 'retraitStore.createRetrait(payload)', 'retraitStore.cancelRetrait(cancellingRetrait.value.retrait_id, justification)',
    'openCancelModal(r)', `r.status === 'active'`, ':disabled="!r.retrait_id"',
    'formatCurrency(r.amount)', 'formatDate(r.retrait_at)', 'r.justification', 'r.category', 'modeLabel(r.payment_method)',
    'v-model="searchQuery"', 'v-model="startDate"', 'v-model="endDate"', 'v-model="statusFilter"', 'value="active"', 'value="cancelled"',
    'retraitStore.filters.searchQuery', 'retraitStore.filters.startDate', 'retraitStore.filters.endDate', 'retraitStore.filters.status',
    'retraitStore.setFilters({ searchQuery: val })', 'retraitStore.setFilters({ startDate: val })', 'retraitStore.setFilters({ endDate: val })', 'retraitStore.setFilters({ status: val })',
    'retraitStore.isLoading', 'retraitStore.loadError', 'retraitStore.retraits', 'retraitStore.pagination.total', 'retraitStore.pagination.total_pages',
    'goToPage(retraitStore.pagination.page - 1)', 'goToPage(retraitStore.pagination.page + 1)', 'retraitStore.setPage(page)',
    '@click="showCreateModal = true"', ':isSaving="isSavingCreate"', ':errorMessage="createError"', '@save="handleCreate"', '@confirm="handleCancel"',
    'showCreateModal.value = false;', 'cancellingRetrait.value = null;', 'cancellingRetrait = null',
    "if (status === 422) return typeof detail === 'string' && detail ? detail : \"Données invalides.\";", 'if (status === 400) return detail || "Requête invalide.";',
    "Erreur réseau. Veuillez vérifier votre connexion.", "t('caisse.status.active')", "t('caisse.status.cancelled')", "t('caisse.status.all')",
    "t('retrait.title')", "t('retrait.new_retrait')", "t('retrait.search_placeholder')", "t('retrait.table.date')", "t('retrait.table.justification')",
    "t('retrait.table.category')", "t('retrait.table.method')", "t('retrait.table.amount')", "t('retrait.table.status')", "t('caisse.actions.cancel')",
    ".replace('XOF', 'FCFA')", "String(iso).split('T')[0]",
]);

check('RetraitModal', modal, [
    `emit('save', {`, 'amount: Number(form.amount),', 'justification: form.justification.trim(),', 'category: form.category || null,', 'payment_method: form.paymentMethod,',
    'Number(form.amount) > 0 && form.justification.trim().length > 0 && !!form.paymentMethod', 'if (!isFormValid.value) return;',
    "paymentMethod: ''", 'v-model.number="form.amount"', 'min="1"', 'step="0.01"', 'v-model="form.category"', 'v-model="form.paymentMethod"', 'v-model="form.justification"',
    'required', 'value="SUPPLIES"', 'value="SALARY"', 'value="MAINTENANCE"', 'value="BILLS"', 'value="OTHER"',
    'v-for="m in paymentModes"', ':value="m.code"', 'usePaymentModes()',
    ':disabled="isSaving || !isFormValid"', "$emit('close')", "t('retrait.modal.title')", "t('retrait.modal.amount')", "t('retrait.modal.category')",
    "t('retrait.modal.justification')", "t('retrait.modal.justification_placeholder')", "t('finance.modal.method')", "t('finance.modal.cancel')", "t('finance.modal.save')",
    "t('caisse.cancel_modal.saving')", '{{ errorMessage }}', "defineEmits(['close', 'save'])",
]);

test('toutes les clés retrait.*, caisse.*, finance.* et retraitScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const src of [list, modal]) {
        for (const m of src.matchAll(/['"`(]((?:retrait|caisse|finance|retraitScreens|caisseScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 20);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('RetraitList : composants ui/, ?nouveau=1, tableau à lignes alternées, statuts par badge', () => {
    assert.match(list, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FormField', 'AppButton']) assert.match(list, new RegExp(`\\b${c}\\b`), c);
    assert.match(list, /route\.query\.nouveau === '1'/);
    assert.match(list, /window\.history\.replaceState\(/);
    assert.match(list, /\n\s+striped\s*\n/);
    assert.match(list, /<StatusBadge/);
    assert.match(list, /align: 'right'/);
    assert.match(list, /variant="danger"/);
});

test('RetraitModal : panneau, champs avec étiquette, barre d’actions', () => {
    for (const c of ['FullScreenPanel', 'FormField', 'ActionBar', 'AppButton']) assert.match(modal, new RegExp(`\\b${c}\\b`), c);
});

test('écrans retraits : jetons du thème, texte >= 13 px, aucun caractère interdit dans le gabarit', () => {
    for (const src of [list, modal]) {
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
        assert.doesNotMatch(src, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
        assert.doesNotMatch(templateOf(src), /[—–…·−]/);
    }
});

test('clés retraitScreens.* en FR et EN', () => {
    const keys = ['count', 'empty', 'cancel_label', 'amount_help', 'justification_help'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].retraitScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.retraitScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.retraitScreens.${k}`);
        }
    }
});
