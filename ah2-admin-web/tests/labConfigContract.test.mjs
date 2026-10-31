import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const files = {
    view: read('../src/views/modules/labo/LabConfig.vue'),
    form: read('../src/components/labo/CatalogueExamForm.vue'),
    table: read('../src/components/labo/CatalogueParamTable.vue'),
    ranges: read('../src/components/labo/CatalogueRangeEditor.vue'),
};
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

// L'ecran de configuration du laboratoire est desormais l'ecran de gestion du catalogue (tache C4) ; ses regles
// fonctionnelles sont dans labCatalogueContract.test.mjs. Ici : les regles de la refonte visuelle.
test('LabConfig : composants ui/, route et titres conserves', () => {
    const v = files.view;
    assert.match(v, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'AppButton', 'FullScreenPanel', 'StatusBadge']) assert.match(v, new RegExp(`\\b${c}\\b`), c);
    assert.match(v, /t\('lab\.config\.title'\)/);
    assert.match(v, /t\('lab\.config\.subtitle'\)/);
    assert.match(v, /t\('lab\.config\.new_exam'\)/);
    assert.doesNotMatch(templateOf(v), /<table/);
});

test('LabConfig : la page defile dans le cadre du labo', () => {
    assert.match(templateOf(files.view), /overflow-y-auto/);
});

test('catalogue : jetons du theme, cibles >= 44 px, aucun emoji ni caractere typographique interdit', () => {
    for (const [name, src] of Object.entries(files)) {
        assert.doesNotMatch(src, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/, name);
        assert.doesNotMatch(src, /text-xs|text-\[(?:[0-9]|1[0-3])px\]/, name);
        assert.doesNotMatch(src, /@apply|<style/, name);
        assert.doesNotMatch(templateOf(src).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u, name);
        // chaque champ de saisie porte la classe a 44 px minimum
        for (const m of templateOf(src).matchAll(/<(input|select|textarea)\b[^>]*>/g)) {
            if (/type="checkbox"/.test(m[0])) continue;
            assert.match(m[0], /fieldClass/, `${name} : ${m[0].slice(0, 60)}`);
        }
    }
    for (const src of [files.view, files.form, files.table, files.ranges]) {
        const field = src.match(/const fieldClass = '([^']+)'/);
        assert.ok(field && field[1].includes('min-h-11'), 'fieldClass 44 px');
    }
});
