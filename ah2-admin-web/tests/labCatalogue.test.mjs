import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  toDays, fromDays, validateRange, rangePayload, validateExam, examPayload, validateParam, paramPayload,
  validateNote, validateNotes, notesPayload, notesFromExam, blankNote, hasControlChars, NOTE_POSITIONS, NOTE_STYLES, CATALOGUE_LIMITS,
  parseChoices, moveInList, groupExams, serverCode, catalogueErrorMessage, normalizeText,
} from '../src/utils/labCatalogue.js';
import { ageFromExternal } from '../src/utils/labAge.js';

const R = (o = {}) => ({ sexe: 'X', valeur_min: '1', valeur_max: '2', age_min_days: null, age_max_days: null, ga_min_weeks: null, ga_max_weeks: null, ...o });

test('toDays : memes regles que ageFromExternal (lab_age.py)', () => {
  for (const [v, u] of [[5, 'jours'], [2, 'semaines'], [3, 'mois'], [1, 'ans'], [5, 'ans'], [2, 'ans'], [18, 'mois']]) {
    assert.equal(toDays(v, u), ageFromExternal(v, u));
  }
  assert.equal(toDays('4', 'semaines'), 28);
  assert.equal(toDays(5, 'ans'), 1826);
});

test('toDays : refuse non entier, negatif, trop grand, unite inconnue', () => {
  assert.equal(toDays('', 'jours'), null);
  assert.equal(toDays(null, 'jours'), null);
  assert.equal(toDays('1.5', 'jours'), null);
  assert.equal(toDays(-1, 'jours'), null);
  assert.equal(toDays(131, 'ans'), null);
  assert.equal(toDays(3, 'siecles'), null);
  assert.equal(toDays('abc', 'jours'), null);
});

test('fromDays : plus grande unite exacte, aller-retour exact', () => {
  assert.deepEqual(fromDays(0), { value: 0, unit: 'jours' });
  assert.deepEqual(fromDays(28), { value: 4, unit: 'semaines' });
  assert.deepEqual(fromDays(29), { value: 29, unit: 'jours' });
  assert.deepEqual(fromDays(7), { value: 1, unit: 'semaines' });
  assert.deepEqual(fromDays(365), { value: 1, unit: 'ans' });
  assert.equal(fromDays(null), null);
  assert.equal(fromDays(-3), null);
  for (const d of [0, 1, 6, 7, 14, 27, 28, 29, 30, 31, 60, 91, 365, 730, 1095, 1825, 1826, 6574, 47500]) {
    const f = fromDays(d);
    assert.equal(toDays(f.value, f.unit), d, `jours ${d}`);
  }
});

test('validateRange : plage valide', () => {
  assert.deepEqual(validateRange(R({ valeur_min: '0.7', valeur_max: '1.1' })), { errors: [], warnings: [] });
  assert.deepEqual(validateRange(R({ valeur_min: '1,5', valeur_max: '2' })).errors, []);
});

test('validateRange : min > max, valeurs manquantes ou non numeriques', () => {
  assert.deepEqual(validateRange(R({ valeur_min: '5', valeur_max: '2' })).errors, ['labCatalogue.errors.range_min_gt_max']);
  assert.deepEqual(validateRange(R({ valeur_min: '', valeur_max: '2' })).errors, ['labCatalogue.errors.range_values_required']);
  assert.deepEqual(validateRange(R({ valeur_min: 'x', valeur_max: '2' })).errors, ['labCatalogue.errors.range_values_number']);
  assert.deepEqual(validateRange(R({ valeur_min: '2', valeur_max: '2' })).errors, []);
});

