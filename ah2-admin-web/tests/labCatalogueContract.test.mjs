import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const pick = (o, path) => path.split('.').reduce((x, k) => x?.[k], o);

const view = read('../src/views/modules/labo/LabConfig.vue');
const form = read('../src/components/labo/CatalogueExamForm.vue');
const table = read('../src/components/labo/CatalogueParamTable.vue');
const ranges = read('../src/components/labo/CatalogueRangeEditor.vue');
const gateway = read('../src/services/LabCatalogueGateway.js');
const all = { view, form, table, ranges, gateway };

test('passerelle : toutes les routes /labo/catalogue/* de C2', () => {
  for (const frag of [
    "'/labo/catalogue'", '/exams`', '/exams/${id}`', '/exams/order`', '/exams/${id}/order`', '/parameters`', '/parameters/${id}`',
    '/parameters/${id}/order`', '/exams/${examId}/parameters/order`', '/ranges`', '/ranges/${id}`',
  ]) assert.ok(gateway.includes(frag), frag);
});

test('aucune charge utile du catalogue ne porte de prix', () => {
  for (const [name, src] of Object.entries(all)) {
    assert.ok(!/\bprix\s*:/.test(src), `${name} envoie un prix`);
    assert.ok(!/payload\.prix|form\.prix|price:/.test(src), `${name} lit/envoie un prix`);
  }
  // le prix n'est qu'affiche (lecture seule) et renvoie vers la configuration
  assert.ok(form.includes('exam?.prix'));
  assert.ok(form.includes("name: 'system-config'"));
  assert.ok(!/v-model="form\.prix"/.test(form));
});

test('controles d\'edition reserves a canEditLabCatalogue, en ligne seulement', () => {
  assert.ok(view.includes('authStore.canEditLabCatalogue'));
  assert.ok(view.includes('const editable = computed(() => canEdit.value && online.value)'));
  assert.ok(view.includes('v-if="canEdit"'));
  assert.ok(view.includes(':editable="editable"'));
  assert.ok(view.includes("window.addEventListener('offline', syncOnline)"));
  assert.ok(view.includes("t('labCatalogue.offline_save')"));
  for (const [name, src] of Object.entries({ form, table, ranges })) {
    assert.ok(src.includes('editable'), `${name} ignore editable`);
  }
  // formulaires d'ecriture masques quand non editable
  assert.ok(table.includes('<form v-if="editable"'));
  assert.ok(ranges.includes('<form v-if="editable"'));
  assert.ok(form.includes('<ActionBar v-if="editable">'));
  // le brouillon n'est pas efface par un echec d'envoi : les formulaires ne se vident qu'apres succes (done)
  assert.ok(table.includes('done: reset') && ranges.includes('done: reset'));
  assert.ok(view.includes('if (ok && done) done()'));
});

test('code readonly apres creation, famille issue de la liste fermee, actif, ordre', () => {
  assert.ok(form.includes(':readonly="!isNew"'));
  assert.ok(form.includes('v-for="f in LAYOUT_FAMILIES"'));
  assert.ok(form.includes("'labCatalogue.families.' + form.layout_family + '_desc'"));
  for (const id of ['cat-nom', 'cat-print-title', 'cat-categorie', 'cat-section', 'cat-sort', 'cat-method', 'cat-family', 'cat-signature', 'cat-active']) {
    assert.ok(form.includes(`id="${id}"`), id);
  }
  assert.ok(table.includes("emit('move'") || table.includes("$emit('move'"));
  assert.ok(view.includes('LabCatalogueGateway.orderParams') && view.includes('LabCatalogueGateway.moveExam'));
});

test('suppression avec confirmation, 409 in_use propose de desactiver', () => {
  assert.ok(view.includes('window.confirm(t(\'labCatalogue.exam.delete_confirm\''));
  assert.ok(view.includes('window.confirm(t(\'labCatalogue.param.delete_confirm\''));
  assert.ok(view.includes('window.confirm(t(\'labCatalogue.range.delete_confirm\''));
  assert.ok(view.includes("serverCode(err) === 'in_use'"));
  assert.ok(view.includes('is_active: false'));
  assert.ok(view.includes("t('labCatalogue.deactivate_instead')"));
});

