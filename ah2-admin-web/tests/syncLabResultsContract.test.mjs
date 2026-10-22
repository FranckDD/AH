import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const sync = read('views/modules/sync/SyncFailuresView.vue');
const labResults = read('views/modules/labo/MedicalLabResults.vue');

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Échecs de synchronisation : toute la logique de quarantaine reste en place ---
check('SyncFailuresView', sync, [
    'listQuarantine()', 'reattachToExistingPatient(g.patientUuid, match.patient_id || match.id)',
    'dismissQuarantineEntry(l.id)', "api.get('/patients/', { params: { search: code, per_page: 5 } })",
    "code.startsWith('AH2-') ? code : `AH2-${code}`", 'list.find((p) => p.code_patient === code)',
    "r.kind === 'patient'", "c.kind === 'medical_record'", "c.kind === 'prescription'", "c.kind === 'lab_result'",
    "c.kind === 'lab_result_detail'", "r.kind === 'medical_record_locked' || r.kind === 'prescription_locked'",
    "l.kind === 'medical_record_locked'", "r.kind === 'lab_result' || r.kind === 'lab_result_detail'",
    "'consultation_date', 'motif_code', 'symptoms', 'diagnosis', 'treatment', 'notes', 'medical_history'",
    "'allergies', 'bp', 'temperature', 'weight', 'height', 'medication', 'dosage', 'frequency', 'duration', 'start_date', 'end_date'",
    '@click="handleReattach(g)"', ':disabled="busy[g.patientUuid]"', '@click="handleDismiss(l)"',
    'v-model="codes[g.patientUuid]"', 'messages[g.patientUuid].ok',
    "'Saisissez le code du patient existant.'", '`Aucun patient avec le code ${code}.`',
    '`Données rattachées à ${match.first_name} ${match.last_name}.`', "'Erreur serveur, réessayez.'",
    "'Connexion requise pour rattacher un patient.'", "'Patient sans nom'", 'Échecs de synchronisation', 'Aucun échec de synchronisation.',
    'Rattacher à ce patient', "t('medical.readonly.quarantine_title')", "t('medical.readonly.quarantine_intro')",
    "t('medical.readonly.quarantine_record')", "t('medical.readonly.quarantine_prescription')", "t('medical.readonly.quarantine_dismiss')",
    'onMounted(load)', 'groups.length === 0 && labOrphans.length === 0 && lockedRejections.length === 0',
]);

// --- Résultats d'examens (médecin / infirmière) : lecture seule, recherche, pagination ---
check('MedicalLabResults', labResults, [
    'store.fetchPaginatedHistory({', 'page: filters.value.page', 'limit: filters.value.limit', 'search: q.length >= 2 ? q : null',
    'if (q.length === 1) return;', 'debounce(() => {', '}, 400);', 'limit: 15',
    'store.fetchResultDetail(item.result_id)', 'store.downloadPDF(item.result_id, filename)', '`Resultat_${item.result_id}.pdf`',
    'if (filters.value.page < store.paginatedHistory.total_pages)', 'if (filters.value.page > 1)',
    ':disabled="filters.page === 1"', ':disabled="filters.page >= store.paginatedHistory.total_pages"',
    'v-model="filters.query"', '@input="handleSearch"', '@click="openView(res)"', '@click="downloadPdf(res)"', '@click="refresh"',
    '@close="selectedResult = null"', '@print="downloadPdf"', 'ResultDetailModal',
    'res.result_id', 'res.code', 'res.patient_name', 'res.patient_age', 'res.patient_sexe', 'res.is_external', 'res.examen_nom', 'res.test_date',
    "dayjs(d).format('DD/MM/YYYY HH:mm')", 'store.paginatedHistory.items', 'store.paginatedHistory.total_items',
    "t('lab.result_modal.external')", "t('lab.history_view.empty_medical')", "t('lab.history_view.empty_medical_hint')",
]);

test('lecture seule : aucune action de modification des résultats pour médecin et infirmière', () => {
    assert.doesNotMatch(labResults, /updateResult|validateResult|saveResult|deleteResult|submit/i);
});

test('chaque clé citée littéralement dans les écrans existe en FR et EN', () => {
    const used = new Set();
    for (const src of [sync, labResults]) {
        for (const m of src.matchAll(/['"`(]((?:lab\.history_view|lab\.result_modal|medical\.readonly)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    }
    assert.ok(used.size >= 10);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte ---
test('les écrans utilisent la bibliothèque ui/ et des tableaux responsives', () => {
    assert.match(sync, /@\/components\/ui/);
    assert.match(labResults, /@\/components\/ui/);
    assert.match(labResults, /ResponsiveTable/);
});

test('états vides aimables et erreurs avec texte, jamais la couleur seule', () => {
    assert.match(sync, /EmptyState/);
    assert.match(sync, /role="alert"|role="status"/);
});

test('aucune couleur de marque ou d’état en dur', () => {
    for (const [name, src] of [['sync', sync], ['labResults', labResults]]) {
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, `${name}: hexadécimal`);
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/, `${name}: couleur Tailwind brute`);
    }
});

test('texte affiché : ni tiret long, ni point médian, ni points de suspension typographiques', () => {
    for (const [name, src] of [['sync', sync], ['labResults', labResults]]) {
        const template = src.slice(0, src.indexOf('<script'));
        assert.doesNotMatch(template, /[—–…·]/, `${name}: caractère typographique dans le gabarit`);
    }
});

test('texte jamais inférieur à 13 px', () => {
    for (const [name, src] of [['sync', sync], ['labResults', labResults]]) {
        assert.doesNotMatch(src, /text-\[(1[0-2]|[0-9])px\]/, name);
        assert.doesNotMatch(src, /text-xs/, name);
    }
});