test('validateRange : sexe, age et SA', () => {
  assert.ok(validateRange(R({ sexe: 'Z' })).errors.includes('labCatalogue.errors.range_sex'));
  assert.ok(validateRange(R({ age_min_days: 10, age_max_days: 5 })).errors.includes('labCatalogue.errors.range_age_order'));
  assert.ok(validateRange(R({ age_min_days: -1 })).errors.includes('labCatalogue.errors.range_age_bounds'));
  assert.ok(validateRange(R({ age_max_days: 47501 })).errors.includes('labCatalogue.errors.range_age_bounds'));
  assert.ok(validateRange(R({ age_min_days: NaN })).errors.includes('labCatalogue.errors.range_age_bounds'));
  assert.ok(validateRange(R({ ga_min_weeks: 46 })).errors.includes('labCatalogue.errors.range_ga_bounds'));
  assert.ok(validateRange(R({ ga_max_weeks: -1 })).errors.includes('labCatalogue.errors.range_ga_bounds'));
  assert.ok(validateRange(R({ ga_min_weeks: 30, ga_max_weeks: 20 })).errors.includes('labCatalogue.errors.range_ga_order'));
  assert.deepEqual(validateRange(R({ age_min_days: 0, age_max_days: 28, ga_min_weeks: 0, ga_max_weeks: 45 })).errors, []);
  assert.deepEqual(validateRange(R({ age_min_days: 5, age_max_days: 5 })).errors, []);
});

test('validateRange : doublon exact refuse, valeurs differentes seulement avertissement', () => {
  const a = R({ id: 1, age_min_days: 0, age_max_days: 28, valeur_min: 10, valeur_max: 20 });
  assert.deepEqual(validateRange(R({ age_min_days: 0, age_max_days: 28 , valeur_min: '10', valeur_max: '20' }), [a]).errors, ['labCatalogue.errors.range_duplicate']);
  const v = validateRange(R({ age_min_days: 0, age_max_days: 28, valeur_min: '11', valeur_max: '21' }), [a]);
  assert.deepEqual(v.errors, []);
  assert.deepEqual(v.warnings, ['labCatalogue.errors.range_overlap']);
});

test('validateRange : chevauchement ambigu en avertissement, pas entre criteres differents', () => {
  const nb = R({ id: 1, age_min_days: 0, age_max_days: 28, valeur_min: 10, valeur_max: 20 });
  const child = R({ age_min_days: 29, age_max_days: 1825, valeur_min: '9', valeur_max: '15' });
  assert.deepEqual(validateRange(child, [nb]), { errors: [], warnings: [] });
  const over = R({ age_min_days: 20, age_max_days: 60, valeur_min: '9', valeur_max: '15' });
  assert.deepEqual(validateRange(over, [nb]).warnings, ['labCatalogue.errors.range_overlap']);
  // une plage sexe M n'est pas ambigue avec une plage F
  const m = R({ sexe: 'M', id: 2, valeur_min: 1, valeur_max: 2 });
  assert.deepEqual(validateRange(R({ sexe: 'F', valeur_min: '3', valeur_max: '4' }), [m]).warnings, []);
  // plage age seule contre plage SA seule : criteres differents, pas d'ambiguite signalee
  const ageOnly = R({ id: 3, age_min_days: 0, age_max_days: 100 });
  assert.deepEqual(validateRange(R({ ga_min_weeks: 10, ga_max_weeks: 20, valeur_min: '5', valeur_max: '6' }), [ageOnly]).warnings, []);
  // bornes ouvertes qui se recouvrent
  const open = R({ id: 4, age_min_days: 29, valeur_min: 1, valeur_max: 2 });
  assert.deepEqual(validateRange(R({ age_max_days: 100, age_min_days: 50, valeur_min: '3', valeur_max: '4' }), [open]).warnings, ['labCatalogue.errors.range_overlap']);
});

test('rangePayload : nombres JSON, ages en jours, aucun prix', () => {
  const p = rangePayload(R({ sexe: 'f', valeur_min: '0,7', valeur_max: '1.1', age_min_days: 0, age_max_days: 28, ga_min_weeks: '', ga_max_weeks: '12' }));
  assert.deepEqual(p, { sexe: 'F', age_min_days: 0, age_max_days: 28, ga_min_weeks: null, ga_max_weeks: 12, valeur_min: 0.7, valeur_max: 1.1, display_text: null });
  assert.ok(!('prix' in p) && !('price' in p));
});

