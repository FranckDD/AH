import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const modal = read('src/components/toxico/ToxicoTransferModal.vue');
const list = read('src/views/modules/toxico/ToxicoList.vue');
const dossier = read('src/components/toxico/ToxicoDossierModal.vue');
const timeline = read('src/components/toxico/ToxicoStaysTimeline.vue');
const bell = read('src/components/notifications/NotificationBell.vue');
const gateway = read('src/services/ToxicoGateway.js');
const store = read('src/stores/toxicoStore.js');

test('transfer modal: props, emits, validation, server error, 44 px targets, no role check inside', () => {
    for (const needle of ['dossierId', 'patientName', 'currentPsychologistId', 'currentPsychologistName', "'close'", "'transferred'",
        'validateTransfer', 'apiErrorMessage', 'min-h-11', 'FullScreenPanel', 'transferDossier']) {
        assert.ok(modal.includes(needle), `modal misses ${needle}`);
    }
    assert.doesNotMatch(modal, /hasRole/);
    assert.doesNotMatch(modal, /v-if="[^"]*(role|Role)/);
    assert.match(modal, /\.filter\(\(p\) => p\.id !== props\.currentPsychologistId\)/);
});

test('gateway and store expose transferDossier (POST body to_psychologist_id + reason, reloads list and stats)', () => {
    assert.match(gateway, /\/toxico\/dossiers\/\$\{dossierId\}\/transfer/);
    assert.match(gateway, /to_psychologist_id/);
    assert.match(store, /async function transferDossier\(dossierId, \{ toPsychologistId, reason \}/);
    assert.match(store, /transferDossier[\s\S]{0,400}fetchToxicoPatients\(\)[\s\S]{0,100}fetchDashboardStats\(\)/);
});

test('list: transfer button gated by canTransferPatient, deep link reacts to query changes and clears it', () => {
    assert.match(list, /v-if="canTransferPatient"/);
    assert.match(list, /hasRole\(TOXICO_TRANSFER_ROLES\)/);
    assert.match(list, /ToxicoTransferModal/);
    assert.match(list, /openFromQuery\(route\.query\.patient\)/);
    assert.doesNotMatch(list, /router\.replace\(/);
    assert.doesNotMatch(list, /useRouter/);
    assert.doesNotMatch(list, /watch\(\(\) => route\.query\.patient/);
    assert.match(list, /window\.history\.replaceState\(window\.history\.state, '', /);
    assert.match(list, /searchParams\.delete\('patient'\)/);
    assert.match(list, /route\.fullPath/);
    assert.match(list, /AppShell/);
});

test('timeline: automatic Readmission reason is translated, key in FR and EN', () => {
    assert.match(timeline, /toxico\.transfer\.reason_readmission/);
    assert.match(timeline, /=== 'Readmission'/);
    const i18n = read('src/i18n.js');
    assert.match(i18n, /reason_readmission: "Réadmission"/);
    assert.match(i18n, /reason_readmission: "Readmission"/);
});

test('dossier modal: transfer button for active or discharged files, never read-only', () => {
    assert.match(dossier, /v-if="canTransfer"/);
    assert.match(dossier, /const canTransfer = computed\(\(\) => !isReadOnly\.value && authStore\.hasRole\(TOXICO_TRANSFER_ROLES\)\)/);
    assert.match(dossier, /ToxicoTransferModal/);
    assert.match(dossier, /:transfers="patient\.transfers/);
});

test('timeline shows transfer entries with history_line and history_reason', () => {
    assert.match(timeline, /item\.kind === 'transfer'/);
    assert.match(timeline, /toxico\.transfer\.history_line/);
    assert.match(timeline, /toxico\.transfer\.history_reason/);
    assert.match(timeline, /transferItems/);
});

test('bell labels and opens the toxico_transfer notification on the real route', () => {
    assert.equal((bell.match(/n\.type === 'toxico_transfer'/g) || []).length, 2); // labelFor + handleClick
    assert.match(bell, /pushIfRoute\('\/dashboard\/toxico\?patient=' \+ n\.payload\.patient_id\)/);
});

const KEYS = [
    'toxico.transfer.action', 'toxico.transfer.title', 'toxico.transfer.current', 'toxico.transfer.no_referent', 'toxico.transfer.target_label',
    'toxico.transfer.target_placeholder', 'toxico.transfer.reason_label', 'toxico.transfer.reason_placeholder', 'toxico.transfer.submit',
    'toxico.transfer.submitting', 'toxico.transfer.cancel', 'toxico.transfer.success', 'toxico.transfer.errors.target_required',
    'toxico.transfer.errors.same_referent', 'toxico.transfer.errors.reason_required', 'toxico.transfer.errors.reason_too_long',
    'toxico.transfer.history_label', 'toxico.transfer.history_line', 'toxico.transfer.history_reason', 'toxico.transfer.reason_readmission', 'notifications.toxico_transfer',
    'serverErrors.not_referent', 'serverErrors.transfer_target_invalid', 'serverErrors.transfer_same_referent',
    'serverErrors.transfer_reason_required', 'serverErrors.read_only_access',
];

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const get = (o, k) => k.split('.').reduce((a, p) => (a == null ? undefined : a[p]), o);
for (const loc of ['fr', 'en']) {
    test(`every transfer i18n key exists in ${loc}`, () => {
        const msgs = i18n.global.getLocaleMessage(loc);
        for (const k of KEYS) assert.equal(typeof get(msgs, k), 'string', `missing ${loc}: ${k}`);
    });
}

test('keys used in source exist in the list above (no new key left out)', () => {
    const files = ['src/components/toxico/ToxicoTransferModal.vue', 'src/components/toxico/ToxicoStaysTimeline.vue', 'src/utils/toxicoStays.js'];
    for (const f of files) {
        for (const m of read(f).matchAll(/['"`](toxico\.transfer\.[\w.]+)['"`]/g)) assert.ok(KEYS.includes(m[1]), `${f} uses unlisted ${m[1]}`);
    }
});
