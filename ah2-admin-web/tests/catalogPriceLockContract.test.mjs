// Prix unitaire verrouille au catalogue pour la secretaire (2026-10-24).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

const modal = readFileSync(new URL('../src/components/caisse/CaisseInvoiceModal.vue', import.meta.url), 'utf8');
const bell = readFileSync(new URL('../src/components/notifications/NotificationBell.vue', import.meta.url), 'utf8');
const templateOf = (src) => src.slice(0, src.indexOf('<script'));
const scriptOf = (src) => src.slice(src.indexOf('<script'));

test('regle de role : seuls admin et promoteur saisissent librement (hasRole)', () => {
    assert.ok(scriptOf(modal).includes("const canEditCatalogPrice = computed(() => authStore.hasRole(['admin', 'promoteur']));"));
});

test('types a prix catalogue : medicament et examen des la creation, consultation FamilyRestoration a la selection', () => {
    const s = scriptOf(modal);
    assert.ok(s.includes("catalogLine: itemType === 'Médicament' || itemType === 'Examen',"));
    assert.ok(s.includes("line.catalogLine = consultation.type_consultation === 'FamilyRestoration';"));
    assert.ok(s.includes('const isPriceLocked = (line) => !canEditCatalogPrice.value && line.catalogLine;'));
    assert.ok(s.includes('const isPriceUndefined = (line) => isPriceLocked(line) && line.refId !== null && !(Number(line.unitPrice) > 0);'));
});

test('une ligne a prix non defini ne peut pas etre validee', () => {
    assert.ok(scriptOf(modal).includes('if (isPriceUndefined(line)) return false;'));
});

test('gabarit : prix en lecture seule + aide + message prix non defini', () => {
    const tpl = templateOf(modal);
    assert.ok(tpl.includes(':readonly="isPriceLocked(line)"'));
    assert.ok(tpl.includes(":help=\"isPriceLocked(line) && !isPriceUndefined(line) ? t('caisseInvoice.price_locked_help') : ''\""));
    assert.ok(tpl.includes('v-if="isPriceUndefined(line)"'));
    assert.ok(tpl.includes("t('caisseInvoice.price_undefined')"));
    // le prix reste lie au modele (admin/promoteur, Service, Spiritual)
    assert.ok(tpl.includes('v-model.number="line.unitPrice"'));
});

test('notification price_mismatch : libelle et navigation', () => {
    const s = scriptOf(bell);
    assert.ok(s.includes("if (n.type === 'price_mismatch') {"));
    assert.ok(s.includes("t('notifications.price_mismatch'"));
    assert.ok(s.includes("if (authStore.hasRole(['admin'])) pushIfRoute('/dashboard/finance');"));
    const block = s.slice(s.indexOf('// Journal financier unifie'));
    assert.ok(!block.slice(0, block.indexOf('}')).includes('cash-closures'), 'le promoteur ne navigue pas');
});

const KEYS = ['caisseInvoice.price_locked_help', 'caisseInvoice.price_undefined', 'notifications.price_mismatch',
    'notifications.price_mismatch_undefined'];
const FORBIDDEN = /[–—…·→←\u{1F300}-\u{1FAFF}]/u;

for (const locale of ['fr', 'en']) {
    test(`i18n ${locale} : cles presentes, ASCII de ponctuation uniquement`, () => {
        for (const k of KEYS) {
            const v = pick(msgs[locale], k);
            assert.equal(typeof v, 'string', `${locale}.${k} manquante`);
            assert.ok(!FORBIDDEN.test(v), `${locale}.${k} contient un caractere interdit`);
        }
    });
}

test('textes FR exacts', () => {
    assert.equal(pick(msgs.fr, 'caisseInvoice.price_locked_help'),
        'Prix du catalogue. Pour un autre prix, faites une demande de réduction.');
    assert.equal(pick(msgs.fr, 'caisseInvoice.price_undefined'), "Prix non défini, contactez l'administrateur.");
    for (const k of ['notifications.price_mismatch', 'notifications.price_mismatch_undefined']) {
        assert.ok(pick(msgs.fr, k).includes('hors ligne avant un changement de prix'), k);
        assert.ok(pick(msgs.en, k).includes('offline sale made before a price change'), k);
    }
});

test('ProductModal : prix decimal accepte (step any, min 0)', () => {
    const pm = readFileSync(new URL('../src/components/stock/ProductModal.vue', import.meta.url), 'utf8');
    assert.ok(pm.includes('v-model.number="form.price" type="number" required min="0" step="any"'));
});
