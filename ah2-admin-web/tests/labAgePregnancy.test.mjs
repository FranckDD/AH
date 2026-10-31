// Tache B4 : age exact (port JS de utils/lab_age.py), unites, SA proposee depuis la DPA, grossesse masquee a la
// secretaire (aides pures + contrats de source), menu et route du rapport reserves au promoteur et a l'admin.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ageFromExternal, ageInDays, ageLabelFromBirth, formatAge, gestationalFromDpa, tryAgeFromExternal, tryAgeInDays,
} from '../src/utils/labAge.js';
import {
  GA_MAX, PREGNANCY_READ_ROLES, PREGNANCY_WRITE_ROLES, batchGestationalWeeks, canEditPregnancyOnPatientFile, canSeePregnancy,
  canWritePregnancy, externalPregnancyPayload, parseGestationalWeeks, pregnancyApplies,
} from '../src/utils/pregnancy.js';
import { MAX_RANGE_DAYS, defaultPeriod, periodError } from '../src/utils/pregnancyReport.js';
import { hasRoleFor, parseMenuItems } from './helpers_mainLayoutMenu.mjs';
import { buildMenu } from '../src/utils/sidebarMenu.js';

const here = dirname(fileURLToPath(import.meta.url));
const read = (rel) => readFileSync(resolve(here, rel), 'utf-8').replace(/\r\n/g, '\n');
const CASES = JSON.parse(readFileSync(resolve(here, '../../tests/fixtures/lab_age_cases.json'), 'utf-8'));
const storeFor = (role) => ({ hasRole: hasRoleFor(role) });

// ---------------------------------------------------------------- age : fixture partagee avec pytest
test('formatAge : memes libelles que utils/lab_age.py sur toute la fixture partagee', () => {
  const entries = Object.entries(CASES.format_age);
  assert.ok(entries.length > 1000);
  for (const [days, label] of entries) assert.equal(formatAge(Number(days)), label, `jours=${days}`);
});

test('formatAge : cas cles', () => {
  assert.equal(formatAge(5), '5 jours');
  assert.equal(formatAge(17), '2 semaines 3 jours');
  assert.equal(formatAge(0), '0 jour');
  assert.equal(formatAge(1825), '4 ans 11 mois');
  assert.throws(() => formatAge(-1));
});

test('ageFromExternal : memes conversions et memes refus que le serveur (arrondi moitie vers le pair)', () => {
  assert.ok(CASES.age_from_external.length > 50);
  for (const [value, unit, expected] of CASES.age_from_external) {
    if (expected === null) assert.throws(() => ageFromExternal(value, unit), `${value} ${unit}`);
    else assert.equal(ageFromExternal(value, unit), expected, `${value} ${unit}`);
  }
  assert.equal(ageFromExternal(24, 'mois'), 730); // 730,5 arrondi au pair, comme round() de Python
});

test('ageInDays : memes ecarts que le serveur, naissance future refusee', () => {
  for (const [birth, ref, expected] of CASES.age_in_days) {
    if (expected === null) assert.throws(() => ageInDays(birth, ref));
    else assert.equal(ageInDays(birth, ref), expected, `${birth} -> ${ref}`);
  }
});

test('conversion d une saisie en libelle exact : 2 semaines 3 jours', () => {
  assert.equal(formatAge(ageFromExternal(17, 'jours')), '2 semaines 3 jours');
  assert.equal(formatAge(ageFromExternal(2, 'semaines')), '2 semaines');
  assert.equal(formatAge(ageFromExternal(3, 'mois')), '3 mois');
  assert.equal(formatAge(ageFromExternal(30, 'ans')), '30 ans');
  assert.equal(tryAgeFromExternal(-1, 'jours'), null);
  assert.equal(tryAgeFromExternal(1.5, 'mois'), null);
  assert.equal(tryAgeFromExternal(3, 'siecles'), null);
});

test('naissance : libelle exact depuis la date de naissance, vide si absente ou future', () => {
  assert.equal(ageLabelFromBirth('2026-10-14', '2026-10-31'), '2 semaines 3 jours');
  assert.equal(ageLabelFromBirth('', '2026-10-31'), '');
  assert.equal(ageLabelFromBirth(null, '2026-10-31'), '');
  assert.equal(ageLabelFromBirth('2026-11-05', '2026-10-31'), '');
  assert.equal(tryAgeInDays('2026-02-30', '2026-10-31'), null);
});

