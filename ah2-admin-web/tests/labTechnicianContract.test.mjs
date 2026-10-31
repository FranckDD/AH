import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labo/LabTechnician.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : paillasse (liste des dossiers, saisie des valeurs, drapeaux, validation, impression) ---
check('LabTechnician', view, [
    // chargement et ouverture directe depuis le tableau de bord
    'const refreshList = () => labStore.fetchPaillasseList();', 'await refreshList();', 'const target = Number(route.query.open);', 'await openDossier(target);',
    'const activeDossier = computed(() => labStore.currentResult);',
    // liste
    // liste : un patient une seule fois (LabPassageCard), l'ouverture d'un examen reste openDossier(result_id)
    '<LabPassageCard v-for="passage in passages"', ':key="passage.key"', ':active-id="activeId"', '@open="openDossier"', 'groupPaillasse(labStore.paillasseList)',
    'labStore.paillasseList.length === 0 && !labStore.loading', '@click="refreshList"', "t('lab.technician.in_analysis', { n: labStore.paillasseList.length })",
    // ouverture d'un dossier et restauration des drapeaux
    'if (!id) return;', 'activeId.value = id;', 'labStore.clearMessages();', 'const data = await labStore.fetchResultDetail(id);', "formGlobalNote.value = data.note || '';",
    "const val = (d.valeur !== null && d.valeur !== undefined) ? d.valeur : '';", 'formValues.value[d.detail_id] = val;', 'formFlags.value[d.detail_id] = flagFromDetail(d);',
    "formInterpretations.value[d.detail_id] = d.interpretation || '';", 'if (!(d.is_abnormal || d.flagged)) return \'\';', "if (interp === 'haut') return 'H';", "if (interp === 'bas') return 'L';", "return 'A';",
    // dossiers du même lot
    'v-if="labStore.batchSiblings.length > 1"', 'v-for="sibling in labStore.batchSiblings"', ':key="sibling.result_id"', '@click="openDossier(sibling.result_id)"',
    'sibling.result_id === activeDossier.result_id', 'sibling.exam_name', "sibling.status === 'completed'",
    // en-tête du dossier
    'activeDossier.examen_nom', 'activeDossier.code', 'activeDossier.patient_info?.nom', 'activeDossier.patient_info?.sexe', 'activeDossier.patient_info?.age',
    // validation des boutons
    '@click="submit(false)"', '@click="submit(true, false)"', '@click="submit(true, true)"', ':disabled="labStore.loading || !activeDossier.details.length || isFormEmpty"',
    "if (Object.keys(formValues.value).length === 0) return true;", "return !Object.values(formValues.value).some(val => val !== '' && val !== null && val !== undefined);",
    // saisie
    'detail.input_type === \'numeric\'', 'v-model.number="formValues[detail.detail_id]"', 'step="any"', '@wheel="$event.target.blur()"', 'v-model="formValues[detail.detail_id]"',
    'v-if="hasValue(formValues[detail.detail_id])"', 'v-model="formFlags[detail.detail_id]"', "value: 'H'", "value: 'L'", "value: 'N'", "value: 'A'", "value: ''", 'v-model="formInterpretations[detail.detail_id]"',
    'detail.unite', 'getRangeForPatient(detail, activeDossier.patient_info)', '!activeDossier.details || activeDossier.details.length === 0',
    'v-model="formGlobalNote"', 'v-if="activeDossier.details && activeDossier.details.length > 0"',
    // charge envoyée
    'const targetId = activeId.value || activeDossier.value?.result_id;', 'notifyText(t(\'lab.technician.no_file_selected\'));', 'const payloadValues = {};', 'for (const detailId in formValues.value) {',
    'valeur: formValues.value[detailId],', "flag: formFlags.value[detailId] || '',", "interpretation: formInterpretations.value[detailId] || ''", 'values: payloadValues,', 'completed: isCompleted,',
    'note: formGlobalNote.value', 'const success = await labStore.saveValues(targetId, fullPayload);', 'if (isCompleted && shouldPrint) {', 'await labStore.downloadPDF(targetId, `Resultat_${targetId}.pdf`);',
    'activeId.value = null;',
    // plage de référence
    // plage du sexe du patient (labRanges.js), jamais ranges[0] en repli
    'rangeLabelForDetail(detail, info?.sexe, info?.age_days ?? null, null)',
    // clés
    "t('lab.technician.title')", "t('lab.technician.nothing_to_enter')", "t('lab.technician.select_file')", "t('lab.technician.save_draft')", "t('lab.technician.validate_close')",
    "t('lab.technician.validate_print')", "t('lab.technician.value')", "t('lab.result_modal.param')", "t('lab.result_modal.unit')", "t('lab.technician.reference')", "t('lab.technician.result_placeholder')", "t('lab.technician.flag_normal')", "t('lab.technician.interp_placeholder')", "t('lab.technician.no_params')", "t('lab.technician.global_conclusion')", "t('lab.technician.conclusion_placeholder')",
    "t('lab.result_modal.years')", "t('lab.result_modal.flag_high')", "t('lab.result_modal.flag_low')", "t('lab.result_modal.abnormal')",
]);

test('toutes les clés lab.* et labScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:lab|labScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 20);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabTechnician : composants ui/, tableau des paramètres responsive, jauge de progression, barre d actions, boutons par action', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['AppCard', 'ResponsiveTable', 'StatusBadge', 'AppButton', 'ActionBar', 'FormField', 'EmptyState']) assert.match(view, new RegExp(`\\b(?:${c})\\b`), c);
    assert.match(view, /\bstriped\b/);
    const t = templateOf(view);
    assert.match(t, /variant="success"/, 'valider = vert');
    assert.doesNotMatch(t, /<table/);
});

test('LabTechnician : la liste montre un patient une seule fois, jamais des div cliquables', () => {
    const t = templateOf(view);
    assert.match(t, /<LabPassageCard/);
    assert.doesNotMatch(t, /<div[^>]*@click="openDossier/s);
    assert.match(t, /aria-pressed/);
    assert.match(t, /role="status"/);
});

test('LabTechnician : champs de saisie nommés, drapeaux dits par le texte (jamais emoji ni couleur seule)', () => {
    const t = templateOf(view);
    assert.match(t, /aria-label/);
    assert.doesNotMatch(t, /[🔺🔻✅⚠]|\p{Extended_Pictographic}/u);
    assert.match(t, /type="radio"/, 'drapeaux en pastilles à choisir');
    assert.match(t, /role="radiogroup"/);
    assert.match(t, /role="progressbar"/);
    for (const icon of ['ArrowUpIcon', 'ArrowDownIcon', 'CheckCircleIcon', 'ExclamationTriangleIcon']) assert.match(view, new RegExp(icon), icon);
});

test('LabTechnician : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view, /@apply|h-\[calc\(100vh/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
});

test('clés labScreens (paillasse) en FR et EN', () => {
    const keys = ['refresh', 'external_badge', 'done_badge', 'batch_label', 'value_for', 'flag_for', 'note_for', 'sex_age', 'flag_clear', 'progress'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].labScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.labScreens.${k}`);
        }
    }
});