test('validateExam : creation et modification', () => {
  const ok = { code: 'nfs', nom: 'NFS', categorie: 'Hematologie', layout_family: 'table', sort_order: 3 };
  assert.deepEqual(validateExam(ok, { isNew: true }), {});
  assert.deepEqual(validateExam({ ...ok, code: '' }, { isNew: false }), {});
  assert.equal(validateExam({ ...ok, code: '' }, { isNew: true }).code, 'labCatalogue.errors.code_required');
  assert.equal(validateExam({ ...ok, code: 'a b' }, { isNew: true }).code, 'labCatalogue.errors.code_format');
  assert.equal(validateExam({ ...ok, code: 'A'.repeat(21) }, { isNew: true }).code, 'labCatalogue.errors.code_format');
  assert.equal(validateExam({ ...ok, nom: '  ' }).nom, 'labCatalogue.errors.name_required');
  assert.equal(validateExam({ ...ok, categorie: '' }).categorie, 'labCatalogue.errors.category_required');
  assert.equal(validateExam({ ...ok, layout_family: 'carte' }).layout_family, 'labCatalogue.errors.family_invalid');
  assert.equal(validateExam({ ...ok, sort_order: -1 }).sort_order, 'labCatalogue.errors.sort_order_invalid');
  assert.equal(validateExam({ ...ok, sort_order: '1.5' }).sort_order, 'labCatalogue.errors.sort_order_invalid');
  assert.equal(validateExam({ ...ok, method: 'x'.repeat(1001) }).method, 'labCatalogue.errors.too_long');
});

test('examPayload : sans prix, code seulement a la creation', () => {
  const form = { code: 'nfs', nom: ' NFS ', categorie: 'H', section: '', print_title: ' T ', method: '', layout_family: 'table', signature_label: '', sort_order: '', is_active: true, prix: 5000, price: 1 };
  const up = examPayload(form);
  assert.ok(!('code' in up) && !('prix' in up) && !('price' in up));
  assert.equal(up.nom, 'NFS');
  assert.equal(up.section, null);
  assert.equal(up.sort_order, 0);
  const cr = examPayload(form, { isNew: true });
  assert.equal(cr.code, 'NFS');
  assert.ok(!('prix' in cr));
});

test('validateParam / paramPayload / parseChoices', () => {
  assert.deepEqual(validateParam({ nom_parametre: 'Hb', unite: 'g/dl', result_kind: 'numeric' }), {});
  assert.equal(validateParam({ nom_parametre: '', result_kind: 'numeric' }).nom_parametre, 'labCatalogue.errors.param_name_required');
  assert.equal(validateParam({ nom_parametre: 'x', result_kind: 'zz' }).result_kind, 'labCatalogue.errors.kind_invalid');
  assert.equal(validateParam({ nom_parametre: 'x', result_kind: 'choice', choices_text: '' }).choices, 'labCatalogue.errors.choices_required');
  assert.equal(validateParam({ nom_parametre: 'x', result_kind: 'choice', choices_text: 'a\na' }).choices, 'labCatalogue.errors.choices_duplicate');
  assert.equal(validateParam({ nom_parametre: 'x', result_kind: 'choice', choices: ['a,b'] }).choices, 'labCatalogue.errors.choices_invalid');
  assert.equal(validateParam({ nom_parametre: 'x', result_kind: 'choice', choices: Array.from({ length: 31 }, (_, i) => `c${i}`) }).choices, 'labCatalogue.errors.choices_too_many');
  assert.deepEqual(parseChoices('Rare\n Moyen ;Abondant,\n\n'), ['Rare', 'Moyen', 'Abondant']);
  assert.deepEqual(paramPayload({ nom_parametre: ' Ha ', unite: '', print_label: '', result_kind: 'choice', choices_text: 'A\nB', is_active: false }),
    { nom_parametre: 'Ha', unite: '', print_label: null, group_label: null, norm_text: null, result_kind: 'choice', is_active: false, choices: ['A', 'B'] });
  assert.ok(!('choices' in paramPayload({ nom_parametre: 'x', result_kind: 'numeric' })));
});

test('moveInList : monter, descendre, bornes', () => {
  assert.deepEqual(moveInList([1, 2, 3], 1, -1), [2, 1, 3]);
  assert.deepEqual(moveInList([1, 2, 3], 1, 1), [1, 3, 2]);
  assert.equal(moveInList([1, 2, 3], 0, -1), null);
  assert.equal(moveInList([1, 2, 3], 2, 1), null);
  assert.equal(moveInList([1, 2, 3], 5, 1), null);
});

