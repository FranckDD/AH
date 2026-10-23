import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const card = readFileSync(new URL('../src/components/lab/LabPassageCard.vue', import.meta.url), 'utf8');
const bench = readFileSync(new URL('../src/views/modules/labo/LabTechnician.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(src.indexOf('<template>'));

// --- Carte de passage : le patient une seule fois, tous ses examens en pastilles ---
test('carte : patient une seule fois, une pastille par examen, ouverture par result_id', () => {
    for (const needle of ['v-for="e in passage.exams"', ':key="e.result_id"', "$emit('open', e.result_id)", 'passage.patient_name', 'passage.patient_sexe', 'passage.patient_age',
        'passage.is_external', "defineEmits(['open'])", 'activeId === e.result_id', "e.examen_nom || t('lab.technician.exam')"]) {
        assert.ok(card.includes(needle), needle);
    }
});

test('carte : chaque examen dit son état par une icône ET un mot, et la progression n apparaît qu avec plusieurs examens', () => {
    const t = templateOf(card);
    assert.match(t, /<component :is="ICONS\[meta\(e\.status\)\.icon\]"/);
    assert.match(t, /t\(meta\(e\.status\)\.labelKey\)/);
    assert.match(t, /v-if="passage\.exams\.length > 1"/);
    assert.match(t, /role="progressbar"/);
});

test('carte : pastilles en vrais boutons de 44 px avec état, jamais des div cliquables', () => {
    const t = templateOf(card);
    assert.match(t, /<button type="button" :aria-pressed/);
    assert.match(t, /min-h-11/);
    assert.doesNotMatch(t, /<div[^>]*@click/s);
});

test('carte : jetons du thème, texte >= 13 px, aucun caractère typographique interdit', () => {
    assert.doesNotMatch(card, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(card, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(card), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
});

test('la paillasse utilise la carte et regroupe par passage', () => {
    assert.match(bench, /import LabPassageCard from '@\/components\/lab\/LabPassageCard\.vue'/);
    assert.match(bench, /groupPaillasse\(labStore\.paillasseList\)/);
});

test('toutes les clés citées par la carte existent en FR et EN', () => {
    const used = new Set();
    for (const m of card.matchAll(/['"`(]((?:lab|labScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    for (const k of ['lab.status.pending', 'lab.status.completed', 'lab.status.validated', 'labScreens.status_in_progress', 'labScreens.passage_progress', 'labScreens.passage_exams', 'labScreens.exams_count', 'labScreens.history_passages']) used.add(k);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
            assert.doesNotMatch(String(v), /[—–…·]/, `${locale}.${k}`);
        }
    }
});
