import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labo/LabConfig.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : configuration du laboratoire (liste des examens du catalogue) ---
// Corrige apres la refonte (2026-10-23) : openModal() n'etait definie nulle part et labStore.deleteExam n'existait pas,
// donc "Nouvel examen" et "Supprimer" ne faisaient rien. La creation reutilise ExamFormModal (configuration systeme),
// la suppression passe par configStore.deleteExamen apres une confirmation.
check('LabConfig', view, [
    "const isAdmin = computed(() => {", "return authStore.hasRole(['admin', 'manager']);", 'labStore.fetchExams();', 'onMounted(() => {',
    'v-if="isAdmin"', '@click="openModal()"', ':rows="labStore.exams"', 'row-key="id"', 'exam.code', 'exam.nom', 'exam.categorie', '@click="removeExam(exam)"',
    // création et suppression réellement branchées
    'const openModal = (exam = null) => {', 'selectedExam.value = exam;', 'showExamModal.value = true;', '<ExamFormModal v-if="showExamModal"', ':examen="selectedExam"', '@saved="onExamSaved"',
    "import ExamFormModal from '@/components/config/ExamFormModal.vue';", 'await labStore.fetchExams();',
    "if (!window.confirm(t('labScreens.delete_exam_confirm', { name: exam.nom }))) return;", 'await configStore.deleteExamen(exam.id);',
    "t('lab.config.title')", "t('lab.config.subtitle')", "t('lab.config.new_exam')", "t('lab.config.col_code')", "t('lab.config.col_name')", "t('lab.config.col_category')",
]);

test('toutes les clés lab.* et labScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:lab|labScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 6);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('LabConfig : composants ui/, tableau responsive à lignes alternées, catégorie en badge, actions en boutons avec texte', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'ResponsiveTable', 'StatusBadge', 'AppButton']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.match(view, /\bstriped\b/);
    const t = templateOf(view);
    assert.doesNotMatch(t, /<table/);
    assert.match(t, /variant="danger"/);
    assert.match(t, /<AppButton[^>]*@click="removeExam\(exam\)"/s);
    assert.match(t, /<AppButton[^>]*@click="openModal\(\)"/s);
});

test('LabConfig : la page défile dans le cadre du labo (zone de défilement propre)', () => {
    assert.match(templateOf(view), /overflow-y-auto/);
});

test('LabConfig : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(view, /@apply|<style/);
    assert.doesNotMatch(templateOf(view).replace(/<!--.*?-->/gs, ''), /[—–…·•‹›→✓]|\p{Extended_Pictographic}/u);
});

test('clés labScreens (configuration) en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        for (const k of ['delete_exam', 'delete_exam_confirm']) {
            const v = msgs[locale].labScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.labScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/);
        }
    }
    assert.match(msgs.fr.labScreens.delete_exam_confirm, /\{name\}/);
    assert.match(msgs.en.labScreens.delete_exam_confirm, /\{name\}/);
});

test('LabConfig : aucune fonction appelée par le gabarit n\'est laissée indéfinie', () => {
    const t = templateOf(view);
    const called = [...t.matchAll(/@click="([a-zA-Z]+)\(/g)].map((m) => m[1]);
    for (const fn of new Set(called)) {
        assert.match(view.slice(view.indexOf('<script')), new RegExp(`const ${fn}\\b|function ${fn}\\b`), `${fn}() appelée par le gabarit mais non définie`);
    }
    assert.doesNotMatch(t, /labStore\.deleteExam\b/);
});
