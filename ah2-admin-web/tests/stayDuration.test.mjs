import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { formatStayDuration } from '../src/utils/stayDuration.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const L = { days: 'jour(s)', hours: 'h', minutes: 'min' };
const at = (s) => new Date(s);

test('moins d une heure : minutes', () => {
  assert.equal(formatStayDuration(at('2026-10-26T06:38:00'), at('2026-10-26T06:50:00'), L), '12 min');
});
test('moins d un jour : heures et minutes, jamais 0 jour(s)', () => {
  assert.equal(formatStayDuration(at('2026-10-26T06:38:00'), at('2026-10-26T09:10:00'), L), '2 h 32 min');
});
test('plusieurs jours', () => {
  assert.equal(formatStayDuration(at('2026-10-26T06:38:00'), at('2026-10-28T07:00:00'), L), '2 jour(s) 0 h');
});
test('fin avant debut (donnees anciennes) : 0 min, jamais negatif', () => {
  assert.equal(formatStayDuration(at('2026-10-26T06:38:00'), at('2026-10-26T05:47:00'), L), '0 min');
});
test('les ecrans de sejour utilisent l utilitaire (plus de diff en jours bruts)', () => {
  for (const f of ['components/hospitalization/HospitalizationCard.vue', 'views/modules/hospitalization/HospitalizationsList.vue']) {
    const src = readFileSync(new URL(`../src/${f}`, import.meta.url), 'utf8');
    assert.ok(src.includes('formatStayDuration'), f);
    assert.equal(src.includes(".diff(dayjs(d), 'day')"), false, f);
  }
});
test('i18n hospitalization.hours_short / minutes_short FR et EN', () => {
  for (const lang of ['fr', 'en']) for (const k of ['hours_short', 'minutes_short'])
    assert.ok(msgs[lang].hospitalization[k], `${lang}.${k}`);
});
