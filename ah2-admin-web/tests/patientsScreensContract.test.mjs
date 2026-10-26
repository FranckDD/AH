import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const list = read('views/modules/patients/PatientList.vue');
const detail = read('views/modules/patients/PatientDetailView.vue');
const header = read('components/patients/PatientHeader.vue');
const modal = read('components/patients/PatientModal.vue');
const labTable = read('components/patients/labs/LabResultTable.vue');
const spiritual = read('components/patients/medical/SpiritualTimeline.vue');

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Liste des patients ---
check('PatientList', list, [
    'patientStore.fetchPatients()', 'patientStore.fetchCounts()', 'patientStore.addPatient(payload)',
    'patientStore.updatePatient(patientBeingEdited.value.patient_id, payload)', 'patientStore.deletePatient(patient.id)',
    'patientStore.getPatientById(patient.id)', 'patientStore.setPage(page)', 'patientStore.setFilters({ search: searchInput.value })',
    'patientStore.setFilters({ type: val })', 'patientStore.pagination.hasNext', 'patientStore.pagination.total_pages',
    '@keyup.enter="searchNow"', 'v-model="searchInput"', '@input="onSearchInput"', 'setTimeout(() => {', '}, 300);',
    "authStore.hasRole(['medecin', 'nurse', 'secretaire', 'admin', 'manager'])", 'canManagePatients',
    "authStore.hasRole(['medecin', 'nurse'])", "tousLesOnglets.filter((t) => t.value !== 'TOXICO' && t.value !== 'SPIRITUEL')",
    "value: 'ALL'", "value: 'CLINIQUE'", "value: 'TOXICO'", "value: 'SPIRITUEL'",
    'disableDetailLink', 'router.push(`${route.path}/${patientId}`)', 'router.push(`${route.path}/${created.localUuid}`)',
    'showsCodeDialog(authStore.userRole, created)', 'patient.pending', "t('screens.patientList.pending_sync')",
    'Voulez-vous vraiment supprimer ${patient.firstName} ${patient.lastName} ?', "t('staffDiscount.badge')", 'patient.is_staff',
    "api.get('/patients/export'", 'ExportModal', 'NewPatientCodeModal', 'MedicalRecordModal', ':defaultNeedsDoctorReview="true"',
    '@close="closeModal"', '@save="handleSave"', 'viewPatientDossier(patient.id)',
    "t('screens.patientList.load_for_edit_failed')", 'mapErrorToMessage',
]);

// --- Fiche patient : cloisonnement par rôle, onglets, flux de consultation et de prescription ---
check('PatientDetailView', detail, [
    'dossierStore.fetchDossierComplete(id)', 'dossierStore.refreshMedicalHistoryLocal(route.params.id)',
    'dossierStore.refreshMedicalHistory(route.params.id)', 'dossierStore.refreshVitalsSummaryLocal(route.params.id)',
    'dossierStore.refreshPrescriptionHistoryLocal(route.params.id)',
    'medicalRecordStore.createMedicalRecord(data)', 'medicalRecordStore.updateMedicalRecord(recordId, data)',
    'prescriptionStore.createPrescription(data)', 'appointmentStore.completeAppointment(data.appointmentId)',
    "authStore.hasRole(['medecin', 'nurse'])", 'isRecordEditable(target, dossierStore.medicalHistory, { samePatient: true })',
    "['MEDICAL', 'PHARMA'].includes(route.query.tab)", 'route.query.appointmentId', 'route.query.record',
    'clearDeepLinkQuery()', '`/patients/${route.params.id}/dossier/export`', "params: { format }",
    "currentTab = 'MEDICAL'", "currentTab = 'LABO'", "currentTab = 'PHARMA'", "currentTab = 'HOSPITALISATION'",
    "currentTab = 'TOXICO'", "currentTab = 'SPIRITUEL'",
    'v-if="dossierStore.isToxicology"', 'v-if="dossierStore.isSpiritual"',
    'v-if="authStore.hasRole([\'medecin\', \'nurse\'])"', 'dossierStore.spirituelRestreint', 'dossierStore.toxicoRestreint',
    "dossierStore.isDomaineIndisponible('dossier_toxico')", 'dossierStore.domainesIndisponibles',
    'canCreateConsultation', '@edit="openEditConsultationModal"', '@prescribe="openPrescriptionFor"',
    ':prefilledMedicalRecordId="prescriptionOffer.medicalRecordId"', '@save="handleConsultationSave"', '@save="handlePrescriptionSave"',
    'acceptPrescriptionOffer', 'declinePrescriptionOffer', ':patient-id="dossierStore.patientSummary.patient_id"',
    '@back="goBack"', 'exportDossier(\'pdf\')', 'exportDossier(\'excel\')', 'resolveRecordId',
    "'medical.vitals.bp'", "'medical.vitals.weight'", "'medical.vitals.temperature'", "'medical.alerts.allergies_title'",
]);

