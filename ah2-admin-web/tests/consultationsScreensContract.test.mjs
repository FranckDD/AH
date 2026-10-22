import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const list = read('views/modules/consultations/ConsultationsList.vue');
const modal = read('components/consultations/ConsultationModal.vue');

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

check('ConsultationsList', list, [
    'consultationStore.fetchConsultations()', '@keyup.enter="consultationStore.fetchConsultations()"', 'v-model.lazy="searchQuery"',
    'consultationStore.setFilters({ search: val })', 'consultationStore.filters.search',
    'consultationStore.setPage(consultationStore.pagination.page - 1)', 'consultationStore.setPage(consultationStore.pagination.page + 1)',
    ':disabled="consultationStore.pagination.page === 1"', ':disabled="!consultationStore.hasNextPage"',
    'consultationStore.updateConsultation(editingConsultation.value.consultation_id, data)',
    'consultationStore.createConsultation(data)', 'consultationStore.deleteConsultation(rec.consultation_id)',
    "confirm(t('consultations.confirm_delete'))", 'alert(err.response?.data?.detail || err.message)',
    "api.get('/cs/export'", "responseType: format === 'pdf' ? 'blob' : 'text'", 'format,', 'search: consultationStore.filters.search || undefined',
    'date_from: dateFrom || undefined', 'date_to: dateTo || undefined', '`consultations_export.${format}`',
    "rec.type_consultation === 'Spiritual'", 'rec.patient_name || `#${rec.patient_id}`', 'rec.patient_code',
    "(rec.consultation_date || '').slice(0, 10)", 'rec.consultation_id', ':consultation="editingConsultation"', '@save="handleSave"',
    'showModal.value = false', "[{ value: 'pdf', label: 'PDF' }, { value: 'csv', label: 'CSV' }]", ':onExport="exportConsultations"',
    '@click="openModal(null)"', 'openModal(rec)', 'handleDelete(rec)', 'showExportModal = true', 'consultationStore.isLoading', 'consultationStore.consultations',
    "t('consultations.title')", "t('consultations.subtitle')", "t('consultations.search_placeholder')", "t('consultations.new_consultation')",
    "t('consultations.table.patient')", "t('consultations.table.type')", "t('consultations.table.date')",
    "t('consultations.empty')", "t('consultations.type_spiritual')", "t('consultations.type_family_restoration')",
    "t('consultations.actions.edit')", "t('consultations.actions.delete')", "t('export.confirm')",
]);

check('ConsultationModal (champs et règles)', modal, [
    "defineEmits(['close', 'save'])", 'defineProps({ consultation: { type: Object, default: null } })',
    'v-model="patientCode"', '@blur="lookupPatient"', ':readonly="isEdit"', 'v-model="form.typeConsultation"', 'v-model="form.consultationDate"',
    'type="datetime-local"', 'v-model="form.mpType"', 'v-model="form.psaume"', 'v-model="form.prescGeneric"', 'v-model="form.prescMedSpirituel"',
    "['Hony', 'Massage', 'Prayer']", "['SE', 'TIS', 'AE']", 'v-model="form.frRegisteredAt"', 'v-model="form.frAppointmentAt"',
    'v-model="form.frAmountPaid"', 'type="number" min="0" step="0.01" required', 'v-model="form.frObservation"', 'v-model="form.notes"',
    "v-if=\"form.typeConsultation === 'Spiritual'\"", "v-else-if=\"form.typeConsultation === 'FamilyRestoration'\"",
    'consultationStore.fetchPrayerBookTypes()', 'v-for="pbt in consultationStore.prayerBookTypes"', 'pbt.label || pbt.type_code',
    'let isInitializing = true;', 'if (isInitializing) return;', "form.frRegisteredAt = '';", "form.mpType = '';", 'form.prescGeneric = [];',
    'await ensureLookup();', "alert(t('consultations.modal.patient_not_found'))", "alert(t('consultations.modal.type_required'))",
    "emit('save', {", 'patientId: patientId.value', 'typeConsultation: form.typeConsultation', 'prescGeneric: form.prescGeneric',
    'prescMedSpirituel: form.prescMedSpirituel', 'mpType: form.mpType || null', 'psaume: form.psaume || null', 'notes: form.notes || null',
    'frRegisteredAt: form.frRegisteredAt || null', 'frAppointmentAt: form.frAppointmentAt || null',
    "frAmountPaid: form.frAmountPaid !== '' && form.frAmountPaid !== null ? form.frAmountPaid : null",
    'frObservation: form.frObservation || null', 'consultationDate: form.consultationDate || null',
    "form.consultationDate = rec.consultation_date ? rec.consultation_date.slice(0, 16) : '';",
    "form.typeConsultation = rec.type_consultation || 'Spiritual';", 'setFromExisting({',
]);

test('chaque clé consultations.* / export.* citée littéralement existe en FR et EN', () => {
    const used = new Set();
    for (const src of [list, modal]) {
        for (const m of src.matchAll(/['"`(]((?:consultations|export)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size > 25);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

test('clés ajoutées en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        for (const k of ['prev_page', 'next_page', 'page_label', 'section_patient']) {
            assert.equal(typeof msgs[locale].consultationsScreens?.[k], 'string', `${locale}.consultationsScreens.${k}`);
        }
    }
});

// --- Refonte ---
test('les écrans utilisent ui/ (tableau responsive, panneau, sections, barre d’actions)', () => {
    assert.match(list, /@\/components\/ui/);
    assert.match(list, /ResponsiveTable/);
    assert.match(modal, /FullScreenPanel/);
    assert.match(modal, /FormSection/);
    assert.match(modal, /ActionBar/);
    assert.match(modal, /FormField/);
    assert.match(modal, /type="submit"/);
    assert.match(modal, /variant="ghost"/);
});

test('couleurs par jetons, texte >= 13 px, aucun caractère typographique ni entité de flèche', () => {
    for (const [name, src] of [['list', list], ['modal', modal]]) {
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, `${name}: hexadécimal`);
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/, `${name}: couleur brute`);
        assert.doesNotMatch(src, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/, `${name}: texte trop petit`);
        assert.doesNotMatch(src.slice(0, src.indexOf('<script')), /[—–…·]|&laquo;|&raquo;|&times;/u, `${name}: caractère typographique`);
        assert.doesNotMatch(src, /' — '/, `${name}: séparateur en tiret long`);
    }
});
