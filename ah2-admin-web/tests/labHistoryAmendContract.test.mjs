import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const g = i18n.global;
const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');

const history = read('views/modules/labo/LabHistory.vue');
const passage = read('components/lab/LabHistoryPassage.vue');
const modal = read('components/lab/ResultDetailModal.vue');
const bench = read('views/modules/labo/LabTechnician.vue');

test('historique : bouton Corriger reserve aux roles de /amend, en ligne seulement', () => {
    assert.match(history, /hasRole\(\['laborantin', 'admin', 'ToxicoManager'\]\)/);
    assert.match(history, /navigator\.onLine === false/);
    assert.ok(history.includes("history_view.amend_offline"));
    assert.match(history, /query: \{ open: [^}]*amend: 1 \}/);
    assert.ok(history.includes(':can-amend="canAmend"'));
    assert.ok(history.includes('@amend='));
});

test('ligne de passage et detail : bouton visible seulement pour un resultat valide et canAmend', () => {
    assert.ok(passage.includes("'amend'") && passage.includes('canAmend'));
    assert.ok(passage.includes("status === 'completed'"));
    assert.ok(passage.includes("t('lab.technician.amend_btn')"));
    assert.ok(modal.includes('canAmend') && modal.includes("'amend'"));
    assert.ok(modal.includes("result.status === 'completed'"));
    assert.ok(modal.includes("t('lab.technician.amend_btn')"));
});

test('paillasse : ?amend=1 ouvre le dossier en mode correction, sans changer le reste', () => {
    assert.ok(bench.includes('route.query.amend'));
    assert.ok(bench.includes('startAmend()'));
    // comportement existant conserve
    for (const s of ['const target = Number(route.query.open);', 'openDossier(target)', 'const submitAmend = async', 'labStore.amendResult(targetId']) assert.ok(bench.includes(s), s);
});

test('cle de message hors ligne en FR et EN', () => {
    for (const l of ['fr', 'en']) assert.ok(g.te('lab.history_view.amend_offline', l), l);
});
