import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
    DISCHARGE_REASONS, dischargeReasonLabelKey, validateDischarge, groupByStay, apiErrorMessage, sortNewestFirst, isFinishedStatus,
} from '../src/utils/toxicoStays.js';

test('DISCHARGE_REASONS lists the 4 backend values', () => {
    assert.deepEqual(DISCHARGE_REASONS, ['guerison', 'abandon', 'exclusion', 'autre']);
});

test('dischargeReasonLabelKey maps known and unknown reasons', () => {
    for (const r of DISCHARGE_REASONS) assert.equal(dischargeReasonLabelKey(r), `toxico.stays.reason.${r}`);
    assert.equal(dischargeReasonLabelKey('xyz'), 'toxico.stays.reason.unknown');
    assert.equal(dischargeReasonLabelKey(null), 'toxico.stays.reason.unknown');
    assert.equal(dischargeReasonLabelKey('__proto__'), 'toxico.stays.reason.unknown');
});

test('validateDischarge', () => {
    assert.deepEqual(validateDischarge({ reason: '' }), ['toxico.stays.errors.reason_required']);
    assert.deepEqual(validateDischarge({ reason: 'bad' }), ['toxico.stays.errors.reason_required']);
    assert.deepEqual(validateDischarge({ reason: 'guerison' }), []);
    assert.deepEqual(validateDischarge({ reason: 'autre', note: '   ' }), ['toxico.stays.errors.note_required']);
    assert.deepEqual(validateDischarge({ reason: 'autre', note: 'parti' }), []);
    assert.deepEqual(validateDischarge({ reason: 'abandon', note: 'x'.repeat(2001) }), ['toxico.stays.errors.note_too_long']);
});

test('groupByStay groups by stay in chronological order, legacy last', () => {
    const stays = [
        { stay_number: 2, admission_date: '2026-05-01', is_open: true },
        { stay_number: 1, admission_date: '2026-01-01', discharge_date: '2026-03-01', is_open: false },
    ];
    const items = [
        { id: 'a', stay_number: 1 }, { id: 'b', stay_number: 2 }, { id: 'c', stay_number: null },
        { id: 'd', stay_number: 1 }, { id: 'e' },
    ];
    const groups = groupByStay(items, stays);
    assert.deepEqual(groups.map((g) => g.stay?.stay_number ?? 'legacy'), [1, 2, 'legacy']);
    assert.deepEqual(groups[0].items.map((i) => i.id), ['a', 'd']);
    assert.deepEqual(groups[1].items.map((i) => i.id), ['b']);
    assert.deepEqual(groups[2].items.map((i) => i.id), ['c', 'e']);
    assert.equal(groups[2].legacy, true);
});

test('groupByStay keeps empty stays and omits empty legacy group', () => {
    const groups = groupByStay([], [{ stay_number: 1, is_open: true }]);
    assert.equal(groups.length, 1);
    assert.deepEqual(groups[0].items, []);
    assert.deepEqual(groupByStay(null, null), []);
});

test('apiErrorMessage reads string and pydantic details', () => {
    assert.equal(apiErrorMessage({ response: { data: { detail: 'deja sorti' } } }, 'f'), 'deja sorti');
    assert.equal(apiErrorMessage({ response: { data: { detail: [{ msg: 'Value error, note' }] } } }, 'f'), 'note');
    assert.equal(apiErrorMessage({}, 'fallback'), 'fallback');
});

test('sortNewestFirst + groupByStay keeps newest first inside each stay', () => {
    const items = [
        { id: 'old', date: '2026-01-02', stay_number: 1 },
        { id: 'new', date: '2026-02-10T09:00:00', stay_number: 1 },
        { id: 's2', date: '2026-05-02', stay_number: 2 },
    ];
    const groups = groupByStay(sortNewestFirst(items), [{ stay_number: 2 }, { stay_number: 1 }]);
    assert.deepEqual(groups.map((g) => g.items.map((i) => i.id)), [['new', 'old'], ['s2']]);
    assert.deepEqual(sortNewestFirst(null), []);
});

