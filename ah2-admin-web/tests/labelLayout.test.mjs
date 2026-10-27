import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildLabelPages, MAX_NAME_LENGTH } from '../src/utils/labelLayout.js';

const size = { widthMm: 50, heightMm: 30 };
const item = (name, copies = 1) => ({ name, barcode: '12345678', copies });

test('roll : 3 produits x 2 copies donnent 6 pages de la taille demandee', () => {
    const pages = buildLabelPages([item('A', 2), item('B', 2), item('C', 2)], size, 'roll');
    assert.equal(pages.length, 6);
    for (const p of pages) {
        assert.equal(p.widthMm, 50);
        assert.equal(p.heightMm, 30);
        assert.equal(p.labels.length, 1);
    }
});

test('a4 : 100 etiquettes se repartissent sur plusieurs pages sans depassement', () => {
    const pages = buildLabelPages([item('Produit', 100)], size, 'a4');
    assert.ok(pages.length > 1);
    let total = 0;
    for (const p of pages) {
        assert.equal(p.widthMm, 210);
        assert.equal(p.heightMm, 297);
        assert.ok(p.columns >= 1 && p.rows >= 1);
        for (const l of p.labels) {
            total += 1;
            assert.ok(l.xMm >= 0 && l.yMm >= 0);
            assert.ok(l.xMm + 50 <= 210 + 1e-9, 'depasse en largeur');
            assert.ok(l.yMm + 30 <= 297 + 1e-9, 'depasse en hauteur');
        }
    }
    assert.equal(total, 100);
});

test('a4 : grandes etiquettes (120 x 120) tiennent encore sur la page', () => {
    const pages = buildLabelPages([item('Grand', 5)], { widthMm: 120, heightMm: 120 }, 'a4');
    for (const p of pages) for (const l of p.labels) {
        assert.ok(l.xMm + 120 <= 210 && l.yMm + 120 <= 297);
    }
});

test('copies invalides rejetees', () => {
    for (const copies of [0, -1, 1.5, NaN, '2', null]) {
        assert.throws(() => buildLabelPages([item('A', copies)], size, 'roll'), /copies/);
    }
});

test('nom trop long tronque avec trois points ASCII', () => {
    const long = 'Paracetamol 500 mg comprimes pellicules boite de 100';
    const [page] = buildLabelPages([item(long)], size, 'roll');
    const name = page.labels[0].name;
    assert.ok(name.length <= MAX_NAME_LENGTH);
    assert.ok(name.endsWith('...'));
    assert.match(name, /^[\x20-\x7e]+$/);
    assert.equal(buildLabelPages([item('Court')], size, 'roll')[0].labels[0].name, 'Court');
});

test('taille ou mode invalide rejete', () => {
    for (const bad of [{ widthMm: 19, heightMm: 30 }, { widthMm: 50, heightMm: 121 }, { widthMm: 'x', heightMm: 30 }, { widthMm: NaN, heightMm: 30 }, null]) {
        assert.throws(() => buildLabelPages([item('A')], bad, 'roll'), /size/);
    }
    assert.throws(() => buildLabelPages([item('A')], size, 'poster'), /mode/);
});

test('code-barres manquant rejete', () => {
    assert.throws(() => buildLabelPages([{ name: 'A', barcode: '', copies: 1 }], size, 'roll'), /barcode/);
});
