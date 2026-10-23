import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/components/toxico/ToxicoDossierModal.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : dossier d'un patient toxicologie (historique, médical, prescriptions, export PDF, sortie) ---
check('ToxicoDossierModal', view, [
    // interface avec la liste
    'patientId: { type: Number, required: true }', "defineEmits(['close', 'discharged'])", 'const patient = ref(null);', 'const isLoading = ref(true);', "const currentTab = ref('history');",
    // onglets et droits (le serveur refuse aussi ces routes aux autres rôles)
    "{ id: 'history', label: 'toxico.dossier.tabs.history', icon: ClockIcon }", "{ id: 'medical', label: 'toxico.dossier.tabs.medical', icon: HeartIcon }",
    "{ id: 'prescriptions', label: 'toxico.dossier.tabs.prescriptions', icon: BeakerIcon }",
    "authStore.hasRole(['admin', 'ToxicoManager', 'Psychologist'])", "authStore.hasRole(['admin', 'ToxicoManager'])", '!!patient.value?.isActive && authStore.hasRole(TOXICO_DISCHARGE_ROLES)',
    'authStore.hasRole(TOXICO_DOSSIER_EXPORT_ROLES)', "tabs.filter((tab) => canSeeClinical.value || !['medical', 'prescriptions'].includes(tab.id))",
    'v-for="tab in visibleTabs"', ':key="tab.id"', '@click="currentTab = tab.id"', 't(tab.label)', "currentTab === 'history'", "currentTab === 'medical'", "currentTab === 'prescriptions'",
    // chargement du dossier
    'const data = await toxicoStore.getPatientDetails(props.patientId);', 'patient.value = data;', 'v-if="isLoading"', 'v-else-if="!patient"',
    // en-tête
    'patient.firstName', 'patient.lastName', 'patient.code', 'patient.substance', 'patient.isActive === false', "t('toxico.discharged.badge_inactive')",
    // historique : progression et séjours
    '(patient.currentPhase || 1) / 4', ':stays="patient.stays || []"', ':phaseHistory="patient.phaseHistory || []"', ':evaluations="patient.evaluations || []"',
    // activité récente, chargée à la première ouverture seulement
    'if (recent.value || recentLoading.value) return;', 'const res = await ToxicoGateway.getRecentActivity(props.patientId);', 'recent.value = res.data;', 'recentError.value = true;',
    "if (canSeeClinical.value && (tab === 'medical' || tab === 'prescriptions')) loadRecent();",
    'v-if="recentLoading"', 'recentError || recent?.historique_medical === null', '!recent?.historique_medical?.length', 'v-for="r in recent.historique_medical"', ':key="r.record_id"',
    'r.diagnosis || r.motif_code', 'r.symptoms', 'formatDate(r.consultation_date)',
    'recentError || recent?.prescriptions === null', '!recent?.prescriptions?.length', 'v-for="p in recent.prescriptions"', ':key="p.prescription_id"', 'prescriptionLabel(p)',
    '[p.dosage, p.frequency].filter(Boolean).join(', 'formatDate(p.start_date)',
    "p.medication || (p.lab_exams_list && p.lab_exams_list.length ? p.lab_exams_list.join(', ') : p.lab_exams) || '-'",
    // historique complet : réservé admin et responsable toxico
    'v-if="canOpenFullHistory"', "@click=\"openFullHistory('MEDICAL')\"", "@click=\"openFullHistory('PHARMA')\"",
    "router.push({ name: 'PatientDetail', params: { id: props.patientId }, query: { tab } });",
    // export PDF
    'v-if="canExportDossier"', '@click="exportPdf"', ':disabled="isExporting"', 'const res = await ToxicoGateway.exportDossierPdf(props.patientId);',
    'downloadPdfBlob(res.data, dossierExportFilename(props.patientId));', 'exportError.value = exportErrorKey(e);', 'v-if="exportError"', 't(exportError)',
    // sortie depuis le dossier
    'v-if="canDischarge"', '@click="showDischarge = true"', 'v-if="dischargeSuccess"', "t('toxico.stays.discharge_success')", "emit('discharged');", 'try { await loadDossier(); } catch (e)',
    '<ToxicoDischargeModal v-if="showDischarge && patient"', ':dossierId="patient.dossier_id"', '@close="showDischarge = false"', '@discharged="onDischarged"',
    // clés
    "t('toxico.export.exporting')", "t('toxico.export.dossier_pdf')", "t('toxico.stays.discharge_action')", "t('toxico.dossier.recent.medical_title')", "t('toxico.dossier.recent.prescriptions_title')",
    "t('toxico.dossier.recent.see_all')", "t('toxico.dossier.recent.loading')", "t('toxico.dossier.recent.error')", "t('toxico.dossier.recent.empty_medical')", "t('toxico.dossier.recent.empty_prescriptions')",
    "t('toxico.dossier.tabs.history')",
]);

test('toutes les clés toxico.* et toxicoScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:toxico|toxicoScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 14);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('ToxicoDossierModal : panneau accessible, onglets accessibles, barre d actions, la sortie reste une fenêtre à part', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['FullScreenPanel', 'StatusBadge', 'AppButton', 'ActionBar']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    const t = templateOf(view);
    assert.doesNotMatch(t, /fixed inset-0/);
    assert.match(t, /<FullScreenPanel[^>]*accent/s);
    assert.match(t, /role="tablist"/);
    assert.match(t, /role="tab"/);
    assert.match(t, /:aria-selected="currentTab === tab\.id"/);
    assert.match(t, /role="tabpanel"/);
    // les deux panneaux sont frères (jamais imbriqués) : le piège du focus de l'un ne gêne pas l'autre
    assert.match(t, /<\/FullScreenPanel>\s*<ToxicoDischargeModal/);
});

test('ToxicoDossierModal : progression par la couleur de la phase, valeur écrite, barre nommée', () => {
    assert.match(view, /phaseMeta\(/);
    assert.match(view, /import \{[^}]*phaseMeta[^}]*\} from '@\/utils\/toxicoUi'/);
    const t = templateOf(view);
    assert.match(t, /role="progressbar"/);
});

test('ToxicoDossierModal : états annoncés (chargement, erreur, succès), boutons par action (sortie rouge, fermer neutre/indigo)', () => {
    const t = templateOf(view);
    assert.match(t, /role="status"/);
    assert.match(t, /role="alert"/);
    assert.match(t, /<AppButton[^>]*variant="danger"[^>]*@click="showDischarge = true"/s);
    assert.match(t, /<AppButton[^>]*@click="exportPdf"/s);
});

test('ToxicoDossierModal : plus aucun texte français en dur dans le gabarit', () => {
    const t = templateOf(view).replace(/\{\{[^}]*\}\}/g, '').replace(/<!--.*?-->/gs, '');
    for (const bad of ['Impossible de charger', 'Fermer le dossier', 'Progression', 'Code:', 'Substance:', '>Phase ']) assert.ok(!t.includes(bad), `texte en dur : ${bad}`);
});

test('ToxicoDossierModal : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓×]|&times;|&rarr;|\p{Extended_Pictographic}/u);
    assert.doesNotMatch(templateOf(view), /animate-spin/, 'plus de roue maison : le chargement est un message annoncé');
});

test('clés toxicoScreens (dossier) en FR et EN', () => {
    const keys = ['dossier_title', 'dossier_load_error', 'dossier_close', 'progress_title', 'phase_short', 'dossier_code_substance', 'phase_progress'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].toxicoScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.toxicoScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.toxicoScreens.${k}`);
        }
    }
});