test('groupExams : par section dans l\'ordre du serveur, sans section en fin, recherche sans accent', () => {
  const exams = [
    { id: 1, code: 'NFS', nom: 'NFS', section: 'Hematologie' },
    { id: 2, code: 'TP', nom: 'Taux de prothrombine', section: '' },
    { id: 3, code: 'GS', nom: 'Groupe sanguin', section: 'Hematologie', is_active: false },
    { id: 4, code: 'VIH', nom: 'Serologie VIH', section: 'Serologie' },
  ];
  const g = groupExams(exams);
  assert.deepEqual(g.map((x) => x.section), ['Hematologie', 'Serologie', '']);
  assert.deepEqual(g[0].items.map((e) => e.id), [1, 3]);
  assert.deepEqual(groupExams(exams, '', false)[0].items.map((e) => e.id), [1]);
  assert.deepEqual(groupExams(exams, 'serolog').map((x) => x.items[0].id), [4]);
  assert.deepEqual(groupExams(exams, 'prothrombine').map((x) => x.items[0].id), [2]);
  assert.equal(normalizeText('Éléphant'), 'elephant');
});

test('erreurs serveur : code et message', () => {
  const err = (detail, extra = {}) => ({ response: { status: 409, data: { detail, ...extra } } });
  assert.equal(serverCode(err({ code: 'in_use', message: 'm' })), 'in_use');
  assert.equal(serverCode(err('texte traduit', { detail_raw: { code: 'in_use', message: 'm' } })), 'in_use');
  assert.equal(serverCode(err('texte')), null);
  assert.equal(catalogueErrorMessage(err({ code: 'in_use', message: 'Desactivez-le' })), 'Desactivez-le');
  assert.equal(catalogueErrorMessage(err('Acces refuse')), 'Acces refuse');
  assert.equal(catalogueErrorMessage(err([{ loc: ['body', 'valeur_min'], msg: 'requis' }])), 'valeur_min : requis');
  assert.equal(catalogueErrorMessage({}, 'repli'), 'repli');
});

// ---------------------------------------------------------------- C5 : textes imprimes et notes fixes
test('notes fixes : une note valide, position / style / texte obligatoires', () => {
  assert.equal(validateNote({ position: 'after_body', style: 'bold', text: 'Zones therapeutiques' }), null);
  assert.equal(validateNote({ position: 'milieu', style: 'bold', text: 'x' }), 'labCatalogue.errors.note_position_invalid');
  assert.equal(validateNote({ position: 'after_body', style: 'souligne', text: 'x' }), 'labCatalogue.errors.note_style_invalid');
  assert.equal(validateNote({ position: 'after_body', style: 'normal', text: '   ' }), 'labCatalogue.errors.note_text_required');
  assert.equal(validateNote({ position: 'after_body', style: 'normal', text: 'x'.repeat(1001) }), 'labCatalogue.errors.too_long');
  assert.equal(validateNote({ position: 'after_body', style: 'normal', text: 'x'.repeat(1000) }), null);
  assert.equal(validateNote({ position: 'after_body', style: 'normal', text: 'a\u0000b' }), 'labCatalogue.errors.control_chars');
  assert.equal(validateNote({ position: 'after_body', style: 'normal', text: 'ligne 1\nligne 2' }), null);
});

test('notes fixes : 12 au plus, erreur par note', () => {
  const ok = { position: 'before_body', style: 'normal', text: 'a' };
  assert.equal(CATALOGUE_LIMITS.notes, 12);
  assert.equal(validateNotes(Array(12).fill(ok)).list, null);
  assert.equal(validateNotes(Array(13).fill(ok)).list, 'labCatalogue.errors.notes_too_many');
  assert.deepEqual(validateNotes([ok, { ...ok, text: '' }]).items, [null, 'labCatalogue.errors.note_text_required']);
  assert.deepEqual(validateNotes(undefined), { items: [], list: null });
});