test('bandeau des anciennes normes et lecture seule pour les autres laborantins', () => {
  assert.ok(view.includes('data-testid="snapshot-banner"'));
  assert.ok(view.includes('data-testid="readonly-banner"'));
  assert.equal(msgs.fr.labCatalogue.snapshot_banner.startsWith('Les résultats déjà validés gardent leurs anciennes normes'), true);
  assert.equal(msgs.en.labCatalogue.snapshot_banner.startsWith('Already validated results keep their old norms'), true);
  const layout = read('../src/views/modules/labo/LabLayout.vue');
  assert.ok(layout.includes("canConfigure = computed(() => authStore.hasRole(['admin', 'laborantin']))"));
  const router = read('../src/router/index.js');
  assert.ok(/name: 'lab-config'[\s\S]{0,600}roles: \['admin', 'laborantin'\]/.test(router));
});

test('plages : unite d\'age convertie en jours, SA avec aide, validation avant envoi', () => {
  assert.ok(ranges.includes('toDays(f.ageMin, f.unit)') && ranges.includes('validateRange(draft.value'));
  assert.ok(ranges.includes("t('labCatalogue.range.ga_help')"));
  assert.ok(ranges.includes('if (verdict.value.errors.length) return;'));
  assert.ok(ranges.includes('data-testid="range-warning"'));
});

test('pas de texte sous 14 px, jetons seulement, ponctuation ASCII', () => {
  for (const [name, src] of Object.entries({ view, form, table, ranges })) {
    assert.ok(!/\btext-xs\b/.test(src), `${name} : text-xs`);
    assert.ok(!/text-\[\d+px\]/.test(src), `${name} : taille en px`);
    assert.ok(!/#[0-9a-fA-F]{3,6}\b/.test(src.replace(/id="[^"]*"/g, '')), `${name} : couleur en dur`);
    assert.ok(!/style="[^"]*(color|background)/.test(src), `${name} : style en ligne`);
  }
});

function walk(o, prefix, out) {
  for (const [k, v] of Object.entries(o)) {
    if (v && typeof v === 'object') walk(v, `${prefix}.${k}`, out);
    else out.push([`${prefix}.${k}`, v]);
  }
  return out;
}

test('labCatalogue : FR et EN ont exactement les memes cles, textes en ASCII sans signes typographiques', () => {
  const fr = walk(msgs.fr.labCatalogue, 'labCatalogue', []);
  const en = walk(msgs.en.labCatalogue, 'labCatalogue', []);
  assert.deepEqual(fr.map(([k]) => k), en.map(([k]) => k));
  assert.ok(fr.length > 120);
  for (const [k, v] of [...fr, ...en]) {
    assert.equal(typeof v, 'string', k);
    assert.ok(v.trim().length > 0, k);
    assert.ok(!/[—–…·→←↑↓]/.test(v), `${k} : signe typographique`);
  }
});

