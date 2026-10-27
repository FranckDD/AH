import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const list = read('views/modules/stock/StockList.vue');
const modal = read('components/stock/ProductModal.vue');
const labels = read('components/stock/LabelPrintModal.vue');
const config = read('views/SystemConfig.vue');
const store = read('stores/stockStore.js');

test('StockList : boutons etiquettes reserves aux roles de gestion, jamais la secretaire', () => {
    assert.match(list, /const canManageLabels = computed\(\(\) => authStore\.hasRole\(\['admin', 'Assistant', 'ToxicoManager'\]\)\)/);
    assert.doesNotMatch(list, /canManageLabels[^\n]*secretaire/);
    // chaque bouton d'etiquettes porte la condition de role
    for (const m of list.matchAll(/<AppButton[^>]*openLabels\([^>]*>/g)) {
        assert.match(m[0], /v-if="canManageLabels/);
    }
    assert.match(list, /openLabels = \(prod\) => \{\s*if \(!canManageLabels\.value\) return;/);
    assert.match(list, /<LabelPrintModal/);
});

test('ProductModal : section photo reservee aux gestionnaires, code en lecture seule', () => {
    assert.match(modal, /const canManage = computed\(\(\) => authStore\.hasRole\(\['admin', 'Assistant', 'ToxicoManager'\]\)\)/);
    assert.match(modal, /<FormSection v-if="isEditing && canManage"/);
    // le code n'est affiche que dans un paragraphe, jamais dans un champ de saisie
    assert.match(modal, /data-testid="product-code"[^>]*>\{\{ form\.barcode/);
    assert.doesNotMatch(modal, /v-model(?:\.\w+)*="form\.barcode"/);
    assert.doesNotMatch(modal, /v-model(?:\.\w+)*="form\.(hasPhoto|photoVersion)"/);
    assert.match(modal, /accept="image\/jpeg,image\/png,image\/webp"/);
    assert.match(modal, /5 \* 1024 \* 1024/);
    assert.match(modal, /window\.confirm\(t\('stockLabels\.confirm_remove'\)\)/);
});

test('le store expose barcode, hasPhoto, photoVersion', () => {
    assert.match(store, /barcode: p\.barcode/);
    assert.match(store, /hasPhoto: !!p\.has_photo/);
    assert.match(store, /photoVersion: Number\(p\.photo_version\)/);
});

test('LabelPrintModal : regle @page, mode rouleau par defaut, taille de la configuration', () => {
    assert.match(labels, /const mode = ref\('roll'\)/);
    assert.match(labels, /label_width_mm/);
    assert.match(labels, /\.print\(\)/);
    assert.match(labels, /MAX_COPIES/);
    const html = read('utils/labelPrintHtml.js');
    assert.match(html, /@page \{ size: \$\{mm\(first\.widthMm\)\} \$\{mm\(first\.heightMm\)\}; margin: 0; \}/);
    assert.match(html, /@page \{ size: A4 portrait; margin: 0; \}/);
});

test('SystemConfig : champs de taille d etiquette ajoutes sans toucher aux autres champs', () => {
    assert.match(config, /id="cfg-label-width"/);
    assert.match(config, /id="cfg-label-height"/);
    assert.match(config, /label_width_mm: 50, label_height_mm: 30/);
    for (const field of ['niu', 'rccm', 'po_box', 'address']) assert.match(config, new RegExp(`${field}:`));
});

const flat = (o, prefix = '') => Object.entries(o).flatMap(([k, v]) => (
    v && typeof v === 'object' ? flat(v, `${prefix}${k}.`) : [`${prefix}${k}`]
));

test('i18n : memes cles FR/EN pour stockLabels et la taille d etiquette', () => {
    assert.deepEqual(flat(msgs.fr.stockLabels).sort(), flat(msgs.en.stockLabels).sort());
    for (const k of ['label_title', 'label_width', 'label_height', 'label_size_help', 'label_size_invalid']) {
        assert.ok(msgs.fr.configScreens[k], `fr ${k}`);
        assert.ok(msgs.en.configScreens[k], `en ${k}`);
    }
});

test('textes visibles sans tirets longs, fleches, points de suspension ni point median', () => {
    const bad = /[–—→←…·]/;
    for (const lang of ['fr', 'en']) {
        for (const key of flat(msgs[lang].stockLabels)) {
            const v = key.split('.').reduce((o, k) => o[k], msgs[lang].stockLabels);
            assert.doesNotMatch(v, bad, `${lang} ${key}`);
        }
        for (const k of ['label_title', 'label_width', 'label_height', 'label_size_help', 'label_size_invalid']) {
            assert.doesNotMatch(msgs[lang].configScreens[k], bad);
        }
    }
});
