import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import dayjs from 'dayjs';
import { periodRange, shiftAnchor, weekDays } from '../src/utils/nurseShiftRange.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const f = (d) => d.format('YYYY-MM-DD');

test('semaine : du lundi au dimanche, quel que soit le jour choisi', () => {
    for (const day of ['2026-10-19', '2026-10-22', '2026-10-25']) {
        assert.deepEqual(periodRange('week', dayjs(day)), { start: '2026-10-19', end: '2026-10-25' }, day);
    }
    // dimanche = fin de semaine, pas début de la suivante
    assert.deepEqual(periodRange('week', dayjs('2026-10-25')), { start: '2026-10-19', end: '2026-10-25' });
    assert.deepEqual(periodRange('week', dayjs('2026-10-26')), { start: '2026-10-26', end: '2026-11-01' });
});

test('mois : grille de semaines complètes commençant le lundi (comme avant)', () => {
    // octobre 2026 : le 1er est un jeudi, le 31 un samedi
    assert.deepEqual(periodRange('month', dayjs('2026-10-22')), { start: '2026-09-28', end: '2026-11-01' });
    // février 2027 : le 1er est un lundi, le 28 un dimanche -> exactement 4 semaines
    assert.deepEqual(periodRange('month', dayjs('2027-02-10')), { start: '2027-02-01', end: '2027-02-28' });
});

test('vue inconnue : traitée comme la semaine', () => {
    assert.deepEqual(periodRange('???', dayjs('2026-10-22')), periodRange('week', dayjs('2026-10-22')));
});

test('navigation : une semaine ou un mois à la fois, dans les deux sens', () => {
    assert.equal(f(shiftAnchor('week', dayjs('2026-10-22'), 1)), '2026-10-29');
    assert.equal(f(shiftAnchor('week', dayjs('2026-10-22'), -1)), '2026-10-15');
    assert.equal(f(shiftAnchor('month', dayjs('2026-10-22'), 1)), '2026-11-22');
    assert.equal(f(shiftAnchor('month', dayjs('2026-10-22'), -1)), '2026-09-22');
});

test('weekDays : sept dates consécutives à partir du début de semaine', () => {
    assert.deepEqual(weekDays('2026-10-19'), [
        '2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23', '2026-10-24', '2026-10-25',
    ]);
    // passage de mois
    assert.equal(weekDays('2026-10-26')[6], '2026-11-01');
});

const KEYS = ['view_week', 'view_month', 'prev_week', 'next_week', 'day_column'];

test('clés nurseShift.* de la vue semaine en FR et EN', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        for (const k of KEYS) assert.equal(typeof msgs[locale].nurseShift[k], 'string', `${locale}.nurseShift.${k}`);
    }
});

const cal = readFileSync(new URL('../src/components/nurseshift/NurseShiftCalendar.vue', import.meta.url), 'utf8');

test('vue semaine : noms complets, jamais tronqués ni en texte réduit', () => {
    const week = cal.slice(cal.indexOf('data-view="week"'), cal.indexOf('data-view="month"'));
    assert.ok(week.length > 200, 'bloc de la vue semaine introuvable');
    assert.doesNotMatch(week, /\btruncate\b/);
    assert.doesNotMatch(week, /text-(xs|sm)\b/);
    assert.match(week, /text-base/);
    assert.match(week, /nursesByShift/);
});

test('la vue semaine est la vue par défaut et le choix est annoncé aux lecteurs d’écran', () => {
    assert.match(cal, /ref\('week'\)/);
    assert.match(cal, /aria-pressed/);
});
