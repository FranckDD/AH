import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const modal = read('components/stock/ProductModal.vue');
const store = read('stores/stockStore.js');

// Defaut releve par les guides (2026-10-26) : un produit stocke 'Autre' est lu
// comme categorie AUTRE par stockStore, mais le select de ProductModal n'avait
// pas cette option : liste vide, et l'enregistrement pouvait changer la categorie.
test('le store lit une categorie inconnue/Autre comme AUTRE et la renvoie comme Autre', () => {
  assert.ok(store.includes("let cat = 'AUTRE';"));
  assert.ok(read('utils/productApi.js').includes("let typeDb = 'Autre';"));
});

test('le select de categorie propose toutes les valeurs que le store peut produire', () => {
  const select = modal.slice(modal.indexOf('id="product-category"'), modal.indexOf('</select>'));
  for (const v of ['PHARMA', 'NATUREL', 'MATERIEL', 'AUTRE']) {
    assert.ok(select.includes(`<option value="${v}">`), v);
  }
  assert.ok(select.includes("t('stock.categories.AUTRE')"));
});
