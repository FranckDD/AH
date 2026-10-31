import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');

test('gateway reads the dossier of an offline passage by its client batch uuid', () => {
  const gw = read('services/labGateway.js');
  assert.match(gw, /getDossierByBatchUuid/);
  assert.match(gw, /\/labo\/batch-uuid\/\$\{encodeURIComponent\(batchUuid\)\}\/dossier/);
});

test('queued reception polls the server number and keeps the pending message otherwise', () => {
  const store = read('stores/labStore.js');
  assert.match(store, /this\.pollDossierForBatch\(batchUuid\)/);
  assert.match(store, /async pollDossierForBatch\(/);
  // une relecture lente d'un ancien passage ne doit jamais ecrire dans une nouvelle reception
  assert.match(store, /let dossierPollSeq = 0/);
  assert.match(store, /dossierPollSeq \+= 1/);
  assert.match(store, /seq === dossierPollSeq/);
  const vue = read('views/modules/labo/LabReception.vue');
  assert.match(vue, /labStore\.lastDossier \? \$t\('labScreens\.dossier_assigned_receipt'/);
  assert.match(vue, /dossier_pending_receipt/);
});

test('lab sheet layout setting is exposed on the config screen in both languages', () => {
  const vue = read('views/SystemConfig.vue');
  assert.match(vue, /cfg-lab-variant/);
  assert.match(vue, /value="centered_results"/);
  assert.match(vue, /value="left_laboratory"/);
  assert.match(read('stores/configStore.js'), /lab_sheet_title_variant: 'centered_results'/);
  const src = read('i18n.js');
  for (const k of ['lab_sheet_title_variant', 'lab_sheet_title_variant_help', 'lab_variant_centered', 'lab_variant_left']) {
    const lines = src.split('\n').filter((l) => l.trim().startsWith(`${k}:`));
    assert.equal(lines.length, 2, k);
  }
});
