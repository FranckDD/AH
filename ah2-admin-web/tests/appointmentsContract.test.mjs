import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const list = read('views/modules/appointments/AppointmentsList.vue');
const modal = read('components/appointments/AppointmentModal.vue');
const calendar = read('components/appointments/AppointmentsCalendar.vue');
const panel = read('components/appointments/AppointmentDayPanel.vue');
const badge = read('components/appointments/StatusBadge.vue');

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// Liste figée de ce que faisaient les écrans avant la refonte : rien ne doit disparaître.
check('AppointmentsList', list, [
    'appointmentStore.startWatchingAppointments()', 'appointmentStore.fetchSpecialties()',
    'appointmentStore.completeAppointment(appt.server_id)', 'appointmentStore.cancelAppointment(appt.server_id)',
    'appointmentStore.updateAppointment(editingAppointment.value.id, data)', 'appointmentStore.createAppointment(data)',
    'appointmentStore.setFilters({ searchQuery: val })', 'appointmentStore.setFilters({ status: val })',
    'appointmentStore.setFilters({ dateMode: val })', 'appointmentStore.setFilters({ customDate: val })',
    'appointmentStore.rawAppointments', 'APPOINTMENT_STATUSES',
    'router.push(`/medical/patients/${appt.patient_id}`)',
    'router.push(`/medical/patients/${appt.patient_id}?appointmentId=${appt.server_id}`)',
    '@day-click="handleDayClick"', '@edit="openEditModal"', '@view-dossier="voirDossier"',
    '@start-consultation="demarrerConsultation"', ':initial-date="createDate"', '@save="handleSave"', '@close="closeModal"',
    "viewMode = 'list'", "viewMode = 'calendar'",
    ':disabled="!appt.server_id"', ':disabled="!appt.patient_id || !appt.server_id"', ':disabled="!appt.patient_id"',
    "appt.status === 'pending'", 'openCreateModal', 'openEditModal(appt)',
]);

check('AppointmentModal', modal, [
    "defineEmits(['close', 'save'])", "emit('save', {",
    'patientId: patientId.value', 'specialty: form.specialty', 'appointmentDate: form.appointmentDate',
    'appointmentTime: form.appointmentTime', 'reason: form.reason', 'doctorId: form.doctorId || null',
    'waitForInitialSync()', 'FROM patients_lookup WHERE code_patient = ?', '/doctor-dashboard/doctors',
    'v-model="patientCode"', '@blur="lookupPatient"', 'v-model="form.specialty"', 'v-model="form.doctorId"',
    'v-model="form.appointmentDate"', 'v-model="form.appointmentTime"', 'v-model="form.reason"',
    ':readonly="isEdit"', 'appointmentStore.specialties', 'timeSlots', 'props.initialDate',
]);

check('AppointmentsCalendar', calendar, [
    "defineEmits(['day-click'])", "$emit('day-click', day.dateStr)", 'MAX_VISIBLE_PER_DAY = 3',
    'goToPreviousMonth', 'goToNextMonth', 'goToToday', 'weekdays_short', 'isToday',
]);

check('AppointmentDayPanel', panel, [
    "defineEmits(['close', 'edit', 'cancel', 'complete', 'view-dossier', 'start-consultation'])",
    "$emit('close')", "$emit('complete', appt)", "$emit('cancel', appt)", "$emit('view-dossier', appt)",
    "$emit('start-consultation', appt)", "$emit('edit', appt)",
    ':disabled="!appt.server_id"', ':disabled="!appt.patient_id"', ':disabled="!appt.patient_id || !appt.server_id"',
]);

check('StatusBadge (rendez-vous)', badge, ['status_completed', 'status_cancelled', 'status_pending']);

