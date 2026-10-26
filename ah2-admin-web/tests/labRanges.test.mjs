import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeSex, rangeLabelForPatient } from '../src/utils/labRanges.js';

const male = { sexe: 'M', min: 4.5, max: 6.5 };
const female = { sexe: 'F', min: 4, max: 5.5 };
const any = { sexe: 'X', min: 1, max: 2 };

test('normalizeSex ramene tout vers M, F ou X', () => {
  assert.equal(normalizeSex('F'), 'F');
  assert.equal(normalizeSex('female'), 'F');
  assert.equal(normalizeSex('Femme'), 'F');
  assert.equal(normalizeSex('M'), 'M');
  assert.equal(normalizeSex('homme'), 'M');
  assert.equal(normalizeSex(null), 'X');
  assert.equal(normalizeSex('-'), 'X');
});

test('la plage du sexe du patient est choisie', () => {
  assert.equal(rangeLabelForPatient([male, female], 'F'), '4 - 5.5');
  assert.equal(rangeLabelForPatient([male, female], 'M'), '4.5 - 6.5');
});

test('une plage masculine seule n est jamais montree pour une femme', () => {
  assert.equal(rangeLabelForPatient([male], 'F'), '-');
});

test('la plage generique X sert quand le sexe n a pas la sienne', () => {
  assert.equal(rangeLabelForPatient([male, any], 'F'), '1 - 2');
  assert.equal(rangeLabelForPatient([any], '-'), '1 - 2');
});

test('sexe inconnu : toutes les plages sont montrees avec leur sexe, rien n est choisi au hasard', () => {
  assert.equal(rangeLabelForPatient([male, female], '-'), 'M 4.5 - 6.5 / F 4 - 5.5');
});

test('aucune plage : tiret', () => {
  assert.equal(rangeLabelForPatient([], 'F'), '-');
  assert.equal(rangeLabelForPatient(undefined, 'F'), '-');
});
