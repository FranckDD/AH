import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const list = read('../src/views/modules/finance/CaisseList.vue');
const cancel = read('../src/components/caisse/CaisseCancelModal.vue');
const installment = read('../src/components/caisse/CaisseInstallmentModal.vue');

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : tout ce que l'écran fait aujourd'hui (aucun changement de comportement ni de montant) ---
check('CaisseList', list, [
    // actions sur une ligne, avec leurs conditions
    'openViewModal(tx)', 'openInstallmentModal(tx)', 'handleSettle(tx)', 'openCancelModal(tx)', 'downloadInvoice(tx)',
    'printTicketForTransaction(tx.transaction_id)', ':disabled="!tx.transaction_id"',
    `tx.status === 'active' && Number(tx.amount_due) > 0`, `tx.status === 'active'`,
    // montants, réduction personnel, statuts, échec de synchronisation
    'formatCurrency(tx.amount)', 'formatCurrency(tx.amount_paid)', 'formatCurrency(tx.amount_due)',
    'Number(tx.staff_discount_amount) > 0', 'formatCurrency(tx.staff_discount_amount)', "t('staffDiscount.invoice_line')",
    'tx.status === \'pending_approval\'', 'tx.status === \'refunded\'', 'tx.upload_error', 'formatDate(tx.paid_at)', 'tx.patient_name', 'tx.transaction_type',
    // indicateurs, filtres, pagination
    'caisseStore.kpi.total_paid', 'caisseStore.kpi.remaining_due', 'caisseStore.kpi.total_transactions', 'kpiAffiche(', 'caisseStore.pagination.total',
    'v-model="searchQuery"', 'v-model="startDate"', 'v-model="endDate"', 'v-model="statusFilter"',
    'value="active"', 'value="pending_approval"', 'value="cancelled"', 'value="refunded"',
    'caisseStore.isLoading', 'caisseStore.loadError', 'caisseStore.transactions', 'caisseStore.pagination.total_pages',
    'goToPage(caisseStore.pagination.page - 1)', 'goToPage(caisseStore.pagination.page + 1)',
    // bandeau des réductions en attente
    'pendingApprovalCount > 0 && statusFilter !== \'pending_approval\'', "statusFilter = 'pending_approval'", "t('caisse.pending_banner', { count: pendingApprovalCount })",
    // création de facture et modales
    '@click="showInvoiceModal = true"', 'showInvoiceModal = true', ':isSaving="isSavingInvoice"', ':errorMessage="invoiceError"', '@save="handleCreateInvoice"',
    '@discount-requested', 'fetchPendingApprovalCount()',
    ':remainingDue="Number(installmentTx.amount_due)"', '@confirm="handleAddPayment"', '@confirm="handleCancel"', 'cancellingTx.transaction_id',
    // erreurs
    'v-if="actionError"', '{{ actionError }}',
    // échec d'impression : notification persistante (même cas qu'avant, plus de message dans la page)
    "toastStore.push(describePrintError(err), 'warning')", 'notifyPrintFailure(err);',
    // détail de la facture
    'viewingTx', 'viewingItems', 'viewLoading', 'viewError', 'row-key="item_id"','formatCurrency(item.unit_price)', 'formatCurrency(item.line_total)',
    // script : logique conservée
    'caisseStore.fetchTransactions()', 'caisseStore.createInvoice(payload)', 'caisseStore.addPayment(installmentTx.value.transaction_id, data)',
    'caisseStore.settleTransaction(tx)', 'caisseStore.cancelTransaction(cancellingTx.value.transaction_id, justification)',
    'CaisseGateway.getTransaction(tx.transaction_id)', 'CaisseGateway.getTicket(transactionId)', 'waitForSyncedTransactionId(localUuid)',
    'const AUTO_REFRESH_MS = 30000;', 'showInvoiceModal.value || !!cancellingTx.value || !!installmentTx.value || !!viewingTx.value',
    "Jeton d'impression non configuré.", 'Ticket non imprimé',
    `api.get(\`/caisse/\${tx.transaction_id}/invoice/download\`, { responseType: 'blob' })`,
]);

check('CaisseCancelModal', cancel, [
    `emit('confirm', justification.value.trim())`, '!justification.value.trim()', 'v-model="justification"', 'required',
    ':disabled="isSaving', "$emit('close')", "t('caisse.cancel_modal.title')", "t('caisse.cancel_modal.justification')",
    "t('caisse.cancel_modal.justification_placeholder')", "t('caisse.cancel_modal.cancel')", "t('caisse.cancel_modal.confirm')", "t('caisse.cancel_modal.saving')",
    'label:', 'isSaving:', 'errorMessage:', '{{ errorMessage }}', '{{ label }}',
]);

