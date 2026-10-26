// Defauts releves par les guides (2026-10-26), domaine MEDICAL : medecin, infirmier,
// hospitalisation, planning. Chaque test decrit le defaut observe.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

const calendar = read('components/appointments/AppointmentsCalendar.vue');
const detail = read('views/modules/patients/PatientDetailView.vue');
const apptList = read('views/modules/appointments/AppointmentsList.vue');
const recordStore = read('stores/medicalRecordStore.js');
const dossierStore = read('stores/patientDossierStore.js');
const hospCard = read('components/hospitalization/HospitalizationCard.vue');
const shiftCal = read('components/nurseshift/NurseShiftCalendar.vue');
const shiftPanel = read('components/nurseshift/NurseShiftDayPanel.vue');
const shiftView = read('views/modules/nurseshift/NurseShiftsView.vue');
const shiftStore = read('stores/nurseShiftStore.js');
const toast = read('components/common/ToastContainer.vue');
const patientStore = read('stores/patientStore.js');

test('calendrier des RDV : les jours viennent de tm()/rt(), pas de t() sur un tableau (cle brute affichee)', () => {
  assert.ok(!calendar.includes("t('appointments.calendar.weekdays_short')"));
  assert.ok(calendar.includes("tm('appointments.calendar.weekdays_short')"));
  assert.ok(calendar.includes('rt('));
  for (const lang of ['fr', 'en']) {
    const days = pick(msgs[lang], 'appointments.calendar.weekdays_short');
    assert.equal(days.length, 7, `${lang}: 7 jours`);
  }
});

test('fiche patient : le deep link ne remonte plus la vue (router-view est cle sur fullPath)', () => {
  // router.replace({ query: {} }) change fullPath => la vue est recreee et le formulaire ouvert se ferme.
  assert.ok(!detail.includes('router.replace({ query: {} })'));
  assert.ok(detail.includes('clearDeepLinkQuery'));
  assert.ok(detail.includes('history.replaceState'));
});

test('liste des RDV : refuser un rendez-vous demande confirmation (tableau ET panneau du calendrier)', () => {
  assert.ok(apptList.includes("confirm(t('appointments.confirm_cancel'))"));
  assert.ok(apptList.includes('confirmCancel'));
  assert.ok(!apptList.includes('@click="appointmentStore.cancelAppointment('));
  assert.ok(!apptList.includes('@cancel="(appt) => appointmentStore.cancelAppointment('));
  for (const lang of ['fr', 'en']) assert.ok(pick(msgs[lang], 'appointments.confirm_cancel'));
});

test('nouvelle consultation locale : l auteur est ecrit tout de suite (plus de "Inconnu" jusqu au rechargement)', () => {
  assert.ok(recordStore.includes('created_by_name'));
  assert.ok(recordStore.includes('created_by,'));
});

test('apres enregistrement local : le dossier est relu du serveur des que la synchro a abouti (signes vitaux, auteur)', () => {
  assert.ok(dossierStore.includes('syncDossierFromServer'));
  assert.ok(detail.includes('syncDossierFromServer'));
});

test('onglet Traitements : statut traduit et demande d examen lisible', async () => {
  const { prescriptionStatusLabelKey, isPlaceholder, prescriptionDetails } = await import('../src/utils/prescriptionDisplay.js');
  assert.equal(prescriptionStatusLabelKey('active'), 'medical.prescription_status.active');
  assert.equal(prescriptionStatusLabelKey('Active'), 'medical.prescription_status.active');
  assert.equal(prescriptionStatusLabelKey('completed'), 'medical.prescription_status.completed');
  assert.equal(prescriptionStatusLabelKey(undefined), 'medical.prescription_status.unknown');
  assert.equal(prescriptionStatusLabelKey('zzz'), 'medical.prescription_status.unknown');
  assert.equal(isPlaceholder('N/A'), true);
  assert.equal(isPlaceholder(' n/a '), true);
  assert.equal(isPlaceholder(''), true);
  assert.equal(isPlaceholder(null), true);
  assert.equal(isPlaceholder('500 mg'), false);
  assert.deepEqual(prescriptionDetails({ dosage: '500 mg', frequency: 'N/A', duration: '5 j' }), ['500 mg', '5 j']);
  assert.deepEqual(prescriptionDetails({ is_lab_order: true, dosage: 'N/A', frequency: 'N/A', duration: 'N/A' }), []);
  assert.ok(detail.includes('prescriptionStatusLabelKey'));
  assert.ok(detail.includes('prescriptionDetails'));
  assert.ok(!detail.includes('String(p.status)'));
  for (const lang of ['fr', 'en']) {
    for (const k of ['active', 'completed', 'cancelled', 'unknown']) assert.ok(pick(msgs[lang], `medical.prescription_status.${k}`), `${lang} ${k}`);
    assert.ok(pick(msgs[lang], 'medical.treatments.lab_order'));
  }
});

