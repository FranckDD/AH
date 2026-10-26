import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const modal = read('components/toxico/ToxicoEvaluationModal.vue');
const list = read('views/modules/toxico/ToxicoList.vue');

// Defaut releve par les guides (2026-10-26) : l'evaluation etait enregistree
// deux fois (modale PUIS liste). Decision : la MODALE est seule proprietaire de
// l'envoi (elle gere les erreurs d'affichage) ; la liste ne fait que fermer.
test('la modale envoie l evaluation exactement une fois', () => {
  assert.equal((modal.match(/toxicoStore\.submitEvaluation\(/g) || []).length, 1);
});

test('ToxicoList ne renvoie pas l evaluation', () => {
  assert.equal(list.includes('submitEvaluation'), false);
});

test('ToxicoList ferme la modale sur save', () => {
  const m = list.match(/const handleSaveEvaluation[\s\S]*?\n\};/);
  assert.ok(m, 'handleSaveEvaluation introuvable');
  assert.ok(m[0].includes('closeEvalModal()'));
});
