import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const list = read('../src/views/modules/finance/FinancialList.vue');
const modal = read('../src/components/finance/FinanceModal.vue');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : ce que l'écran et le formulaire font aujourd'hui (aucun changement de chiffre ni de forme envoyée) ---
check('FinancialList', list, [
    // données et filtres
    'financialStore.fetchTransactions()', 'FinanceGateway.fetchCategories()', 'availableCategories.value = reponse.data || [];', 'availableCategories.value = [];',
    'financialStore.filters.searchQuery', 'financialStore.setFilters({ searchQuery: val })', 'financialStore.filters.category', 'financialStore.setFilters({ category: val })',
    'financialStore.filters.type', 'financialStore.setFilters({ type: val })', 'financialStore.filters.startDate', 'financialStore.setFilters({ startDate: val })',
    'financialStore.filters.endDate', 'financialStore.setFilters({ endDate: val })',
    "financialStore.setFilters({ searchQuery: '', category: '', type: 'ALL', startDate: '', endDate: '' })", 'financialStore.setPage(page)',
    'v-model="searchQuery"', 'v-model="categoryFilter"', 'v-model="startDate"', 'v-model="endDate"', 'v-for="cat in availableCategories"', '@click="resetFilters"',
    "typeFilter = 'ALL'", "typeFilter = 'INCOME'", "typeFilter = 'EXPENSE'", "typeFilter === 'ALL'", "typeFilter === 'INCOME'", "typeFilter === 'EXPENSE'",
    // indicateurs : jamais 0 à la place d'une panne
    'financialStore.kpiError ? \'Indisponible\' : valeurFormatee', 'kpiAffiche(formatCurrency(financialStore.totalIncome))', 'kpiAffiche(formatCurrency(financialStore.totalExpenses))',
    'kpiAffiche(formatCurrency(financialStore.currentBalance))', 'financialStore.loadError', 'financialStore.pagination.total',
    // tableau
    'financialStore.transactions', 'financialStore.isLoading', 'tx.description', 'tx.paymentMethod', 'tx.category', "tx.type === 'INCOME'", "tx.type === 'INCOME' ? '+' : '-'",
    'formatCurrency(tx.amount)', "tx.status === 'Validé'", 'tx.status', 'tx.date',
    // pagination
    'financialStore.pagination.total_pages', 'goToPage(financialStore.pagination.page - 1)', 'goToPage(financialStore.pagination.page + 1)',
    // modale
    '@click="showModal = true"', '<FinanceModal', '@close="showModal = false"', '@save="handleSaveTransaction"',
    'await financialStore.addTransaction(transactionData);', 'showModal.value = false;',
    "new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value).replace('XOF', 'FCFA')",
    // clés
    "t('finance.title')", "t('finance.new_transaction')", "t('finance.search_placeholder')", "t('finance.modal.category')", "t('finance.income')", "t('finance.expense')",
    "t('finance.balance')", "t('finance.table.date')", "t('finance.table.desc')", "t('finance.table.category')", "t('finance.table.amount')", "t('finance.table.status')",
    // l'indicateur de chargement est désormais celui du tableau commun (ui.loading)
]);

check('FinanceModal', modal, [
    "defineEmits(['close', 'save'])", "emit('save', { ...form });", "const today = todayLocalISO();",
    "type: 'INCOME'", "amount: ''", 'date: today', "category: ''", "paymentMethod: ''","description: ''",
    "form.type = type;", "form.category = '';", "setTransactionType('INCOME')", "setTransactionType('EXPENSE')",
    'if (form.amount <= 0) {', "notify('alerts.amount_positive');", 'if (!form.category) {', "notify('alerts.category_required');",
    "key: 'CONSULTATION'", "key: 'PHARMACY'", "key: 'HOSPITALIZATION'", "key: 'LAB'", "key: 'DETOX'", "key: 'SUPPLIES'", "key: 'SALARY'", "key: 'MAINTENANCE'", "key: 'BILLS'", "key: 'OTHER'",
    'v-model.number="form.amount"', 'min="1"', 'v-model="form.date"', 'v-model="form.category"', 'v-model="form.paymentMethod"', 'v-model="form.description"', 'required',
    'v-for="cat in availableCategories"', ':value="cat.key"', '{{ cat.label }}',
    'v-for="m in paymentModes"', ':value="m.code"',
    "t('finance.modal.title_new')", "t('finance.modal.type')", "t('finance.modal.amount')", "t('finance.modal.date')", "t('finance.modal.category')", "t('finance.modal.method')",
    "t('finance.modal.desc')", "t('finance.modal.cancel')", "t('finance.modal.save')", "t('finance.income')", "t('finance.expense')",
]);

test('toutes les clés finance.*, common.* et financeScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const src of [list, modal]) {
        for (const m of src.matchAll(/['"`(]((?:finance|common|financeScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
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
test('FinancialList : composants ui/, tuiles, tableau à lignes alternées, statuts par badge, montants à droite', () => {
    assert.match(list, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'StatTile', 'ResponsiveTable', 'StatusBadge', 'FormField', 'AppButton']) assert.match(list, new RegExp(`\\b${c}\\b`), c);
    assert.match(list, /\n\s+striped\s*\n/);
    assert.match(list, /align: 'right'/);
    assert.match(list, /aria-pressed/);
});

test('FinancialList : une cellule par colonne (le tableau n’a plus de colonne de date en double)', () => {
    const tpl = templateOf(list);
    assert.equal((tpl.match(/#cell-/g) || []).length, 5, 'cinq colonnes : date, description, catégorie, montant, statut');
    assert.equal((tpl.match(/\{\{ tx\.date \}\}/g) || []).length, 1, 'la date ne s’affiche qu’une fois par ligne');
});

test('FinanceModal : panneau, champs étiquetés, type en groupe de boutons à état écrit', () => {
    for (const c of ['FullScreenPanel', 'FormField', 'ActionBar', 'AppButton']) assert.match(modal, new RegExp(`\\b${c}\\b`), c);
    assert.match(modal, /aria-pressed/);
    assert.doesNotMatch(templateOf(modal), /fixed inset-0/);
});

test('écrans finance : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    for (const src of [list, modal]) {
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
        assert.doesNotMatch(src, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
        assert.doesNotMatch(templateOf(src), /[—–…·]|\p{Extended_Pictographic}/u);
    }
});

test('clés financeScreens.* en FR et EN', () => {
    const keys = ['subtitle', 'search_label', 'from', 'to', 'all_types', 'entries', 'exits', 'all_categories', 'reset', 'results', 'load_error', 'empty', 'page_label',
        'prev_page', 'next_page', 'amount_help', 'select_category', 'description_placeholder', 'type_group'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].financeScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.financeScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.financeScreens.${k}`);
        }
    }
});
