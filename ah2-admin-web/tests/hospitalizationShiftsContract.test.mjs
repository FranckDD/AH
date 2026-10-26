import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const hospList = read('views/modules/hospitalization/HospitalizationsList.vue');
const hospCard = read('components/hospitalization/HospitalizationCard.vue');
const shiftsView = read('views/modules/nurseshift/NurseShiftsView.vue');
const shiftCal = read('components/nurseshift/NurseShiftCalendar.vue');
const shiftPanel = read('components/nurseshift/NurseShiftDayPanel.vue');

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// Liste figée de ce que faisaient les écrans avant la refonte : rien ne doit disparaître.
check('HospitalizationsList', hospList, [
    'hospitalizationStore.fetchCurrent()', 'hospitalizationStore.current',
    'router.push(`/medical/patients/${patientId}`)', 'latestStatusOf(stay)', 'stayDuration(stay.admitted_at)',
    "stay.status_updates?.length ? stay.status_updates[0].status : null", 'stay.admitted_by_name', 'goToDossier(stay.patient_id)',
    "dayjs(d).format('DD/MM/YYYY HH:mm')", "'AGGRAVATION'", "'AMELIORATION'",
]);

check('HospitalizationCard', hospCard, [
    'hospitalizationStore.admit(props.patientId, admissionReason.value)',
    'hospitalizationStore.addStatusUpdate(openStay.value.id, newStatus.value, statusNote.value, props.patientId)',
    'hospitalizationStore.discharge(openStay.value.id, dischargeDisposition.value, dischargeNote.value, props.patientId)',
    'hospitalizationStore.fetchPatientHistory(props.patientId)', 'hospitalizationStore.patientHistory',
    'HospitalizationGateway.downloadDischargeLetter(hospitalizationId)',
    'DISCHARGE_DISPOSITIONS', 'CLINICAL_STATUSES', 'if (!openStay.value || !dischargeDisposition.value) return;',
    ':disabled="isSubmitting || !dischargeDisposition"', 'v-model="admissionReason"', 'v-model="newStatus"',
    'v-model="statusNote"', 'v-model="dischargeDisposition"', 'v-model="dischargeNote"',
    '@click="submitAdmit"', '@click="submitStatusUpdate"', '@click="submitDischarge"', '@click="downloadLetter(stay.id)"',
    'showAdmitForm', 'showStatusForm', 'showDischargeForm', "type: Number", 'required: true',
    'v-if="!openStay"', 'v-if="stay.discharge_disposition"', 'downloadingLetterId',
    "lettre_sortie_${hospitalizationId}.pdf",
]);

check('NurseShiftsView', shiftsView, [
    'nurseShiftStore.fetchShifts(start, end)',
    'nurseShiftStore.createShift(selectedDate.value, shiftType, nurseId, currentRange.value.start, currentRange.value.end)',
    'nurseShiftStore.deleteShift(shiftId, currentRange.value.start, currentRange.value.end)',
    'nurseShiftStore.fetchActiveNurses()', "authStore.hasRole(['medecin'])",
    "authStore.hasRole(['nurse']) && !!authStore.user?.is_head_nurse",
    '@day-click="handleDayClick"', '@month-change="handleMonthChange"', ':can-manage="canManage && !nurseShiftStore.error"',
    '@add="handleAdd"', '@remove="handleRemove"', ':available-nurses="nurseShiftStore.activeNurses"',
    'if (!nurseId) return;', 'actionError',
]);

check('NurseShiftCalendar', shiftCal, [
    "defineEmits(['day-click', 'month-change'])", 'emitMonthRange()', "$emit('day-click', day.dateStr)",
    'SHIFT_TYPES', 'nursesByShift', 'goToPreviousMonth', 'goToNextMonth', 'goToToday', 'isToday',
    "format('YYYY-MM-DD')",
]);