// Clés i18n utilisées avant la refonte : doivent rester définies en FR et EN, avec le même texte français.
const FROZEN_KEYS = [
    'appointments.title', 'appointments.subtitle', 'appointments.view_list', 'appointments.view_calendar',
    'appointments.new_appointment', 'appointments.search_label', 'appointments.search_placeholder',
    'appointments.status_label', 'appointments.status_all', 'appointments.date_label', 'appointments.date_all',
    'appointments.date_today', 'appointments.date_custom', 'appointments.results_count',
    'appointments.table.patient', 'appointments.table.phone', 'appointments.table.doctor', 'appointments.table.date',
    'appointments.table.time', 'appointments.table.reason', 'appointments.table.status', 'appointments.table.actions',
    'appointments.actions.complete', 'appointments.actions.cancel', 'appointments.actions.view_dossier',
    'appointments.actions.start_consultation', 'appointments.actions.edit', 'appointments.pending_sync',
    'appointments.empty', 'appointments.status_pending', 'appointments.status_completed', 'appointments.status_cancelled',
    'appointments.modal.title_edit', 'appointments.modal.title_new', 'appointments.modal.patient_code',
    'appointments.modal.specialty', 'appointments.modal.specialty_none', 'appointments.modal.doctor',
    'appointments.modal.doctor_unassigned', 'appointments.modal.date', 'appointments.modal.time',
    'appointments.modal.reason', 'appointments.modal.cancel', 'appointments.modal.save',
    'appointments.modal.patient_not_found', 'appointments.modal.patient_lookup_error',
    'appointments.calendar.today', 'appointments.calendar.more', 'appointments.calendar.day_panel_title',
    'appointments.calendar.day_panel_empty', 'appointments.calendar.weekdays_short',
];

test('clés i18n des rendez-vous toujours définies en FR et EN', () => {
    for (const k of FROZEN_KEYS) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// Clés ajoutées par la refonte.
const NEW_KEYS = [
    'calendar.prev_month', 'calendar.next_month', 'calendar.appointments_count',
    'modal.section_patient', 'modal.section_appointment', 'modal.patient_code_help',
];

test('clés ajoutées par la refonte en FR et EN', () => {
    for (const k of NEW_KEYS) {
        for (const locale of ['fr', 'en']) {
            assert.equal(typeof pick(msgs[locale].appointments, k), 'string', `${locale}.appointments.${k} manquante`);
        }
    }
});

test('chaque clé appointments.* citée littéralement dans les écrans existe', () => {
    const used = new Set();
    for (const src of [list, modal, calendar, panel, badge]) {
        for (const m of src.matchAll(/['"`(]appointments\.([a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            assert.ok(pick(msgs[locale].appointments, k) !== undefined, `${locale}.appointments.${k} manquante`);
        }
    }
});

test('aucune couleur de marque ou d’état en dur dans les écrans refondus', () => {
    for (const [name, src] of [['list', list], ['modal', modal], ['calendar', calendar], ['panel', panel], ['badge', badge]]) {
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, `${name}: hexadécimal`);
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue)-\d{2,3}\b/, `${name}: couleur Tailwind brute`);
    }
});

test('les écrans utilisent la bibliothèque ui/', () => {
    for (const [name, src] of [['list', list], ['modal', modal], ['panel', panel], ['badge', badge]]) {
        assert.match(src, /@\/components\/ui/, `${name}: aucun composant ui/ importé`);
    }
});

test('texte affiché : plus de tiret long ni de points de suspension typographiques', () => {
    for (const [name, src] of [['list', list], ['modal', modal], ['calendar', calendar], ['panel', panel], ['badge', badge]]) {
        const template = src.slice(0, src.indexOf('<script'));
        assert.doesNotMatch(template, /[—–…·]/, `${name}: caractère typographique dans le gabarit`);
        assert.doesNotMatch(src.slice(src.indexOf('<script')), /\|\|\s*'[—–]'/, `${name}: valeur de repli en tiret long`);
    }
});

test('texte jamais inférieur à 13 px dans le calendrier', () => {
    assert.doesNotMatch(calendar, /text-\[(1[0-2]|[0-9])px\]/);
    assert.doesNotMatch(calendar, /text-xs/);
});
