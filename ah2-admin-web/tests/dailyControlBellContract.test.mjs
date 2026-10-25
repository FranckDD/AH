// Controle quotidien des Rapports (2026-10-25) : libelle et clic de la notification daily_control.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

const bell = readFileSync(new URL('../src/components/notifications/NotificationBell.vue', import.meta.url), 'utf8');
const scriptOf = (src) => src.slice(src.indexOf('<script'));

test('libelles FR/EN du controle quotidien, ponctuation ASCII', () => {
  for (const lang of ['fr', 'en']) {
    for (const key of ['notifications.daily_control', 'notifications.daily_control_reminder']) {
      const v = pick(msgs[lang], key);
      assert.equal(typeof v, 'string', `${lang}.${key}`);
      assert.ok(v.includes('{date}') && v.includes('{open}'), `${lang}.${key}`);
      assert.ok(!/[–—…·]/.test(v), `${lang}.${key} : ponctuation typographique`);
    }
    assert.ok(pick(msgs[lang], 'notifications.daily_control').includes('{new}'));
  }
});

test('libelle : rappel distinct, nouveaux et encore ouverts', () => {
  const s = scriptOf(bell);
  assert.ok(s.includes("if (n.type === 'daily_control') {"));
  assert.ok(s.includes("p.reason === 'rappel'"));
  assert.ok(s.includes("t('notifications.daily_control_reminder'"));
  assert.ok(s.includes("t('notifications.daily_control', params)"));
});

test('clic : page Rapports, promoteur et admin seulement', () => {
  assert.ok(scriptOf(bell).includes(
    "if (authStore.hasRole(['promoteur', 'admin'])) pushIfRoute('/dashboard/reports');"));
});
