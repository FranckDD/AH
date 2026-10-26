import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const modal = read('components/toxico/ToxicoDischargeModal.vue');
const store = read('stores/toxicoStore.js');
const gateway = read('services/ToxicoGateway.js');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

// Defaut releve par les guides (2026-10-26) : sortie toxico d'un patient hospitalise
// sans avertissement. La modale doit nommer le sejour ouvert et exiger une
// confirmation explicite ("garder le sejour ouvert en connaissance de cause").
test('gateway + store exposent l indicateur de sejour hospitalier ouvert', () => {
  assert.ok(gateway.includes('/open-hospitalization'));
  assert.ok(store.includes('fetchOpenHospitalization'));
});

test('la modale interroge le sejour ouvert, avertit et exige une confirmation', () => {
  for (const needle of [
    'toxicoStore.fetchOpenHospitalization(props.dossierId)',
    'openHosp.value',
    'v-model="ackHosp"',
    "t('toxico.stays.hosp_open_warning'",
    "t('toxico.stays.hosp_open_ack')",
    "toxico.stays.hosp_open_ack_required",
  ]) assert.ok(modal.includes(needle), needle);
});

test('la confirmation bloque l envoi tant qu elle n est pas cochee', () => {
  assert.match(modal, /if \(openHosp\.value && !ackHosp\.value\)/);
});

for (const key of ['hosp_open_warning', 'hosp_open_ack', 'hosp_open_ack_required']) {
  test(`i18n toxico.stays.${key} FR et EN, ASCII`, () => {
    for (const lang of ['fr', 'en']) {
      const v = pick(msgs[lang], `toxico.stays.${key}`);
      assert.ok(typeof v === 'string' && v.length > 5, `${lang}.${key}`);
      assert.ok(!/[\u2013\u2014\u2026\u00b7]/.test(v), `${lang}.${key} caractere non ASCII`);
    }
  });
}
