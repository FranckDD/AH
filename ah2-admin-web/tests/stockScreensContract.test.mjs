import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const list = read('views/modules/stock/StockList.vue');
const product = read('components/stock/ProductModal.vue');
const request = read('components/stock/AdjustmentRequestModal.vue');

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Liste : droits par rôle (écran partagé admin, assistant, secrétaire), recherche, filtres, demandes ---
check('StockList (droits)', list, [
    "const isAdmin = computed(() => authStore.hasRole(['admin']))",
    "const isSecretary = computed(() => authStore.hasRole(['secretaire']))",
    'v-if="!isSecretary" @click="openModal(null)"',
    'v-if="isSecretary" @click="openRequest(prod)"',
    'v-if="!isSecretary" @click="openModal(prod)"',
    `v-if="isAdmin && getExpiryStatus(prod.expiryDate) === 'EXPIRED' && prod.quantity > 0" @click="handleDispose(prod)"`,
    'v-if="isAdmin" @click="confirmDelete(prod)"',
    'v-if="isSecretary"', ':can-edit-quantity="isAdmin"',
    'if (isSecretary.value) loadMyRequests();', 'if (isSecretary.value) return;',
]);

test('StockList : les gardes « if (!isAdmin.value) return; » restent aux deux actions admin (mise au rebut, suppression)', () => {
    assert.equal((list.match(/if \(!isAdmin\.value\) return;/g) || []).length, 2);
});

check('StockList (logique)', list, [
    'stockStore.fetchStock()', 'stockStore.fetchStats()',
    "StockOpsGateway.listAdjustmentRequests({ mineOnly: true })", 'StockOpsGateway.cancelAdjustmentRequest(r.id)',
    "window.confirm(t('stockOps.confirm_cancel'))", 'describeStockError(err, t(',
    'stockStore.setFilters({ searchQuery: searchInput.value })', 'stockStore.setFilters({ categoryFilter: val })',
    "stockStore.setFilters({ categoryFilter: 'ALL', searchQuery: '' })", 'stockStore.setPage(page)',
    'stockStore.saveProduct(updatedProduct)', 'stockStore.saveProduct(product, { canSetQuantity: isAdmin.value })',
    'stockStore.deleteProduct(product.id)', '@input="onSearchInput"', '@keyup.enter="searchNow"', '}, 300);',
    'v-model="categoryFilter"', 'value="ALL"', 'value="PHARMA"', 'value="NATUREL"', 'value="MATERIEL"', 'value="EXPIRED_ONLY"',
    'confirm(`Sortir ${product.name} du stock (PÉRIMÉ) ?`)', 'confirm("Supprimer ce produit ?")',
    'threeMonthsFromNow.setMonth(today.getMonth() + 3)', "if (expiry < today) return 'EXPIRED';", "if (expiry < threeMonthsFromNow) return 'SOON';",
    'prod.quantity <= prod.minThreshold', "r.status === 'en_attente'", ':disabled="cancellingId === r.id"',
    '@created="onRequestCreated"', '@save="handleSave"', 'stockStore.pagination.total_pages', 'formatCurrency(stockStore.currentFilteredValue)',
    'stockStore.stats.countPharma', 'stockStore.stats.countNatural', 'stockStore.stats.lowStockAlerts', 'stockStore.stats.expiredCount',
    "currency: 'XAF'", ".replace('XOF', 'FCFA')", "requestProduct.value = { id: prod.id, name: prod.name, quantity: prod.quantity }",
]);

