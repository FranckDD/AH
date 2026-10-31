import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

const tech = read('views/modules/labo/LabTechnician.vue');
const reception = read('views/modules/labo/LabReception.vue');
const store = read('stores/labStore.js');
const gateway = read('services/labGateway.js');
const schema = read('powersync-client/AppSchema.js');
const connector = read('powersync-client/DossierConnector.js');
const bell = read('components/notifications/NotificationBell.vue');
const modal = read('components/lab/ResultDetailModal.vue');
const history = read('components/lab/LabHistoryPassage.vue');

// ---------------------------------------------------------------- defaut 5 : resultat valide en lecture seule
test('LabTechnician : un resultat valide est en lecture seule, la correction passe par un motif', () => {
  for (const needle of [
    "activeDossier.value?.status === 'completed'", 'const isLocked', ':disabled="isLocked"', 'const amending = ref(false)',
    'const amendReason = ref', 'labStore.amendResult(', "t('lab.technician.amend_btn')", "t('lab.technician.locked_notice')",
    "t('lab.technician.amend_reason_label')", "t('lab.technician.amend_save')",
  ]) assert.ok(tech.includes(needle), `« ${needle} » manque dans LabTechnician`);
  // les boutons Valider ne sont plus montres sur un resultat verrouille
  assert.match(tech, /<ActionBar[^>]*v-if="!isLocked/);
});

test('labStore / labGateway : action de correction', () => {
  assert.ok(store.includes('async amendResult('));
  assert.ok(gateway.includes('async amendResult('));
  assert.ok(gateway.includes('`/labo/results/${resultId}/amend`'));
});

test('ResultDetailModal et LabHistory montrent le marquage corrige', () => {
  assert.ok(modal.includes('result.corrected'));
  assert.ok(modal.includes('result.amendments'));
  assert.ok(history.includes('corrected'));
});

test('NotificationBell : notification de correction vers le medecin', () => {
  assert.ok(bell.includes("n.type === 'lab_result_corrected'"));
  assert.ok(bell.includes('notifications.lab_result_corrected'));
});

// ---------------------------------------------------------------- defaut 6 : reception
test('LabReception : lignes facturees importables, envoyees avec leur ligne de facture', () => {
  for (const needle of ['invoiced_exams', 'is_invoiced', 'caisse_item_id', 'origin_caisse_item_id: item.caisse_item_id']) {
    assert.ok(reception.includes(needle), `« ${needle} » manque dans LabReception`);
  }
});

test('le lien ligne de facture -> dossier labo traverse les 4 couches PowerSync', () => {
  assert.ok(schema.includes('origin_caisse_item_id: column.integer'), 'AppSchema');
  assert.ok(store.includes('origin_caisse_item_id') && /INSERT INTO lab_results[\s\S]*origin_caisse_item_id/.test(store), 'INSERT local');
  assert.ok(connector.includes('origin_caisse_item_id: op.opData.origin_caisse_item_id'), 'connecteur');
  assert.ok(connector.includes('examen_id: op.opData.examen_id, uuid: op.id, origin_caisse_item_id'), 'corps de la requete');
});

// ---------------------------------------------------------------- defaut 9 : plage par sexe
test('les plages de reference passent par rangeLabelForDetail (jamais ranges[0] en repli)', () => {
  for (const [name, src] of [['LabTechnician', tech], ['ResultDetailModal', modal]]) {
    assert.ok(src.includes("from '@/utils/labRanges'"), name);
    assert.ok(!src.includes('|| ranges[0]'), `${name} retombe encore sur ranges[0]`);
  }
});

// ---------------------------------------------------------------- i18n
const KEYS = [
  'lab.technician.locked_notice', 'lab.technician.amend_btn', 'lab.technician.amend_reason_label', 'lab.technician.amend_reason_placeholder',
  'lab.technician.amend_save', 'lab.technician.amend_cancel', 'lab.technician.amend_success', 'lab.technician.corrected_badge',
  'lab.technician.amend_reason_required', 'lab.result_modal.corrected_title', 'lab.result_modal.corrected_by',
  'lab.result_modal.previous_value', 'lab.reception.invoiced_badge', 'labScreens.invoiced_count', 'labScreens.invoiced_imported',
  'notifications.lab_result_corrected',
];
test('cles FR et EN presentes, ASCII pour la ponctuation', () => {
  for (const k of KEYS) {
    for (const locale of ['fr', 'en']) {
      const v = pick(msgs[locale], k);
      assert.ok(typeof v === 'string' && v.length > 0, `${locale}.${k} manquante`);
      assert.ok(!/[\u2013\u2014\u2026\u00b7]/.test(v), `${locale}.${k} contient un caractere typographique`);
    }
  }
});