test('toutes les cles labCatalogue.* et lab.* citees existent en FR et EN', () => {
  const used = new Set();
  const src = Object.values(all).join('\n');
  for (const m of src.matchAll(/['"`]((?:labCatalogue|lab\.config)\.[a-zA-Z_.]+)['"`]/g)) used.add(m[1]);
  for (const m of src.matchAll(/t\('(labCatalogue\.[a-zA-Z_.]+) ?'/g)) used.add(m[1]);
  assert.ok(used.size > 40);
  for (const k of used) {
    if (k.endsWith('.') || k.endsWith('_')) continue; // prefixe de cle dynamique, verifiee plus bas
    for (const loc of ['fr', 'en']) assert.equal(typeof pick(msgs[loc], k), 'string', `${loc}:${k}`);
  }
  // cles construites dynamiquement
  for (const loc of ['fr', 'en']) {
    for (const f of ['table', 'three_columns', 'label_value', 'narrative', 'boxed']) {
      assert.equal(typeof msgs[loc].labCatalogue.families[f], 'string');
      assert.equal(typeof msgs[loc].labCatalogue.families[`${f}_desc`], 'string');
    }
    for (const k of ['numeric', 'text', 'choice', 'pos_neg']) assert.equal(typeof msgs[loc].labCatalogue.kinds[k], 'string');
    for (const u of ['jours', 'semaines', 'mois', 'ans']) assert.equal(typeof msgs[loc].labCatalogue.units[u], 'string');
    for (const s of ['M', 'F', 'X']) assert.equal(typeof msgs[loc].labCatalogue.range[`sex_${s}`], 'string');
    for (const k of ['in_use', 'duplicate_code', 'duplicate_range', 'invalid_order', 'invalid_choices']) assert.equal(typeof msgs[loc].serverErrors[k], 'string');
  }
});

test('les cles d\'erreur de labCatalogue.js existent', () => {
  const util = read('../src/utils/labCatalogue.js');
  const keys = [...util.matchAll(/E\('([a-z_]+)'\)/g)].map((m) => m[1]);
  assert.ok(keys.length > 15);
  for (const k of keys) for (const loc of ['fr', 'en']) assert.equal(typeof msgs[loc].labCatalogue.errors[k], 'string', `${loc}:${k}`);
});

test('banc : NB 1000 et Conclusion 5000 avec compteur, envoi de conclusion', () => {
  const bench = read('../src/views/modules/labo/LabTechnician.vue');
  assert.ok(bench.includes('const NOTE_MAX = 1000;') && bench.includes('const CONCLUSION_MAX = 5000;'));
  assert.ok(bench.includes(':maxlength="CONCLUSION_MAX"') && bench.includes(':maxlength="NOTE_MAX"'));
  assert.ok(bench.includes('id="lab-tech-conclusion"') && bench.includes('id="lab-tech-note"'));
  assert.ok(bench.includes('lab-tech-conclusion-count') && bench.includes('lab-tech-note-count'));
  assert.ok(bench.includes('conclusion: conclusionToSend()'));
  assert.ok(bench.includes('note: formGlobalNote.value, conclusion: conclusionToSend()'));
  assert.ok(bench.includes('formConclusion.value = data.conclusion'));
  const modal = read('../src/components/lab/ResultDetailModal.vue');
  assert.ok(modal.includes('result.conclusion'));
});

test('conclusion : quatre couches (schema local, ecriture locale, connecteur, passerelle)', () => {
  const schema = read('../src/powersync-client/AppSchema.js');
  const lr = schema.slice(schema.indexOf('const lab_results = new Table('), schema.indexOf('const lab_result_details'));
  assert.ok(/conclusion: column\.text/.test(lr), 'AppSchema.lab_results.conclusion');
  const gw = read('../src/services/labGateway.js');
  assert.ok(gw.includes("UPDATE lab_results SET conclusion = ? WHERE id = ?"), 'ecriture locale');
  assert.ok(gw.includes('lr.conclusion') && gw.includes('conclusion: result?.conclusion ?? null'), 'lecture locale');
  const conn = read('../src/powersync-client/DossierConnector.js');
  const patch = conn.slice(conn.indexOf("case 'lab_results:PATCH'"), conn.indexOf("case 'paiement_echelonne:PUT'"));
  assert.ok(patch.includes('SELECT status, note, conclusion, patient_uuid FROM lab_results WHERE id = ?'), 'relit la ligne locale complete');
  assert.ok(patch.includes('conclusion: current.conclusion ?? null'), 'envoie la conclusion lue en local');
  assert.ok(!/conclusion:\s*op\.opData/.test(patch), 'ne fait jamais confiance a op.opData');
});

test('catalogue hors ligne : seuls les examens et parametres actifs', () => {
  const ref = read('../src/powersync-client/referenceData.js');
  assert.ok(ref.includes('FROM exam_catalog WHERE COALESCE(is_active, 1) = 1'));
  const store = read('../src/stores/labStore.js');
  assert.ok(store.includes('FROM reference_lab_params WHERE examen_id = ? AND COALESCE(is_active, 1) = 1'));
  const sync = read('../../powersync/sync-config.yaml');
  const exam = sync.slice(sync.indexOf('reference_exam_catalog:'), sync.indexOf('reference_staff_discount_rules:'));
  assert.ok(exam.includes('WHERE exam_catalog.is_active = true'));
  const params = sync.slice(sync.indexOf('reference_lab_params:'), sync.indexOf('reference_lab_ranges:'));
  assert.ok(params.includes('WHERE reference_lab_params.is_active = true'));
});

// ---------------------------------------------------------------- C5 : textes imprimes, sous-titres, notes fixes
const notesEditor = read('../src/components/labo/CatalogueNotesEditor.vue');

test('C5 : l\'examen porte l\'editeur de notes fixes (liste ordonnee, position, style, texte), verrouille hors edition', () => {
  assert.ok(form.includes('<CatalogueNotesEditor v-model="form.fixed_notes" :disabled="!editable"'));
  assert.ok(form.includes('notesFromExam(e)') && form.includes('fixed_notes: []'));
  for (const frag of ['v-for="p in NOTE_POSITIONS"', 'v-for="s in NOTE_STYLES"', '<textarea', 'maxlength', 'move(i, -1)', 'move(i, 1)', 'remove(i)', '@click="add"']) {
    assert.ok(notesEditor.includes(frag), frag);
  }
  assert.ok(notesEditor.includes(':disabled="notes.length >= MAX_NOTES"'));
  assert.ok(notesEditor.includes('v-if="!disabled"'));
  // le texte est rendu par interpolation (jamais v-html) : aucun HTML interprete
  for (const [name, src] of Object.entries({ notesEditor, form, table, ranges })) assert.ok(!/v-html/.test(src), `${name} v-html`);
});

test('C5 : sous-titre, texte de norme et texte de plage editables, avec limites', () => {
  assert.ok(table.includes('v-model="f.group_label"') && table.includes('maxlength="80"'));
  assert.ok(table.includes('v-model="f.norm_text"') && table.includes('maxlength="200"'));
  assert.ok(ranges.includes('v-model="f.display_text"') && ranges.includes('maxlength="60"'));
  assert.ok(table.includes("group_label: p.group_label || ''") && table.includes("norm_text: p.norm_text || ''"));
  assert.ok(ranges.includes("display_text: r.display_text || ''") && ranges.includes('display_text: f.display_text'));
});

test('C5 : cibles >= 44 px, texte >= 14 px, jetons seulement dans les nouveaux champs', () => {
  assert.ok(notesEditor.includes('min-h-11') && !/text-xs/.test(notesEditor));
  assert.ok(!/#[0-9a-fA-F]{3,6}\b/.test(notesEditor), 'couleur en dur');
  assert.ok(!/text-\[(\d|1[0-3])px\]/.test(notesEditor));
});

test('C5 : cles i18n FR et EN identiques, ASCII sans caracteres typographiques interdits', () => {
  const keysOf = (o, pre = '') => Object.entries(o).flatMap(([k, v]) => (v && typeof v === 'object' ? keysOf(v, pre + k + '.') : [pre + k]));
  const fr = keysOf(msgs.fr.labCatalogue).sort();
  const en = keysOf(msgs.en.labCatalogue).sort();
  assert.deepEqual(fr, en);
  for (const k of ['notes.title', 'notes.help', 'notes.add', 'notes.remove', 'notes.item', 'notes.count', 'notes.text_counter',
    'positions.before_body', 'positions.after_body', 'positions.after_conclusion', 'styles.normal', 'styles.bold', 'styles.italic',
    'param.group_label', 'param.norm_text', 'range.display_text', 'errors.note_text_required', 'errors.notes_too_many',
    'errors.note_position_invalid', 'errors.note_style_invalid', 'errors.control_chars']) {
    for (const lang of ['fr', 'en']) {
      const v = pick(msgs[lang].labCatalogue, k);
      assert.ok(typeof v === 'string' && v.length > 0, `${lang}.${k}`);
      assert.ok(!/[\u2013\u2014\u2026\u00b7]/.test(v), `${lang}.${k} caractere typographique`);
    }
  }
});