// --- Fiche produit ---
check('ProductModal', product, [
    "defineEmits(['close', 'save'])", "emit('save', { ...form })", 'canEditQuantity: { type: Boolean, default: true }',
    "form.forme = 'Autre';", "form.dosage = '';", "if (form.category !== 'PHARMA')",
    'v-model="form.name"', 'v-model="form.category"', 'v-model.number="form.price"', 'v-model="form.forme"', 'v-model="form.dosage"',
    'v-model.number="form.quantity"', 'v-model.number="form.minThreshold"', 'v-model="form.expiryDate"',
    'v-if="canEditQuantity"', 'v-if="form.category === \'PHARMA\'"', 'Object.assign(form, newVal)', "if (!form.forme) form.forme = 'Autre';",
    "value: 'Comprimé'", "value: 'Sirop'", "value: 'Injection'", "value: 'Pommade'", "value: 'Gélule'", "value: 'Sachet'", "value: 'Autre'",
    "t('stockAdjust.qty_readonly_edit')", "t('stockAdjust.qty_readonly_create')",
    'Optionnel pour le matériel non périssable.', 'Seuil Alerte', 'Dosage (mg/ml)', 'Mettre à jour', 'required min="0"',
    "t('stock.modal.edit_title')", "t('stock.modal.add_title')", "t('stock.modal.name')", "t('stock.modal.category')", "t('stock.modal.price')",
    "t('stock.modal.qty')", "t('stock.modal.expiry')", "t('common.cancel')", "t('common.save')",
]);

// --- Demande d'ajustement (secrétaire) ---
check('AdjustmentRequestModal', request, [
    "defineEmits(['close', 'created'])", "emit('created', created)", 'validateAdjustmentRequest(form)',
    "t(`stockAdjust.err_${check.error}`)", "StockOpsGateway.createAdjustmentRequest({",
    'product_id: props.product.id', 'kind: form.kind', 'quantity: form.quantity', 'reason: form.reason.trim()',
    "describeStockError(err, t('stockOps.error_save'))", 'v-model="form.kind"', 'v-model.number="form.quantity"', 'v-model="form.reason"',
    `:min="form.kind === 'correction' ? 0 : 1"`, 'maxlength="2000"', 'v-for="k in ADJUSTMENT_KINDS"',
    "$t('stockAdjust.modal_title')", "$t('stockAdjust.current_stock')", "$t('stockAdjust.col_kind')", "$t(`stockAdjust.kind.${k}`)",
    "$t(`stockAdjust.kind_help.${form.kind}`)", "$t('stockOps.col_quantity')", "$t('stockOps.col_reason')", "$t('stockOps.close')",
    "$t('stockOps.saving')", "$t('stockAdjust.send')", ':disabled="saving"',
]);

// --- Toutes les clés citées existent ---
test('chaque clé stock.* / stockAdjust.* / stockOps.* citée littéralement existe en FR et EN', () => {
    const used = new Set();
    for (const src of [list, product, request]) {
        for (const m of src.matchAll(/['"`(]((?:stock|stockAdjust|stockOps|users\.table|common)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 25);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

test('clés ajoutées en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        for (const k of ['stock_change', 'prev_page', 'next_page', 'filter_reset', 'section_product', 'section_stock']) {
            assert.equal(typeof msgs[locale].stockScreens?.[k], 'string', `${locale}.stockScreens.${k}`);
        }
    }
});

// --- Refonte ---
test('les écrans utilisent la bibliothèque ui/ (tableau responsive, panneau, sections, barre d’actions)', () => {
    for (const [name, src] of [['list', list], ['product', product], ['request', request]]) {
        assert.match(src, /@\/components\/ui/, `${name}: aucun composant ui/`);
    }
    assert.match(list, /ResponsiveTable/);
    assert.match(product, /FullScreenPanel/);
    assert.match(product, /FormSection/);
    assert.match(product, /ActionBar/);
    assert.match(request, /FullScreenPanel/);
    assert.doesNotMatch(product, /components\/common\/Modal\.vue/);
});

test('couleurs par jetons, texte >= 13 px, aucun caractère typographique interdit', () => {
    for (const [name, src] of [['list', list], ['product', product], ['request', request]]) {
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, `${name}: hexadécimal`);
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/, `${name}: couleur brute`);
        assert.doesNotMatch(src, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/, `${name}: texte trop petit`);
        assert.doesNotMatch(src.slice(0, src.indexOf('<script')), /[—–…·→✕]/u, `${name}: caractère typographique`);
    }
});

test('le statut de péremption et la quantité basse s’écrivent en toutes lettres (jamais la couleur seule)', () => {
    assert.match(list, /StatusBadge/);
    assert.match(list, /BAS/);
});