// ---------------------------------------------------------------- SA depuis la DPA
test('SA proposee : 40 - floor((DPA - reference) / 7), bornee a 0..45, memes valeurs que le serveur', () => {
  for (const [dpa, ref, expected] of CASES.sa_from_dpa) assert.equal(gestationalFromDpa(dpa, ref), expected, `${dpa} / ${ref}`);
  assert.equal(gestationalFromDpa('2027-01-01', '2026-10-31'), 32);
  assert.equal(gestationalFromDpa('2026-10-31', '2026-10-31'), 40);
  assert.equal(gestationalFromDpa('2026-10-30', '2026-10-31'), 41); // DPA depassee d un jour : floor vers le bas
  assert.equal(gestationalFromDpa('2025-01-01', '2026-10-31'), null);
  assert.equal(gestationalFromDpa('2030-01-01', '2026-10-31'), null);
  assert.equal(gestationalFromDpa('2026-10-03', '2026-10-31'), 44);
  assert.equal(gestationalFromDpa('2026-10-02', '2026-10-31'), null);
  assert.equal(gestationalFromDpa('2027-09-18', '2026-10-31'), 0);
  assert.equal(gestationalFromDpa('2027-09-19', '2026-10-31'), null);
  assert.equal(gestationalFromDpa('pas une date', '2026-10-31'), null);
});

test('SA saisie : entier de 0 a 45 seulement', () => {
  assert.deepEqual(parseGestationalWeeks(''), { ok: true, value: null });
  assert.deepEqual(parseGestationalWeeks('20'), { ok: true, value: 20 });
  assert.deepEqual(parseGestationalWeeks(0), { ok: true, value: 0 });
  assert.equal(parseGestationalWeeks(GA_MAX).ok, true);
  for (const bad of [-1, 46, '12.5', 'abc', 99]) assert.equal(parseGestationalWeeks(bad).ok, false, String(bad));
});

// ---------------------------------------------------------------- visibilite : la secretaire ne voit rien
test('roles : lecture medecin, infirmier, laboratoire, admin, promoteur ; ecriture sans le promoteur', () => {
  assert.deepEqual([...PREGNANCY_READ_ROLES].sort(), ['admin', 'laborantin', 'medecin', 'nurse', 'promoteur']);
  assert.deepEqual([...PREGNANCY_WRITE_ROLES].sort(), ['admin', 'laborantin', 'medecin', 'nurse']);
  for (const r of PREGNANCY_READ_ROLES) assert.equal(canSeePregnancy(storeFor(r)), true, r);
  for (const r of ['secretaire', 'Assistant', 'ToxicoManager', 'Psychologist', 'SpiritualCounsellor', 'StockController', 'ProductionManager', 'manager']) {
    assert.equal(canSeePregnancy(storeFor(r)), false, r);
    assert.equal(canWritePregnancy(storeFor(r)), false, r);
  }
  assert.equal(canWritePregnancy(storeFor('promoteur')), false);
  assert.equal(canSeePregnancy(null), false);
  // la fiche patient s enregistre par PUT /patients/{id} : medecin, infirmier, admin seulement
  assert.equal(canEditPregnancyOnPatientFile(storeFor('medecin')), true);
  assert.equal(canEditPregnancyOnPatientFile(storeFor('laborantin')), false);
  assert.equal(canEditPregnancyOnPatientFile(storeFor('promoteur')), false);
});

test('la secretaire n envoie aucune cle de grossesse (ni statut, ni SA), meme avec des valeurs saisies', () => {
  const form = { gender: 'F', pregnancy_status: 'enceinte', expected_delivery_date: '2027-01-01', pregnancy_program_number: 'P1' };
  assert.deepEqual(externalPregnancyPayload(form, storeFor('secretaire')), {});
  assert.deepEqual(externalPregnancyPayload(form, storeFor('promoteur')), {});
  assert.equal(batchGestationalWeeks('enceinte', '20', storeFor('secretaire')), null);
});

