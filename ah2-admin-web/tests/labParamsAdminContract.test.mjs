import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const pick = (o, path) => path.split('.').reduce((x, k) => x?.[k], o);

const panelPath = '../src/components/config/ExamParamsPanel.vue';
test('le panneau des parametres existe et appelle les routes du catalogue', () => {
    assert.ok(existsSync(new URL(panelPath, import.meta.url)));
    const panel = read(panelPath);
    for (const n of ['labStore.addParam', 'labStore.updateParam', 'labStore.deleteParam', 'labStore.addRange', 'labStore.deleteRange', 'describeServerError']) {
        assert.ok(panel.includes(n), n);
    }
});
test('gateway et store exposent modification et plages', () => {
    const gw = read('../src/services/labGateway.js');
    assert.ok(gw.includes('updateExamParam') && gw.includes('addRange') && gw.includes('deleteRange'));
    assert.ok(gw.includes('`/labo/params/${paramId}`'));
});
test('catalogue labo : le nouvel ecran remplace le panneau (voir labCatalogueContract)', () => {
    const v = read('../src/views/modules/labo/LabConfig.vue');
    assert.ok(v.includes('CatalogueParamTable'));
    assert.ok(!v.includes('ExamParamsPanel'));
});
test('libelles FR et EN identiques', () => {
    const keys = ['lab.config.col_price', 'lab.config.edit_exam', 'lab.config.params_button', 'labParams.title', 'labParams.add', 'labParams.name', 'labParams.unit',
        'labParams.ranges', 'labParams.sex_m', 'labParams.sex_f', 'labParams.sex_x', 'labParams.age_min', 'labParams.age_max', 'labParams.value_min', 'labParams.value_max',
        'labParams.add_range', 'labParams.confirm_delete', 'labParams.empty', 'labParams.save', 'labParams.close', 'labParams.edit', 'labParams.type_numeric', 'labParams.type_text'];
    for (const l of ['fr', 'en']) for (const k of keys) {
        const val = pick(msgs[l], k);
        assert.ok(typeof val === 'string' && val.length > 0, `${l}.${k}`);
        assert.ok(!/[\u2013\u2014\u2026\u00b7]/.test(val), `${l}.${k} caractere interdit`);
    }
});

test('ordre des parametres : boutons monter/descendre, route et libelles FR/EN', () => {
    const panel = read(panelPath);
    assert.ok(panel.includes('labStore.reorderParams'), 'panneau appelle reorderParams');
    assert.ok(panel.includes('labParams.move_up') && panel.includes('labParams.move_down'));
    assert.ok(/aria-label="t\('labParams\.move_up'|:aria-label="t\('labParams\.move_up'/.test(panel), 'boutons nommes');
    assert.ok(panel.includes('canReorder'), 'reserve a l admin');
    assert.ok(!panel.includes("pas de colonne d'ordre"), 'ancien commentaire retire');
    assert.ok(read('../src/services/labGateway.js').includes('`/labo/exams/${examId}/params/order`'));
    assert.ok(read('../src/stores/labStore.js').includes('reorderParams'));
    for (const l of ['fr', 'en']) for (const k of ['labParams.move_up', 'labParams.move_down']) {
        const val = pick(msgs[l], k);
        assert.ok(typeof val === 'string' && val.includes('{name}'), `${l}.${k}`);
        assert.ok(!/[\u2013\u2014\u2026\u00b7]/.test(val));
    }
});

test('ordre des parametres : synchro hors ligne et banc suivent la colonne ordre', () => {
    assert.ok(/ordre:\s*column\.integer/.test(read('../src/powersync-client/AppSchema.js')));
    assert.ok(read('../../powersync/sync-config.yaml').includes('reference_lab_params.ordre'));
    const gw = read('../src/services/labGateway.js');
    assert.ok(gw.includes('ORDER BY rp.ordre'), 'detail hors ligne trie par ordre');
});