test('liste des patients hors ligne : le type vient des consultations locales, plus de NOUVEAU pour tous', () => {
  assert.ok(patientStore.includes('n_records'));
  assert.ok(patientStore.includes('ORDER BY l.patient_id DESC'));
});

test('hospitalisation : motif d admission et note de sortie affiches (sejour en cours et historique)', () => {
  assert.ok(hospCard.includes('openStay.admission_reason'));
  assert.ok(hospCard.includes('stay.admission_reason'));
  assert.ok(hospCard.includes('stay.discharge_note'));
  for (const lang of ['fr', 'en']) {
    assert.ok(pick(msgs[lang], 'hospitalization.admission_reason_label'));
    assert.ok(pick(msgs[lang], 'hospitalization.discharge_note_label'));
  }
});

test('planning : la vue mois affiche tous les noms (pas de troncature)', () => {
  const month = shiftCal.slice(shiftCal.indexOf('data-view="month"'));
  assert.ok(!month.includes('truncate'));
  assert.ok(month.includes('break-words'));
});

test('planning hors ligne : etat honnete au lieu de "No nurse assigned."', () => {
  assert.ok(shiftStore.includes('offline'));
  assert.ok(shiftView.includes('nurseShiftStore.error'));
  assert.ok(shiftView.includes(':unavailable='));
  assert.ok(shiftCal.includes('unavailable'));
  assert.ok(shiftPanel.includes('unavailable'));
  for (const lang of ['fr', 'en']) {
    assert.ok(pick(msgs[lang], 'nurseShift.load_failed'));
    assert.ok(pick(msgs[lang], 'nurseShift.offline_unavailable'));
    assert.ok(pick(msgs[lang], 'nurseShift.state_unknown'));
  }
});

test('toast de succes : ton succes, pas l avertissement jaune', () => {
  assert.ok(toast.includes("'success'"));
  assert.ok(toast.includes('toneClasses'));
  assert.ok(!toast.includes('bg-amber-50'));
});

test('planning : le panneau applique la regle NUIT exclusive, MATIN + APRES_MIDI permis', () => {
  assert.ok(shiftPanel.includes("shiftType === 'NUIT'"));
  assert.ok(shiftPanel.includes("includes('NUIT')"));
  assert.ok(shiftPanel.includes('mine.length === 0'));
});

test('planning : les codes de refus du serveur sont traduits FR et EN, repli sur le message serveur', async () => {
  const { shiftErrorMessage } = await import('../src/utils/nurseShiftErrors.js');
  for (const lang of ['fr', 'en']) {
    const t = (k) => pick(msgs[lang], k);
    for (const code of ['shift_night_exclusive', 'shift_rest_after_night', 'shift_already_assigned']) {
      const text = t(`nurseShift.errors.${code}`);
      assert.ok(text, `${lang} ${code}`);
      assert.ok(/^[\x20-\x7E\u00C0-\u00FF]+$/.test(text) || lang === 'fr', `${lang} ${code} ASCII`);
      assert.equal(shiftErrorMessage({ response: { data: { detail: { code, message: 'repli' } } } }, t), text);
    }
    assert.ok(t('nurseShift.errors.generic'));
    assert.ok(t('nurseShift.rest_after_night_hint'));
  }
  const t = (k) => k;
  assert.equal(shiftErrorMessage({ response: { data: { detail: { code: 'inconnu', message: 'repli serveur' } } } }, t), 'repli serveur');
  assert.equal(shiftErrorMessage({ response: { data: { detail: 'texte brut' } } }, t), 'texte brut');
  assert.equal(shiftErrorMessage({}, t), 'nurseShift.errors.generic');
  assert.ok(shiftView.includes('shiftErrorMessage'));
});

test('planning : le panneau n offre pas MATIN apres une nuit la veille ni NUIT avant un matin le lendemain', () => {
  assert.ok(shiftPanel.includes('previousDayShifts'));
  assert.ok(shiftPanel.includes('nextDayShifts'));
  assert.ok(shiftView.includes(':previous-day-shifts='));
  assert.ok(shiftView.includes(':next-day-shifts='));
  assert.ok(shiftPanel.includes('rest_after_night_hint'));
});
