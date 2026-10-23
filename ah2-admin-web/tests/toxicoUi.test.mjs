import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { PHASE_META, phaseMeta, percentOf, newThisWeek } from '../src/utils/toxicoUi.js';

test('phases : memes teintes qu avant (rouge, orange, bleu, vert) via les tonalites du theme', () => {
    assert.deepEqual([1, 2, 3, 4].map((p) => phaseMeta(p).tone), ['danger', 'warning', 'info', 'success']);
    assert.deepEqual(Object.values(PHASE_META).map((m) => m.bar), ['bg-tone-danger-solid', 'bg-tone-warning-solid', 'bg-tone-info-solid', 'bg-tone-success-solid']);
    assert.equal(phaseMeta(9).tone, 'neutral');
    assert.equal(phaseMeta(undefined).tone, 'neutral');
});

test('les jetons pleins utilises par les barres existent dans le theme', () => {
    const css = readFileSync(new URL('../src/style.css', import.meta.url), 'utf8');
    for (const t of ['danger', 'warning', 'info', 'success']) assert.match(css, new RegExp(`--color-tone-${t}-solid:\\s*#[0-9a-fA-F]{6}`), t);
});

test('part d une phase : zero sans patient, sinon proportion', () => {
    assert.equal(percentOf(0, 10), 0);
    assert.equal(percentOf(3, 0), 0);
    assert.equal(percentOf(undefined, 5), 0);
    assert.equal(percentOf(5, 20), 25);
});

test('nouveaux de la semaine : calcul reel sur la liste (admission ou creation dans les 7 jours)', () => {
    const now = new Date('2026-10-23T12:00:00');
    const iso = (d) => `${d}T08:00:00`;
    const patients = [
        { admissionDate: iso('2026-10-22') },        // hier : oui
        { admissionDate: iso('2026-10-10') },        // trop ancien
        { createdAt: iso('2026-10-20') },            // pas d'admission, creation recente : oui
        { admissionDate: 'pas une date' },           // illisible : non
        {},                                          // aucune date : non
    ];
    assert.equal(newThisWeek(patients, now), 2);
    assert.equal(newThisWeek([], now), 0);
    assert.equal(newThisWeek(undefined, now), 0);
});