check('CaisseInstallmentModal', installment, [
    `emit('confirm', { paid_amount: Number(paidAmount.value), payment_method: paymentMethod.value, note: null })`,
    'const paidAmount = ref(props.remainingDue);', "const paymentMethod = ref('especes');", 'v-model.number="paidAmount"', 'v-model="paymentMethod"',
    ':max="remainingDue"', 'min="0.01"', 'step="0.01"', '!(paidAmount > 0)',
    'v-for="m in paymentModes"', ':value="m.code"', 'usePaymentModes()',
    "t('caisse.installment_modal.title')", "t('caisse.installment_modal.remaining_due')", "t('finance.modal.amount')", "t('finance.modal.method')",
    "t('finance.modal.cancel')", "t('finance.modal.save')", 'formatCurrency(remainingDue)', 'remainingDue:', 'errorMessage',
]);

test('toutes les clés caisse.*, finance.* et staffDiscount.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const src of [list, cancel, installment]) {
        for (const m of src.matchAll(/['"`(]((?:caisse|finance|staffDiscount|caisseScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 15);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte : composants ui/, lisibilité, accessibilité (rouge tant que l'écran n'est pas refondu) ---
test('CaisseList : composants ui/ et lecture de ?nouveau=1', () => {
    assert.match(list, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'FullScreenPanel', 'FormField', 'AppButton', 'StatTile']) {
        assert.match(list, new RegExp(`\\b${c}\\b`), c);
    }
    assert.match(list, /route\.query\.nouveau === '1'/);
    // retiré sans navigation : router.replace remonterait la page (clé = fullPath) et fermerait la facture
    assert.match(list, /window\.history\.replaceState\(/);
});

test('CaisseList : montants alignés à droite et statuts écrits (badge avec texte)', () => {
    assert.match(list, /align: 'right'/);
    assert.match(list, /<StatusBadge/);
    assert.match(list, /line-through/);
});

test('modales caisse : panneau, champs avec étiquette, barre d’actions', () => {
    for (const src of [cancel, installment]) {
        assert.match(src, /FullScreenPanel/);
        assert.match(src, /FormField/);
        assert.match(src, /ActionBar/);
    }
});

test('écrans caisse : jetons du thème, texte >= 13 px, aucun caractère typographique interdit dans le gabarit', () => {
    for (const src of [list, cancel, installment]) {
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
        assert.doesNotMatch(src, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
        assert.doesNotMatch(src.slice(0, src.indexOf('<script')), /[—–…·−]/);
    }
});

test('clés caisseScreens.* en FR et EN', () => {
    const keys = ['kpi_transactions', 'transactions_count', 'search_label', 'from', 'to', 'load_error', 'empty', 'page_label', 'prev_page', 'next_page',
        'action_settle', 'action_download', 'pending_sync', 'sync_failed', 'view_title', 'amount_label', 'installment_help', 'cancel_help'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].caisseScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.caisseScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.caisseScreens.${k}`);
        }
    }
});

// --- Retours utilisateur 2026-10-22 : une couleur par action, reste dû en rouge, lignes alternées ---
test('CaisseList : chaque action a sa propre couleur (aucune répétition)', () => {
    const variants = [...list.matchAll(/variant="(\w+)" :icon="(?:EyeIcon|CurrencyDollarIcon|CheckBadgeIcon|ArrowDownTrayIcon|PrinterIcon|XCircleIcon)"/g)];
    assert.equal(variants.length, 6);
    assert.equal(new Set(variants.map((m) => m[1])).size, 6, 'deux actions partagent la même couleur');
});

test('CaisseList : reste dû en rouge (tuile et lignes) et tableau à lignes alternées', () => {
    assert.match(list, /:icon="ClockIcon" tone="danger" alert/);
    assert.match(list, /font-semibold text-tone-danger-text/);
    assert.match(list, /\n\s+striped\s*\n/);
});

test('échec d’impression : notification qui disparaît seule, une seule voie, plus de message dans la page', () => {
    assert.doesNotMatch(list, /printError/);
    assert.equal(list.split('notifyPrintFailure(err);').length - 1, 2, 'impression serveur et ticket local');
    const store = readFileSync(new URL('../src/stores/toastStore.js', import.meta.url), 'utf8');
    assert.match(store, /setTimeout\(\(\) => this\.dismiss\(id\), AUTO_DISMISS_MS\)/);
    assert.doesNotMatch(list, /sticky/);
    assert.doesNotMatch(list.slice(0, list.indexOf('<script')), /Ticket non imprimé/);
    assert.doesNotMatch(list.slice(list.indexOf('const describePrintError')), /Ticket non imprimé —/);
});