check('PatientHeader', header, [
    "defineEmits(['back'])", "$emit('back')", 'patient.full_name', 'patient.code', 'patient.age', 'patient.gender',
    'patient.flags?.is_clinical', 'patient.flags?.is_toxicology', 'patient.flags?.is_spiritual', 'patient.is_staff',
    "t('staffDiscount.badge')", 'getInitials',
]);

check('PatientModal', modal, [
    "defineEmits(['close', 'save'])", "emit('save', { ...form })", 'v-model="form.firstName"', 'v-model="form.lastName"',
    'v-model="form.birthDate"', 'v-model="form.gender"', 'v-model="form.nationalId"', 'v-model="form.contactPhone"',
    'v-model="form.assurance"', 'v-model="form.residence"', 'v-model="form.fatherName"', 'v-model="form.motherName"',
    ':max="today"', 'id="patientForm"', 'form="patientForm"', ':disabled="isSaving || !isFormValid"',
    'isFormValid', 'errorMessage', 'isSaving', 'patientToEdit', 'type="submit"',
    'form.firstName.trim() && form.lastName.trim() && form.birthDate',
]);

check('LabResultTable', labTable, [
    'labStore.fetchResultDetail(res.result_id)', 'labStore.downloadPDF(item.result_id, `Resultat_${item.result_id}.pdf`)',
    'ResultDetailModal', '@close="selectedResult = null"', '@print="downloadPdf"', 'res.nb_anormaux',
    "t('lab.patient_table.abnormal_count', { n: res.nb_anormaux }, res.nb_anormaux)", 'res.examen_name', 'res.code_lab',
    'res.test_date', "t('lab.patient_table.detail_unavailable')", "['pending', 'partial', 'analyzed', 'completed', 'validated']",
]);

check('SpiritualTimeline', spiritual, [
    'rec.type || rec.type_consultation', 'rec.psaume', 'rec.notes', 'rec.fr_amount_paid', 'rec.fr_appointment_at',
    'rec.presc_generic', 'rec.presc_med_spirituel', 'formatDateDMY', "t('screens.spiritual.none')",
]);