test('le laborantin envoie statut, DPA et numero de suivi seulement pour une femme ou un sexe inconnu', () => {
  const base = { pregnancy_status: 'enceinte', expected_delivery_date: '2027-01-01', pregnancy_program_number: ' P1 ' };
  assert.deepEqual(externalPregnancyPayload({ ...base, gender: 'F' }, storeFor('laborantin')),
    { pregnancy_status: 'enceinte', expected_delivery_date: '2027-01-01', pregnancy_program_number: 'P1' });
  assert.deepEqual(externalPregnancyPayload({ ...base, gender: 'X' }, storeFor('laborantin')).pregnancy_status, 'enceinte');
  assert.deepEqual(externalPregnancyPayload({ ...base, gender: 'M' }, storeFor('laborantin')), {});
  // statut par defaut : inconnu, sans DPA ni numero
  assert.deepEqual(externalPregnancyPayload({ gender: 'F' }, storeFor('laborantin')), { pregnancy_status: 'inconnu' });
  assert.deepEqual(externalPregnancyPayload({ gender: 'F', pregnancy_status: 'non_enceinte', expected_delivery_date: '2027-01-01' }, storeFor('admin')),
    { pregnancy_status: 'non_enceinte' });
  assert.equal(batchGestationalWeeks('enceinte', '20', storeFor('laborantin')), 20);
  assert.equal(batchGestationalWeeks('enceinte', '', storeFor('laborantin')), null);
  assert.equal(batchGestationalWeeks('enceinte', '99', storeFor('laborantin')), null);
  assert.equal(batchGestationalWeeks('inconnu', '20', storeFor('laborantin')), null);
  assert.equal(pregnancyApplies('M'), false);
  assert.equal(pregnancyApplies('F'), true);
  assert.equal(pregnancyApplies(null), true);
});

