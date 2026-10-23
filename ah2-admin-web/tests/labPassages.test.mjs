import { test } from 'node:test';
import assert from 'node:assert/strict';
import { groupPaillasse, groupHistory, passageProgress, examStatusMeta, isDone, passageKey, passageStatus, dayKeyOf, groupPassagesByDay, hasPrintable } from '../src/utils/labPassages.js';

const row = (id, nom, status, extra = {}) => ({ result_id: id, examen_nom: nom, status, patient_name: 'KOUAM Jean', patient_sexe: 'M', patient_age: 34, is_external: false, code: `LAB-${id}`, ...extra });

test('paillasse : trois examens a saisir du meme passage donnent un seul patient', () => {
    const exams = [{ result_id: 1, examen_nom: 'NFS', status: 'pending' }, { result_id: 2, examen_nom: 'Glycemie', status: 'pending' }, { result_id: 3, examen_nom: 'ALAT', status: 'completed' }];
    const items = [row(1, 'NFS', 'pending', { batch_id: 'b1', batch_exams: exams }), row(2, 'Glycemie', 'pending', { batch_id: 'b1', batch_exams: exams })];
    const [p, ...rest] = groupPaillasse(items);
    assert.equal(rest.length, 0);
    assert.equal(p.patient_name, 'KOUAM Jean');
    assert.deepEqual(p.exams.map((e) => e.result_id), [1, 2, 3]);       // l'examen termine est montre
    assert.deepEqual(p.pendingIds, [1, 2]);
    assert.equal(p.firstPendingId, 1);
    assert.deepEqual(p.progress, { done: 1, total: 3, pct: 33 });
});

test('paillasse : deux patients differents restent deux passages, dans l ordre de la liste', () => {
    const items = [row(5, 'NFS', 'pending', { batch_id: 'b2', patient_name: 'A' }), row(6, 'NFS', 'pending', { batch_id: 'b3', patient_name: 'B' })];
    assert.deepEqual(groupPaillasse(items).map((p) => p.patient_name), ['A', 'B']);
});

test('paillasse : un examen seul (sans batch_id) est un passage d un examen, sans lien avec les autres', () => {
    const items = [row(7, 'NFS', 'pending'), row(8, 'ALAT', 'pending')];
    const out = groupPaillasse(items);
    assert.equal(out.length, 2);
    assert.deepEqual(out.map((p) => p.exams.length), [1, 1]);
    assert.equal(out[0].key, 'solo-7');
});

test('paillasse : un examen de la liste est toujours montre meme si batch_exams ne le contient pas', () => {
    const [p] = groupPaillasse([row(9, 'NFS', 'pending', { batch_id: 'b4', batch_exams: [{ result_id: 10, examen_nom: 'ALAT', status: 'completed' }] })]);
    assert.deepEqual(p.exams.map((e) => e.result_id), [9, 10]);
});

test('paillasse : liste vide ou absente', () => {
    assert.deepEqual(groupPaillasse([]), []);
    assert.deepEqual(groupPaillasse(undefined), []);
});

test('historique : les examens d un meme passage sont groupes, l ordre des passages est celui de la page', () => {
    const items = [row(1, 'NFS', 'completed', { batch_id: 'bA', test_date: 't1' }), row(2, 'ALAT', 'pending', { batch_id: 'bA' }), row(3, 'NFS', 'completed', { batch_id: 'bB', patient_name: 'Z' })];
    const out = groupHistory(items);
    assert.deepEqual(out.map((p) => p.key), ['bA', 'bB']);
    assert.deepEqual(out[0].exams.map((e) => e.result_id), [1, 2]);
    assert.equal(out[0].test_date, 't1');
    assert.deepEqual(out[0].progress, { done: 1, total: 2, pct: 50 });
});

test('progression : aucun examen, tous termines', () => {
    assert.deepEqual(passageProgress([]), { done: 0, total: 0, pct: 0 });
    assert.equal(passageProgress([{ status: 'completed' }, { status: 'validated' }]).pct, 100);
});

test('etat d un examen : toujours un mot (cle) et une icone, en plus de la tonalite', () => {
    assert.deepEqual(examStatusMeta('pending'), { tone: 'warning', labelKey: 'lab.status.pending', icon: 'clock' });
    assert.equal(examStatusMeta('completed').tone, 'success');
    assert.equal(examStatusMeta('validated').labelKey, 'lab.status.validated');
    assert.equal(examStatusMeta('partial').labelKey, 'labScreens.status_in_progress');
    assert.equal(examStatusMeta(undefined).icon, 'beaker');
    assert.ok(isDone('completed') && isDone('validated') && !isDone('pending'));
});

test('cle de passage', () => {
    assert.equal(passageKey({ batch_id: 'x', result_id: 1 }), 'x');
    assert.equal(passageKey({ batch_id: null, result_id: 1 }), 'solo-1');
});

test('historique : le nombre d anomalies d un passage est la somme de ses examens', () => {
    const items = [row(1, 'NFS', 'completed', { batch_id: 'bA', nb_anormaux: 2 }), row(2, 'ALAT', 'completed', { batch_id: 'bA', nb_anormaux: 0 }), row(3, 'CRP', 'completed', { batch_id: 'bA' })];
    const [p] = groupHistory(items);
    assert.equal(p.abnormalCount, 2);
    assert.equal(groupHistory([row(4, 'NFS', 'completed')])[0].abnormalCount, 0);
});

test('etat global d un passage : termine, en attente, ou n sur total', () => {
    assert.deepEqual(passageStatus({ done: 3, total: 3 }), { tone: 'success', labelKey: 'lab.status.completed', params: {} });
    assert.equal(passageStatus({ done: 0, total: 3 }).tone, 'warning');
    assert.deepEqual(passageStatus({ done: 1, total: 3 }), { tone: 'info', labelKey: 'labScreens.passage_partial', params: { done: 1, total: 3 } });
    const [p] = groupHistory([row(1, 'NFS', 'completed', { batch_id: 'x' }), row(2, 'ALAT', 'pending', { batch_id: 'x' })]);
    assert.equal(p.status.labelKey, 'labScreens.passage_partial');
});

test('jours : cle de date et regroupement dans l ordre de la page', () => {
    assert.equal(dayKeyOf('2026-10-23T09:41:00'), '2026-10-23');
    assert.equal(dayKeyOf(''), 'unknown');
    assert.equal(dayKeyOf(undefined), 'unknown');
    const passages = [{ test_date: '2026-10-23T10:00:00' }, { test_date: '2026-10-23T08:00:00' }, { test_date: '2026-10-22T18:00:00' }, { test_date: '' }];
    const days = groupPassagesByDay(passages);
    assert.deepEqual(days.map((d) => [d.key, d.passages.length]), [['2026-10-23', 2], ['2026-10-22', 1], ['unknown', 1]]);
    assert.deepEqual(groupPassagesByDay(undefined), []);
});

test('imprimable : au moins un examen termine ou valide', () => {
    assert.equal(hasPrintable({ exams: [{ status: 'pending' }, { status: 'completed' }] }), true);
    assert.equal(hasPrintable({ exams: [{ status: 'pending' }] }), false);
});
