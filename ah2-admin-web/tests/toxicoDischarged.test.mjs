import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
    buildDischargedQuery, dischargedDateRangeError, toPreselectedPatient, clampDischargedPage, displayName,
} from '../src/utils/toxicoDischarged.js';

test('buildDischargedQuery drops empty values and trims search', () => {
    assert.deepEqual(buildDischargedQuery({ page: 1, per_page: 20, search: '  ', reason: '', from: '', to: null }),
        { page: 1, per_page: 20 });
    assert.deepEqual(buildDischargedQuery({ page: 3, per_page: 10, search: ' Dupont ', reason: 'abandon', from: '2026-01-01', to: '2026-02-01' }),
        { page: 3, per_page: 10, search: 'Dupont', reason: 'abandon', discharged_from: '2026-01-01', discharged_to: '2026-02-01' });
});

test('buildDischargedQuery ignores unknown reason and bad pagination', () => {
    assert.deepEqual(buildDischargedQuery({ reason: 'xyz', page: 0, per_page: 999 }), { page: 1, per_page: 100 });
    assert.deepEqual(buildDischargedQuery(), { page: 1, per_page: 20 });
});

test('dischargedDateRangeError', () => {
    assert.equal(dischargedDateRangeError('2026-02-01', '2026-01-01'), 'toxico.discharged.errors.date_range');
    assert.equal(dischargedDateRangeError('2026-01-01', '2026-01-01'), null);
    assert.equal(dischargedDateRangeError('', '2026-01-01'), null);
});

test('toPreselectedPatient maps a discharged row to the admission modal shape', () => {
    assert.deepEqual(toPreselectedPatient({ patient_id: 5, patientName: 'Jean Paul Dupont', code: 'P-5' }),
        { patient_id: 5, first_name: 'Jean Paul Dupont', last_name: '', code_patient: 'P-5' });
    assert.equal(toPreselectedPatient(null), null);
});

test('clampDischargedPage', () => {
    assert.equal(clampDischargedPage(3, 41, 20, 1), null);       // page valide non vide
    assert.equal(clampDischargedPage(3, 40, 20, 0), 2);          // derniere page videe
    assert.equal(clampDischargedPage(5, 21, 20, 0), 2);          // au-dela de la fin -> derniere
    assert.equal(clampDischargedPage(4, 30, 20, 5), 2);          // page > total_pages
    assert.equal(clampDischargedPage(1, 0, 20, 0), null);        // vraiment vide
    assert.equal(clampDischargedPage(1, 5, 20, 0), null);        // page 1 : pas de boucle
    assert.equal(clampDischargedPage(2, 0, 20, 0), null);
});

test('displayName skips empty parts', () => {
    assert.equal(displayName('Jean Dupont', ''), 'Jean Dupont');
    assert.equal(displayName(' Jean ', null, 'Dupont'), 'Jean Dupont');
    assert.equal(displayName('', undefined), '');
});

// Parite FR/EN des cles toxico.discharged.*
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const FILES = ['../src/utils/toxicoDischarged.js', '../src/views/modules/toxico/ToxicoList.vue', '../src/components/toxico/ToxicoDischargedPanel.vue',
    '../src/components/toxico/ToxicoDossierModal.vue'];
const keys = new Set();
for (const f of FILES) {
    const src = readFileSync(new URL(f, import.meta.url), 'utf8');
    for (const m of src.matchAll(/['"`](toxico\.discharged\.[\w.]+)['"`]/g)) keys.add(m[1]);
}
const get = (obj, path) => path.split('.').reduce((o, p) => (o == null ? undefined : o[p]), obj);
for (const loc of ['fr', 'en']) {
    test(`toxico discharged keys exist in ${loc}`, () => {
        const msgs = i18n.global.getLocaleMessage(loc);
        assert.ok(keys.size > 15, `only ${keys.size} keys found`);
        for (const k of keys) assert.equal(typeof get(msgs, k), 'string', `missing ${loc}: ${k}`);
    });
}