// --- Clés i18n ---
test('chaque clé citée littéralement dans les écrans existe en FR et EN', () => {
    const used = new Set();
    for (const src of [list, detail, header, modal, labTable, spiritual]) {
        for (const m of src.matchAll(/['"`(]((?:patients|medical|lab\.patient_table|lab\.status|staffDiscount|export|hospitalization|common)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 20);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

test('clés ajoutées en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        for (const k of ['section_identity', 'section_contact', 'section_family']) {
            assert.equal(typeof msgs[locale].patients.modal?.[k], 'string', `${locale}.patients.modal.${k}`);
        }
    }
});

// --- Refonte ---
test('les écrans utilisent la bibliothèque ui/', () => {
    for (const [name, src] of [['list', list], ['detail', detail], ['header', header], ['modal', modal], ['labTable', labTable], ['spiritual', spiritual]]) {
        assert.match(src, /@\/components\/ui/, `${name}: aucun composant ui/ importé`);
    }
});

test('liste : tableau responsive ; fiche : onglets lisibles ; formulaire : panneau en sections', () => {
    assert.match(list, /ResponsiveTable/);
    assert.match(detail, /role="tablist"/);
    assert.match(detail, /role="tab"/);
    assert.match(modal, /FullScreenPanel/);
    assert.match(modal, /FormSection/);
    assert.match(modal, /ActionBar/);
    assert.match(labTable, /ResponsiveTable/);
});

test('cloisonnement : aucune entrée toxico ou spirituelle ajoutée pour les rôles médicaux', () => {
    // Les onglets de la liste restent filtrés pour médecin et infirmière, ceux de la fiche restent conditionnés aux drapeaux du dossier.
    assert.match(list, /authStore\.hasRole\(\['medecin', 'nurse'\]\)\) \{\s*return tousLesOnglets\.filter/);
    const toxicoTab = detail.slice(detail.indexOf("currentTab = 'TOXICO'") - 200, detail.indexOf("currentTab = 'TOXICO'"));
    assert.match(toxicoTab, /v-if="dossierStore\.isToxicology"/);
    const spiritTab = detail.slice(detail.indexOf("currentTab = 'SPIRITUEL'") - 200, detail.indexOf("currentTab = 'SPIRITUEL'"));
    assert.match(spiritTab, /v-if="dossierStore\.isSpiritual"/);
});

test('aucune couleur de marque ou d’état en dur', () => {
    for (const [name, src] of [['list', list], ['detail', detail], ['header', header], ['modal', modal], ['labTable', labTable], ['spiritual', spiritual]]) {
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, `${name}: hexadécimal`);
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/, `${name}: couleur Tailwind brute`);
    }
    // Les couleurs passées à la carte de constantes viennent de la fiche : elles utilisent aussi les jetons.
    assert.doesNotMatch(detail, /colorClass="bg-(rose|blue|orange)-/);
});

test('texte affiché : ni tiret long, ni point médian, ni emoji, ni croix typographique', () => {
    for (const [name, src] of [['list', list], ['detail', detail], ['header', header], ['modal', modal], ['labTable', labTable], ['spiritual', spiritual]]) {
        const template = src.slice(0, src.indexOf('<script'));
        assert.doesNotMatch(template, /[—–…·✕📖]/u, `${name}: caractère typographique dans le gabarit`);
        assert.doesNotMatch(src.slice(src.indexOf('<script')), /' — '/, `${name}: séparateur en tiret long`);
    }
});

test('texte jamais inférieur à 13 px', () => {
    for (const [name, src] of [['list', list], ['detail', detail], ['header', header], ['modal', modal], ['labTable', labTable], ['spiritual', spiritual]]) {
        assert.doesNotMatch(src, /text-\[(1[0-2]|[0-9])px\]/, name);
        assert.doesNotMatch(src, /text-xs/, name);
    }
});

test('chaque onglet de la fiche a sa propre couleur (jeton tab-*), gardée par l’icône même inactif', () => {
    for (const tok of ['tab-record', 'tab-lab', 'tab-pharma', 'tab-hospital', 'tab-toxico', 'tab-spirit']) {
        assert.ok(detail.includes(`text-${tok}`), `text-${tok} absent`);
        assert.ok(detail.includes(`border-${tok}`), `border-${tok} absent`);
    }
    assert.equal((detail.match(/tabIconClass\('/g) || []).length, 6);
});

test('un patient sans dossier s’affiche « NOUVEAU » (le type interne AUTRE ne change pas)', () => {
    assert.match(list, /:label="typeLabel\(patient\.type\)"/);
    assert.match(list, /type === 'AUTRE' \? t\('patients\.types\.nouveau'\)/);
    for (const locale of ['fr', 'en']) {
        assert.equal(typeof msgs[locale].patients.types.nouveau, 'string', `${locale}.patients.types.nouveau`);
    }
    assert.equal(msgs.fr.patients.types.nouveau, 'Nouveau');
    // le calcul du type reste dans le store : rien n'y a changé
    const store = readFileSync(new URL('../src/stores/patientStore.js', import.meta.url), 'utf8');
    assert.match(store, /let displayType = 'AUTRE';/);
});