check('NurseShiftDayPanel', shiftPanel, [
    "defineEmits(['close', 'add', 'remove'])", "$emit('close')", "$emit('remove', s.id)",
    "emit('add', { shiftType, nurseId })", ':disabled="!selectedNurseByShift[st]"', 'v-if="canManage"',
    'unassignedNursesFor', 'head_nurse_badge', "selectedNurseByShift[shiftType] = ''",
    "{ MATIN: '', APRES_MIDI: '', NUIT: '' }",
]);

test('droits de la chef infirmière : le bouton retirer et l’ajout restent réservés à canManage', () => {
    assert.equal((shiftPanel.match(/v-if="canManage"/g) || []).length >= 2, true);
});

test('la sortie d’hospitalisation garde son motif obligatoire et son bouton d’envoi du formulaire', () => {
    assert.match(hospCard, /disabled="?isSubmitting \|\| !dischargeDisposition|:disabled="isSubmitting \|\| !dischargeDisposition"/);
});

// Clés i18n utilisées avant la refonte.
test('chaque clé citée littéralement dans les écrans existe en FR et EN', () => {
    const used = new Set();
    for (const src of [hospList, hospCard, shiftsView, shiftCal, shiftPanel]) {
        for (const m of src.matchAll(/['"`(]((?:hospitalization|nurseShift|appointments)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 30);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

test('les statuts et dispositions de sortie ont toujours leur libellé FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        for (const s of ['AMELIORATION', 'AGGRAVATION']) {
            assert.equal(typeof msgs[locale].hospitalization.status[s], 'string', `${locale}.status.${s}`);
        }
        assert.ok(Object.keys(msgs[locale].hospitalization.disposition).length >= 2);
    }
});

// Clés ajoutées par la refonte.
test('clés nurseShift.* ajoutées présentes en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        for (const k of ['prev_month', 'next_month', 'nurses_count']) {
            assert.equal(typeof msgs[locale].nurseShift[k], 'string', `${locale}.nurseShift.${k}`);
        }
    }
});

const ALL = [['liste hospitalisations', hospList], ['fiche hospitalisation', hospCard], ['rotations', shiftsView],
    ['calendrier rotations', shiftCal], ['panneau rotations', shiftPanel]];

test('aucune couleur de marque ou d’état en dur dans les écrans refondus', () => {
    for (const [name, src] of ALL) {
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, `${name}: hexadécimal`);
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|green)-\d{2,3}\b/, `${name}: couleur Tailwind brute`);
    }
});

test('les écrans utilisent la bibliothèque ui/', () => {
    for (const [name, src] of ALL) {
        assert.match(src, /@\/components\/ui/, `${name}: aucun composant ui/ importé`);
    }
});

test('texte affiché : ni tiret long, ni flèche, ni points de suspension typographiques', () => {
    for (const [name, src] of ALL) {
        const template = src.slice(0, src.indexOf('<script'));
        assert.doesNotMatch(template, /[—–…·→]/, `${name}: caractère typographique dans le gabarit`);
    }
});

test('texte jamais inférieur à 13 px dans le calendrier des rotations', () => {
    assert.doesNotMatch(shiftCal, /text-\[(1[0-2]|[0-9])px\]/);
    assert.doesNotMatch(shiftCal, /text-xs/);
});

test('alerte d’aggravation : texte et icône, jamais la couleur seule', () => {
    assert.match(hospList, /ExclamationTriangleIcon/);
    assert.match(hospList, /AGGRAVATION/);
    assert.match(hospCard, /ExclamationTriangleIcon/);
});

test('protocole du test d’utilisation présent avec ses cinq tâches types', () => {
    const doc = readFileSync(new URL('../../docs/superpowers/usability-test-protocol-medical.md', import.meta.url), 'utf8');
    for (let i = 1; i <= 5; i++) assert.match(doc, new RegExp(`Tâche ${i}\\b`), `Tâche ${i} absente du protocole`);
    assert.match(doc, /Grille d'observation/);
    assert.match(doc, /Modèle de synthèse/);
    assert.match(doc, /penser à voix haute/i);
});
