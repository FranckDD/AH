import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { normalizeSex, rangeLabelForDetail, selectRange } from '../src/utils/labRanges.js';

const here = dirname(fileURLToPath(import.meta.url));
const CASES = JSON.parse(readFileSync(resolve(here, '../../tests/fixtures/lab_range_cases.json'), 'utf-8'));

const male = { id: 1, sexe: 'M', min: 4.5, max: 6.5 };
const female = { id: 2, sexe: 'F', min: 4, max: 5.5 };
const any = { id: 3, sexe: 'X', min: 1, max: 2 };
const label = (ranges, sexe, age = null, ga = null) => rangeLabelForDetail({ ranges }, sexe, age, ga);

test('normalizeSex ramene tout vers M, F ou X', () => {
  assert.equal(normalizeSex('F'), 'F');
  assert.equal(normalizeSex('female'), 'F');
  assert.equal(normalizeSex('Femme'), 'F');
  assert.equal(normalizeSex('M'), 'M');
  assert.equal(normalizeSex('homme'), 'M');
  assert.equal(normalizeSex(null), 'X');
  assert.equal(normalizeSex('-'), 'X');
});

test('les memes cas que le serveur (tests/fixtures/lab_range_cases.json) donnent le meme choix', () => {
  assert.ok(CASES.length > 100);
  for (const c of CASES) {
    const got = selectRange(c.ranges, c.sex, c.age_days, c.ga_weeks);
    assert.equal(got ? got.id : null, c.expected_id, c.name);
  }
});

test('hors ligne : la plage du sexe du patient est choisie', () => {
  assert.equal(label([male, female], 'F'), '4 - 5.5');
  assert.equal(label([male, female], 'M'), '4.5 - 6.5');
});

test('une plage masculine seule n est jamais montree pour une femme', () => {
  assert.equal(label([male], 'F'), '-');
});

test('la plage generique X sert quand le sexe n a pas la sienne ; sexe inconnu : X seulement', () => {
  assert.equal(label([male, any], 'F'), '1 - 2');
  assert.equal(label([any], '-'), '1 - 2');
  assert.equal(label([male, female], '-'), '-');
});

test('aucune plage : tiret', () => {
  assert.equal(label([], 'F'), '-');
  assert.equal(rangeLabelForDetail({}, 'F'), '-');
  assert.equal(rangeLabelForDetail(undefined, 'F'), '-');
});

test('l age et la SA changent la plage affichee hors ligne', () => {
  const newborn = { id: 1, sexe: 'X', age_min_days: 0, age_max_days: 28, min: 10, max: 20 };
  const adult = { id: 2, sexe: 'X', age_min_days: 29, min: 12, max: 16 };
  const pregnant = { id: 3, sexe: 'F', ga_min_weeks: 14, ga_max_weeks: 27, min: 10.5, max: 14 };
  assert.equal(label([newborn, adult], 'M', 10), '10 - 20');
  assert.equal(label([newborn, adult], 'M', 9000), '12 - 16');
  assert.equal(label([newborn, adult], 'M', null), '-');
  assert.equal(label([adult, pregnant], 'F', 9000, 20), '10.5 - 14');
  assert.equal(label([adult, pregnant], 'F', 9000, null), '12 - 16');
});

test('le serveur fait foi : applicable_range (meme nulle) remplace la selection locale', () => {
  const ranges = [male, female];
  assert.equal(rangeLabelForDetail({ ranges, applicable_range: { min: 1, max: 3, text: '1 - 3' } }, 'F'), '1 - 3');
  assert.equal(rangeLabelForDetail({ ranges, applicable_range: { min: 1, max: 3 } }, 'F'), '1 - 3');
  assert.equal(rangeLabelForDetail({ ranges, applicable_range: null }, 'F'), '-');
});

test('les colonnes jours / SA traversent la synchro : flux PowerSync, schema local, requete hors ligne', () => {
  const cols = ['age_min_days', 'age_max_days', 'ga_min_weeks', 'ga_max_weeks'];
  const sync = readFileSync(resolve(here, '../../powersync/sync-config.yaml'), 'utf-8');
  const block = sync.slice(sync.indexOf('reference_lab_ranges:'));
  const schema = readFileSync(resolve(here, '../src/powersync-client/AppSchema.js'), 'utf-8');
  const gateway = readFileSync(resolve(here, '../src/services/labGateway.js'), 'utf-8');
  for (const c of cols) {
    assert.ok(block.includes(`reference_lab_ranges.${c}`), `flux ${c}`);
    assert.ok(schema.includes(`${c}: column.integer`), `schema ${c}`);
    assert.ok(gateway.includes(c), `gateway ${c}`);
  }
});
