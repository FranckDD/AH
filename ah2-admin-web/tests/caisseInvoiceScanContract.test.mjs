import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const modal = read('components/caisse/CaisseInvoiceModal.vue');
const panel = read('components/caisse/InvoiceProductPanel.vue');
const fsp = read('components/ui/FullScreenPanel.vue');

test('le modal a un champ de scan qui appelle findProductByBarcode sur Entree', () => {
    assert.match(modal, /id="inv-scan"/);
    assert.match(modal, /@keydown\.enter\.prevent="onScan"/);
    assert.match(modal, /CaisseGateway\.findProductByBarcode\(/);
    assert.match(modal, /normalizeScan\(/);
    assert.match(modal, /applyScanToLines\(/);
});

test('le focus du scan ne vole pas la recherche patient a l ouverture, puis suit patient, scan, retrait et selection', () => {
    assert.doesNotMatch(modal, /onMounted\(focusScan\)/);
    assert.match(modal, /const selectPatient = \(p\) => \{[\s\S]*?focusScan\(\);\s*\};/);
    assert.match(modal, /id="inv-patient-label"[^>]*@keydown\.enter\.prevent="focusScanIfLabel" @blur="focusScanIfLabel"/);
    assert.match(modal, /const focusScanIfLabel = \(\) => \{ if \(patientLabel\.value\.trim\(\)\) focusScan\(\); \};/);
    assert.match(modal, /const removeLine = \(idx\) => \{[\s\S]*?focusScan\(\);/);
    assert.match(modal, /const selectProductLine[\s\S]*?focusScan\(\);/);
    assert.match(modal, /const onScan[\s\S]*?focusScan\(\);\s*\};/);
});

test('code inconnu et erreur reseau affichent un message sans rien ajouter', () => {
    assert.match(modal, /caisseInvoice\.scan_unknown/);
    assert.match(modal, /caisseInvoice\.scan_error/);
    assert.match(modal, /if \(!product\) \{/);
});

test('le modal passe maximizable a FullScreenPanel et montre le panneau produit', () => {
    assert.match(modal, /<FullScreenPanel[^>]*\bmaximizable\b/);
    assert.match(modal, /<InvoiceProductPanel/);
    assert.match(modal, /showInPanel\(product\)/);
    assert.match(modal, /@click="onLineClick\(line\)"/);
    assert.match(panel, /ProductPhotoGateway\.getPhotoUrl/);
    assert.match(fsp, /maximizable: \{ type: Boolean, default: false \}/);
});

test('le flux existant est conserve (recherche par nom, prix verrouille, avertissement de stock)', () => {
    assert.match(modal, /CaisseGateway\.searchProducts\(line\.searchQuery\)/);
    assert.match(modal, /const isPriceLocked = \(line\) => !canEditCatalogPrice\.value && line\.catalogLine;/);
    assert.match(modal, /caisseInvoice\.stock_warning/);
});

test('cles i18n FR/EN identiques et sans caracteres typographiques', () => {
    const keys = ['scan_label', 'scan_placeholder', 'scan_unknown', 'scan_invalid', 'scan_error', 'product_panel', 'product_none', 'product_no_photo', 'product_forme', 'product_dosage', 'product_price', 'product_stock'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].caisseInvoice?.[k];
            assert.equal(typeof v, 'string', `${locale}.caisseInvoice.${k}`);
            assert.doesNotMatch(v, /[\u2013\u2014\u2026\u00b7\u2192]/, `${locale}.${k}`);
        }
        for (const k of ['maximize', 'restore']) assert.equal(typeof msgs[locale].ui?.[k], 'string', `${locale}.ui.${k}`);
    }
});

test('les chiffres de la douchette ne tombent pas dans quantite/prix', () => {
    assert.equal((modal.match(/@keydown\.enter\.prevent="focusScan" @change="returnToScan"/g) || []).length, 2);
    assert.match(modal, /const returnToScan = /);
    assert.match(modal, /addEventListener\('keydown', onStrayDigit, true\)/);
    assert.match(modal, /removeEventListener\('keydown', onStrayDigit, true\)/);
    assert.match(modal, /shouldRedirectToScan\(ev\)/);
    assert.match(modal, /<span class="contents" @click\.stop><AppButton[^>]*@click="removeLine\(idx\)"/);
    assert.match(modal, /panelProduct\.value = null;/);
});
