import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');

test('reception shows the dossier number or the not-yet-assigned state', () => {
  const vue = read('views/modules/labo/LabReception.vue');
  assert.match(vue, /lab-dossier-state/);
  assert.match(vue, /dossier_pending_receipt/);
  assert.match(vue, /dossier_assigned_receipt/);
  const store = read('stores/labStore.js');
  assert.match(store, /lastDossierPending = true/);
  assert.match(store, /this\.lastDossier = data\.dossier/);
  // le client n'envoie jamais de numero: il est attribue par le serveur
  assert.doesNotMatch(store, /dossier_counter|dossier_rank|dossier_year/);
});

test('history passage shows the number, never invents one', () => {
  const vue = read('components/lab/LabHistoryPassage.vue');
  assert.match(vue, /e\.dossier/);
  assert.match(vue, /dossier_pending/);
});

test('dossier i18n keys identical in FR and EN, ASCII only', () => {
  const src = read('i18n.js');
  const keys = ['dossier_label', 'dossier_pending', 'dossier_pending_receipt', 'dossier_assigned_receipt'];
  for (const k of keys) {
    const lines = src.split('\n').filter((l) => l.trim().startsWith(`${k}:`));
    assert.equal(lines.length, 2, k);
    for (const l of lines) assert.doesNotMatch(l, /[^\x00-\x7F]/, k);
  }
});

test('offline reception date travels from the local row to the server (day of the dossier number)', () => {
  const store = read('stores/labStore.js');
  assert.match(store, /const receivedAt = new Date\(\)\.toISOString\(\)/);
  assert.match(store, /origin_caisse_item_id, test_date/);
  const connector = read('powersync-client/DossierConnector.js');
  assert.match(connector, /SELECT test_date, gestational_age_weeks, external_pregnancy_info, pregnancy_status_at_result FROM lab_results WHERE id = \?/);
  assert.match(connector, /received_at: receivedAt/);
});
