import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
    buildDischargedExportQuery, exportErrorKey, TOXICO_DOSSIER_EXPORT_ROLES, TOXICO_LIST_EXPORT_ROLES,
    dossierExportFilename, resolveExportSearch,
} from '../src/utils/toxicoExport.js';

test('buildDischargedExportQuery keeps the panel filters, never pagination', () => {
    assert.deepEqual(buildDischargedExportQuery({ page: 3, per_page: 10, search: ' Dupont ', reason: 'abandon', from: '2026-01-01', to: '2026-02-01' }),
        { search: 'Dupont', reason: 'abandon', discharged_from: '2026-01-01', discharged_to: '2026-02-01' });
    assert.deepEqual(buildDischargedExportQuery({ search: '  ', reason: 'xyz', from: '', to: null }), {});
    assert.deepEqual(buildDischargedExportQuery(), {});
});

test('exportErrorKey maps HTTP status to a readable message key', () => {
    assert.equal(exportErrorKey({ response: { status: 403 } }), 'toxico.export.errors.forbidden');
    assert.equal(exportErrorKey({ response: { status: 401 } }), 'toxico.export.errors.forbidden');
    assert.equal(exportErrorKey({ response: { status: 404 } }), 'toxico.export.errors.not_found');
    assert.equal(exportErrorKey({ response: { status: 422 } }), 'toxico.export.errors.invalid');
    assert.equal(exportErrorKey({ response: { status: 500 } }), 'toxico.export.errors.generic');
    assert.equal(exportErrorKey(new Error('network')), 'toxico.export.errors.generic');
    assert.equal(exportErrorKey(undefined), 'toxico.export.errors.generic');
});

test('role lists mirror the backend guards (exact codes)', () => {
    assert.deepEqual([...TOXICO_DOSSIER_EXPORT_ROLES].sort(), ['Psychologist', 'ToxicoManager', 'admin'].sort());
    assert.ok(!TOXICO_DOSSIER_EXPORT_ROLES.includes('Assistant'));
    assert.ok(!TOXICO_DOSSIER_EXPORT_ROLES.includes('SpiritualCounsellor'));
    assert.deepEqual([...TOXICO_LIST_EXPORT_ROLES].sort(),
        ['Assistant', 'Psychologist', 'SpiritualCounsellor', 'ToxicoManager', 'admin'].sort());
});

test('resolveExportSearch prefers a pending debounced value', () => {
    assert.equal(resolveExportSearch('Dup', 'old'), 'Dup');
    assert.equal(resolveExportSearch('', 'old'), '');
    assert.equal(resolveExportSearch(null, 'old'), 'old');
    assert.equal(resolveExportSearch(undefined, undefined), '');
});

test('dossierExportFilename', () => {
    assert.equal(dossierExportFilename(12), 'dossier_toxico_12.pdf');
});

// Parite FR/EN des cles toxico.export.*
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const FILES = ['../src/utils/toxicoExport.js', '../src/components/toxico/ToxicoDischargedPanel.vue',
    '../src/components/toxico/ToxicoDossierModal.vue'];
const keys = new Set();
for (const f of FILES) {
    const src = readFileSync(new URL(f, import.meta.url), 'utf8');
    for (const m of src.matchAll(/['"`](toxico\.export\.[\w.]+)['"`]/g)) keys.add(m[1]);
}
const get = (obj, path) => path.split('.').reduce((o, p) => (o == null ? undefined : o[p]), obj);
for (const loc of ['fr', 'en']) {
    test(`toxico export keys exist in ${loc}`, () => {
        const msgs = i18n.global.getLocaleMessage(loc);
        assert.ok(keys.size >= 7, `only ${keys.size} keys found`);
        for (const k of keys) assert.equal(typeof get(msgs, k), 'string', `missing ${loc}: ${k}`);
    });
}