test('notes fixes : charge utile ordonnee, texte rogne, aucune cle en trop', () => {
  const list = [{ position: 'after_conclusion', style: 'italic', text: '  fin  ', extra: 1 }, { position: 'before_body', text: 'debut' }];
  assert.deepEqual(notesPayload(list), [
    { position: 'after_conclusion', text: 'fin', style: 'italic' }, { position: 'before_body', text: 'debut', style: 'normal' }]);
  assert.deepEqual(notesPayload(null), []);
  assert.deepEqual(notesFromExam({ fixed_notes: [{ position: 'after_body', text: 'a', style: 'bold' }] }), [{ position: 'after_body', style: 'bold', text: 'a' }]);
  assert.deepEqual(notesFromExam({ fixed_notes: null }), []);
  assert.deepEqual(blankNote(), { position: 'after_body', style: 'normal', text: '' });
  assert.deepEqual(NOTE_POSITIONS, ['before_body', 'after_body', 'after_conclusion']);
  assert.deepEqual(NOTE_STYLES, ['normal', 'bold', 'italic']);
});

test('examen : les notes fixes passent dans la validation et la charge utile', () => {
  const form = { nom: 'NFS', categorie: 'Hematologie', layout_family: 'table', sort_order: 1, is_active: true,
    fixed_notes: [{ position: 'before_body', style: 'bold', text: 'NUMERATION' }] };
  assert.deepEqual(validateExam(form), {});
  assert.deepEqual(examPayload(form).fixed_notes, [{ position: 'before_body', text: 'NUMERATION', style: 'bold' }]);
  assert.deepEqual(examPayload({ ...form, fixed_notes: [] }).fixed_notes, []);
  assert.equal(validateExam({ ...form, fixed_notes: [{ position: 'before_body', style: 'bold', text: '' }] }).fixed_notes,
    'labCatalogue.errors.note_text_required');
  assert.equal(validateExam({ ...form, fixed_notes: Array(13).fill(form.fixed_notes[0]) }).fixed_notes,
    'labCatalogue.errors.notes_too_many');
});

test('parametre : sous-titre (80) et texte de norme (200)', () => {
  const base = { nom_parametre: 'GB', result_kind: 'numeric' };
  assert.deepEqual(validateParam({ ...base, group_label: 'x'.repeat(80), norm_text: 'y'.repeat(200) }), {});
  assert.equal(validateParam({ ...base, group_label: 'x'.repeat(81) }).group_label, 'labCatalogue.errors.too_long');
  assert.equal(validateParam({ ...base, norm_text: 'y'.repeat(201) }).norm_text, 'labCatalogue.errors.too_long');
  assert.equal(validateParam({ ...base, norm_text: 'a\u0001' }).norm_text, 'labCatalogue.errors.control_chars');
  const out = paramPayload({ ...base, group_label: '  NUMERATION  ', norm_text: 'VN > 20 M/ml' });
  assert.equal(out.group_label, 'NUMERATION');
  assert.equal(out.norm_text, 'VN > 20 M/ml');
  assert.equal(paramPayload({ ...base, group_label: ' ', norm_text: '' }).group_label, null);
  assert.equal(paramPayload({ ...base }).norm_text, null);
});

test('plage : texte imprime (60) valide et envoye', () => {
  const r = { sexe: 'M', valeur_min: '4', valeur_max: '5.5', display_text: '4,0 - 5,5' };
  assert.deepEqual(validateRange(r).errors, []);
  assert.equal(rangePayload(r).display_text, '4,0 - 5,5');
  assert.equal(rangePayload({ ...r, display_text: '  ' }).display_text, null);
  assert.deepEqual(validateRange({ ...r, display_text: 'x'.repeat(61) }).errors, ['labCatalogue.errors.too_long']);
  assert.deepEqual(validateRange({ ...r, display_text: 'x'.repeat(60) }).errors, []);
  assert.deepEqual(validateRange({ ...r, display_text: 'a\u0000' }).errors, ['labCatalogue.errors.control_chars']);
});

test('hasControlChars : le retour a la ligne est permis dans une note seulement', () => {
  assert.equal(hasControlChars('a\nb'), true);
  assert.equal(hasControlChars('a\nb', true), false);
  assert.equal(hasControlChars('a\u0000b', true), true);
  assert.equal(hasControlChars('texte < 5 & é'), false);
});