test('isFinishedStatus', () => {
    assert.equal(isFinishedStatus('Terminé'), true);
    assert.equal(isFinishedStatus('terminee'), true);
    assert.equal(isFinishedStatus('En cours'), false);
    assert.equal(isFinishedStatus(null), false);
});

// Parite des cles i18n utilisees par l'interface sejours.
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const FILES = [
    '../src/utils/toxicoStays.js',
    '../src/components/toxico/ToxicoDischargeModal.vue',
    '../src/components/toxico/ToxicoStaysTimeline.vue',
    '../src/components/toxico/ToxicoAdmissionModal.vue',
    '../src/components/toxico/ToxicoDossierModal.vue',
    '../src/views/modules/toxico/ToxicoList.vue',
];
const keys = new Set();
for (const f of FILES) {
    const src = readFileSync(new URL(f, import.meta.url), 'utf8');
    for (const m of src.matchAll(/['"`](toxico\.stays\.[\w.]+)['"`]/g)) keys.add(m[1]);
}
['retry', 'recommendation', 'readmission_success'].forEach((k) => keys.add(`toxico.stays.${k}`));
DISCHARGE_REASONS.concat('unknown').forEach((r) => keys.add(`toxico.stays.reason.${r}`));
const get = (obj, path) => path.split('.').reduce((o, p) => (o == null ? undefined : o[p]), obj);
for (const loc of ['fr', 'en']) {
    test(`toxico stays keys exist in ${loc}`, () => {
        const msgs = i18n.global.getLocaleMessage(loc);
        assert.ok(keys.size > 15, `only ${keys.size} keys found`);
        for (const k of keys) assert.equal(typeof get(msgs, k), 'string', `missing ${loc}: ${k}`);
    });
}

test('readmissionPrefill reprend le referent actuel du dossier (psychologistId) ou null', async () => {
    const { readmissionPrefill } = await import('../src/utils/toxicoStays.js');
    assert.equal(readmissionPrefill({ psychologistId: 7, stays: [] }).psychologist, 7);
    assert.equal(readmissionPrefill({ stays: [] }).psychologist, null);
});

test('validateTransfer returns the error key of the first problem, empty when valid', async () => {
    const { validateTransfer } = await import('../src/utils/toxicoStays.js');
    assert.deepEqual(validateTransfer({ toPsychologistId: null, currentPsychologistId: 3, reason: 'x' }), ['toxico.transfer.errors.target_required']);
    assert.deepEqual(validateTransfer({ toPsychologistId: 3, currentPsychologistId: 3, reason: 'x' }), ['toxico.transfer.errors.same_referent']);
    assert.deepEqual(validateTransfer({ toPsychologistId: 4, currentPsychologistId: 3, reason: '   ' }), ['toxico.transfer.errors.reason_required']);
    assert.deepEqual(validateTransfer({ toPsychologistId: 4, currentPsychologistId: 3, reason: 'a'.repeat(1001) }), ['toxico.transfer.errors.reason_too_long']);
    assert.deepEqual(validateTransfer({ toPsychologistId: 4, currentPsychologistId: null, reason: 'a'.repeat(1000) }), []);
    assert.deepEqual(validateTransfer({ toPsychologistId: 4, currentPsychologistId: 3, reason: ' Surcharge ' }), []);
});

test('transferItems keeps the transfer stay, falls back to the last stay, empty list stays empty', async () => {
    const { transferItems } = await import('../src/utils/toxicoStays.js');
    const stays = [{ stay_number: 1 }, { stay_number: 2 }];
    const tr = (o) => ({ id: 1, decided_at: '2026-10-20T10:00:00', from_name: 'A', to_name: 'B', decided_by_name: 'C', reason: 'r', stay_number: null, ...o });
    const [withStay] = transferItems([tr({ stay_number: 1 })], stays);
    assert.deepEqual(withStay, { kind: 'transfer', date: '2026-10-20T10:00:00', stay_number: 1, from_name: 'A', to_name: 'B', decided_by_name: 'C', reason: 'r' });
    assert.equal(transferItems([tr({})], stays)[0].stay_number, 2);
    assert.equal(transferItems([tr({})], [])[0].stay_number, null);
    assert.deepEqual(transferItems([], stays), []);
    assert.deepEqual(transferItems(undefined, stays), []);
});