// ---------------------------------------------------------------- contrats de source
test('fiche patient : le bloc grossesse n est monte que pour un role lecteur, via authStore.hasRole', () => {
  const view = read('../src/views/modules/patients/PatientDetailView.vue');
  assert.match(view, /<PatientPregnancyBlock v-if="showPregnancyBlock"/);
  assert.match(view, /showPregnancyBlock = computed\(\(\) => canSeePregnancy\(authStore\)/);
  // aucun libelle ni champ de grossesse en dehors du composant garde
  assert.ok(!/pregnancy\./.test(view.replace(/PatientPregnancyBlock/g, '')), 'la vue ne porte aucun libelle de grossesse');
  const util = read('../src/utils/pregnancy.js');
  assert.match(util, /export function canSeePregnancy\(authStore\)[\s\S]*authStore\.hasRole\(PREGNANCY_READ_ROLES\)/);
});

test('bloc de la fiche : en ligne seulement (aucune copie locale), PUT /patients, message hors ligne', () => {
  const block = read('../src/components/patients/PatientPregnancyBlock.vue');
  assert.match(block, /api\.put\(`\/patients\/\$\{props\.patientId\}`/);
  assert.match(block, /navigator\.onLine/);
  assert.match(block, /pregnancy\.file_offline/);
  assert.ok(!/powersync|db\.execute|writeTransaction/i.test(block), 'aucune ecriture locale PowerSync');
  assert.match(block, /:disabled="!online \|\| !loaded"/);
});

test('reception : les cles de grossesse passent uniquement par les aides gardees par role', () => {
  const rec = read('../src/views/modules/labo/LabReception.vue');
  assert.match(rec, /const extPreg = externalPregnancyPayload\(extForm\.value, authStore\)/);
  assert.match(rec, /payload\.external_pregnancy_info = extPreg/);
  assert.ok(!/external_patient_info = \{[^}]*extPreg/s.test(rec), 'grossesse jamais dans external_patient_info');
  assert.match(rec, /batchGestationalWeeks\(pregnancyStatusNow\.value, gaWeeks\.value, authStore\)/);
  // le payload ne ecrit jamais directement un champ de grossesse
  const submit = rec.slice(rec.indexOf('const submitRequest'));
  assert.ok(!/pregnancy_status\s*:/.test(submit) && !/expected_delivery_date\s*:/.test(submit));
  assert.match(rec, /showExternalPregnancy = computed\(\(\) => mode\.value === 'external' && canWritePregnancy\(authStore\)/);
  assert.match(rec, /showInternalPregnancy = computed\(\(\) => mode\.value === 'internal' && !!selectedPatient\.value && canWritePregnancy\(authStore\)/);
  assert.match(rec, /age_days: extAgeDays\.value/);
  assert.match(rec, /age: extLegacyYears\.value/);
  assert.match(rec, /data-testid="pregnancy-block-external"/);
  assert.match(rec, /v-if="showExternalPregnancy"/);
  assert.match(rec, /v-if="showInternalPregnancy"/);
});

test('hors ligne : la SA de la demande suit les quatre couches PowerSync, le reste des grossesses n est pas synchronise', () => {
  assert.match(read('../src/powersync-client/AppSchema.js'), /gestational_age_weeks: column\.integer/);
  assert.match(read('../src/stores/labStore.js'), /origin_caisse_item_id, test_date, gestational_age_weeks/);
  const conn = read('../src/powersync-client/DossierConnector.js');
  assert.match(conn, /SELECT test_date, gestational_age_weeks, external_pregnancy_info, pregnancy_status_at_result FROM lab_results WHERE id = \?/);
  assert.match(conn, /gestational_age_weeks: gestationalWeeks/);
  assert.match(conn, /external_pregnancy_info: externalPregnancy/);
  assert.match(conn, /pregnancy_status_at_result: statusAtResult/);
  assert.match(read('../src/powersync-client/AppSchema.js'), /external_pregnancy_info: column\.text/);
  assert.match(read('../src/stores/labStore.js'), /external_pregnancy_info, pregnancy_status_at_result/);
  const sync = readFileSync(resolve(here, '../../powersync/sync-config.yaml'), 'utf-8');
  assert.ok(!/pregnan|gestational|expected_delivery/i.test(sync), 'aucun flux ne livre la grossesse');
});

test('en-tete de la fiche patient : age exact depuis la naissance du dossier', () => {
  const header = read('../src/components/patients/PatientHeader.vue');
  assert.match(header, /ageLabel/);
  assert.match(read('../src/views/modules/patients/PatientDetailView.vue'), /:age-label="exactAgeLabel"/);
});

// ---------------------------------------------------------------- rapport : menu, route, periode, i18n
test('menu : l entree du rapport n existe que pour le promoteur et l admin', () => {
  const items = parseMenuItems();
  const item = items.find((i) => i.path === '/dashboard/pregnancy-report');
  assert.ok(item);
  assert.deepEqual([...item.roles].sort(), ['admin', 'promoteur']);
  const groups = {};
  for (const role of ['admin', 'promoteur', 'laborantin', 'ToxicoManager', 'Psychologist', 'SpiritualCounsellor', 'Assistant', 'StockController', 'ProductionManager']) {
    const entries = buildMenu(items, { isAdmin: role === 'admin', hasRole: hasRoleFor(role), groups });
    const has = entries.some((e) => e.type === 'link' && e.item.path === '/dashboard/pregnancy-report');
    assert.equal(has, role === 'admin' || role === 'promoteur', role);
  }
});

test('route : le rapport est reserve au promoteur et a l admin', () => {
  const router = read('../src/router/index.js');
  const m = router.match(/path: 'pregnancy-report',[\s\S]*?meta: \{([^}]*)\}/);
  assert.ok(m);
  assert.match(m[1], /roles: \[ROLES\.ADMIN, ROLES\.PROMOTEUR\]/);
});

test('periode du rapport : meme regle que le serveur (366 jours au plus)', () => {
  assert.equal(MAX_RANGE_DAYS, 366);
  assert.deepEqual(defaultPeriod('2026-10-31'), { from: '2026-10-01', to: '2026-10-31' });
  assert.equal(periodError('2026-01-01', '2027-01-01'), null); // 366 jours inclusifs
  assert.equal(periodError('2026-01-01', '2027-01-02'), 'range');
  assert.equal(periodError('2026-03-10', '2026-03-09'), 'order');
  assert.equal(periodError('', '2026-03-09'), 'invalid');
  assert.equal(periodError('2026-02-30', '2026-03-09'), 'invalid');
});

test('i18n : memes cles en francais et en anglais pour pregnancy, ponctuation ASCII', () => {
  const src = read('../src/i18n.js');
  const blocks = [...src.matchAll(/\n    pregnancy: \{\n([\s\S]*?)\n    \},\n/g)].map((m) => m[1]);
  assert.equal(blocks.length, 2);
  const keys = (b) => [...b.matchAll(/^\s{6}(\w+): "/gm)].map((m) => m[1]);
  assert.deepEqual(keys(blocks[0]), keys(blocks[1]));
  assert.ok(keys(blocks[0]).length > 40);
  for (const b of blocks) assert.ok(!/[–—…·→]/.test(b), 'pas de tiret long, points de suspension ni point median');
});

test('ecrans : jetons seulement, aucune couleur codee en dur, textes >= 14 px', () => {
  for (const f of ['../src/views/modules/reports/PregnancyReport.vue', '../src/components/patients/PatientPregnancyBlock.vue']) {
    const src = read(f);
    assert.ok(!/#[0-9a-fA-F]{3,6}\b/.test(src), `${f} : pas de couleur en dur`);
    assert.ok(!/text-(xs|\[1[0-3]px\])/.test(src), `${f} : texte trop petit`);
    assert.match(src, /min-h-11/);
  }
});
