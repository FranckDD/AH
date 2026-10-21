import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const FILES = [
    '../src/components/patients/medical/MedicalRecordTimeline.vue',
    '../src/views/modules/medical-records/MedicalRecordsList.vue',
    '../src/views/modules/prescriptions/PrescriptionsList.vue',
    '../src/views/modules/sync/SyncFailuresView.vue',
    '../src/powersync-client/DossierConnector.js',
];

const used = new Set();
for (const f of FILES) {
    const src = readFileSync(new URL(f, import.meta.url), 'utf8');
    for (const m of src.matchAll(/['"`](medical\.readonly\.[\w]+)['"`]/g)) used.add(m[1]);
}

const get = (obj, path) => path.split('.').reduce((o, p) => (o == null ? undefined : o[p]), obj);

test('readonly keys are used by the views', () => {
    for (const k of ['badge', 'sync_rejected_record', 'sync_rejected_prescription', 'quarantine_title', 'quarantine_dismiss']) {
        assert.ok(used.has(`medical.readonly.${k}`), k);
    }
});

for (const loc of ['fr', 'en']) {
    test(`consultation readonly keys exist in ${loc}`, () => {
        const msgs = i18n.global.getLocaleMessage(loc);
        for (const k of used) assert.equal(typeof get(msgs, k), 'string', `missing ${loc}: ${k}`);
    });
}

test('fr and en readonly groups have the same keys', () => {
    const fr = Object.keys(get(i18n.global.getLocaleMessage('fr'), 'medical.readonly')).sort();
    const en = Object.keys(get(i18n.global.getLocaleMessage('en'), 'medical.readonly')).sort();
    assert.deepEqual(fr, en);
});
