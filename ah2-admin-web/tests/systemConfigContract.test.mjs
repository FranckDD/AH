import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/SystemConfig.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : identité de la structure, logos, jeton d'impression, examens, prières, système ---
check('SystemConfig', view, [
    // chargement
    'await configStore.fetchStructureInfo();', 'await configStore.fetchTicketPrintToken();', 'configStore.fetchExamens();', 'configStore.fetchPrayerBooks();',
    "watch(() => configStore.structureInfo, (info) => {", 'formStructure.value = { ...formStructure.value, ...info }',
    // sections repliables et leur état initial
    'structure: true,', 'exams: true,', 'prayers: false,', 'general: false',
    'openSections.structure = !openSections.structure', 'openSections.exams = !openSections.exams', 'openSections.prayers = !openSections.prayers', 'openSections.general = !openSections.general',
    'v-show="openSections.structure"', 'v-show="openSections.exams"', 'v-show="openSections.prayers"', 'v-show="openSections.general"',
    // identité de la structure : onze champs, leurs types, l'envoi
    "name: '', slogan: '', phone: '', phone2: '', email: '', website: '',", "address: '', city: '', po_box: '', niu: '', rccm: ''",
    'v-model="formStructure.name"', 'v-model="formStructure.slogan"', 'v-model="formStructure.phone"', 'v-model="formStructure.phone2"', 'v-model="formStructure.email"',
    'v-model="formStructure.website"', 'v-model="formStructure.address"', 'v-model="formStructure.city"', 'v-model="formStructure.po_box"', 'v-model="formStructure.niu"', 'v-model="formStructure.rccm"',
    'type="tel"', 'type="email"', 'required', '@submit.prevent="saveStructureConfig"', ':disabled="isSaving"',
    'const formData = new FormData();', "formData.append(key, formStructure.value[key] || '');", "formData.append('logo', logoFile.value);", "formData.append('ticket_logo', ticketLogoFile.value);",
    'await configStore.saveStructureInfo(formData);', "notify('alerts.config_saved', {}, 'success');", "notify('alerts.save_failed', { detail: error.message });",
    // logos
    'type="file"', 'accept="image/*"', '@change="handleLogoUpload"', '@change="handleTicketLogoUpload"', 'URL.createObjectURL(file)',
    'previewLogo || resolveAssetUrl(configStore.structureInfo.logo_url)', 'previewTicketLogo || resolveAssetUrl(configStore.structureInfo.ticket_logo_url)', "'/placeholder-logo.png'",
    // jeton d'impression
    "configStore.ticketPrintToken || 'Non généré'", '@click="handleRegenerateToken"', "Régénérer le jeton invalidera l'ancien pour tous les services pont locaux déjà configurés. Continuer ?", 'await configStore.regenerateTicketPrintToken();',
    // examens
    'configStore.examens', 'configStore.isLoading && configStore.examens.length === 0', 'v-model="searchQuery"', 'v-for="exam in filteredExamens"'.replace('v-for="exam in filteredExamens"', ':rows="filteredExamens"'),
    'exam.nom.toLowerCase().includes(query)', 'exam.code.toLowerCase().includes(query)', 'exam.categorie.toLowerCase().includes(query)', 'exam.code', 'exam.nom', 'exam.categorie', 'formatPrice(exam.prix)',
    'openExamModal(null)', 'openExamModal(exam)', 'handleDeleteExam(exam.id)', 'if(confirm(t(\'config.delete_confirmation\'))) {', 'await configStore.deleteExamen(id);',
    'selectedExam.value = exam;', 'showExamModal.value = true;', 'showExamModal.value = false;', 'configStore.fetchExamens();',
    '<ExamFormModal', ':examen="selectedExam"', '@close="showExamModal = false"', '@saved="onExamSaved"',
    // prières
    'configStore.prayerBookTypes', 'type.type_code', 'type.label',
    // système
    "t('config.backup_server_info')", "t('config.delete_confirmation')",
    "style: 'currency', currency: 'XOF', minimumFractionDigits: 0", ".replace('XOF', 'FCFA')",
    // clés
    "t('config.title')", "t('config.subtitle')", "t('config.exams_title')", "t('config.add_exam')", "t('config.table_code')", "t('config.table_name')", "t('config.table_category')",
    "t('config.table_price')", "t('config.edit')", "t('common.delete')", "t('config.prayers_title')", "t('config.prayers_subtitle')",
    "t('config.table_type_code')", "t('config.table_label')", "t('config.general_title')", "t('config.general_subtitle')", "t('config.db_backup')",
]);

test('toutes les clés config.*, common.*, users.* et configScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:config|common|users|configScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 20);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('SystemConfig : composants ui/ (en-tête, cartes, champs, tableaux, boutons)', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'FormField', 'ResponsiveTable', 'StatusBadge', 'AppButton']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
});

test('SystemConfig : accordéons à vrai bouton (aria-expanded) et panneau associé', () => {
    const t = templateOf(view);
    assert.equal((t.match(/:aria-expanded="openSections\./g) || []).length, 4, 'quatre sections repliables');
    assert.equal((t.match(/aria-controls="cfg-/g) || []).length, 4);
});

test('SystemConfig : sélecteurs de logo nommés, tableaux responsives à lignes alternées', () => {
    const t = templateOf(view);
    assert.equal((t.match(/type="file"/g) || []).length, 2);
    assert.match(t, /configScreens\.logo_label/);
    assert.match(t, /configScreens\.ticket_logo_label/);
    assert.equal((t.match(/<ResponsiveTable/g) || []).length, 2, 'examens et types de prières');
    assert.equal((t.match(/\bstriped\b/g) || []).length, 2);
});

test('SystemConfig : jetons du thème, texte >= 13 px, aucun emoji ni caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green|sky|pink)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(view), /[—–…·•]|\p{Extended_Pictographic}/u);
});

test('clés configScreens.* en FR et EN', () => {
    const keys = ['structure_title', 'structure_help', 'logo_label', 'logo_help', 'ticket_logo_label', 'ticket_logo_help', 'token_label', 'token_regenerate', 'token_warning', 'token_confirm_check',
        'name', 'name_placeholder', 'slogan', 'slogan_placeholder', 'phone', 'phone2', 'email', 'website', 'website_placeholder', 'address', 'address_placeholder', 'city', 'po_box',
        'legal_title', 'niu', 'rccm', 'saving', 'save_structure', 'search_label', 'no_results', 'maintenance_state_on', 'maintenance_state_off'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].configScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.configScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.configScreens.${k}`);
        }
    }
});

test('jeton d’impression : rappel visible, case à cocher obligatoire avant « Régénérer », décochée après chaque régénération', () => {
    const t = templateOf(view);
    assert.match(t, /configScreens\.token_warning/);
    assert.match(t, /v-model="confirmRegenerate"/);
    assert.match(t, /:disabled="!confirmRegenerate" @click="handleRegenerateToken"/);
    assert.match(view, /const confirmRegenerate = ref\(false\);/);
    assert.match(view, /await configStore\.regenerateTicketPrintToken\(\);\s+confirmRegenerate\.value = false;/);
    // la confirmation du navigateur reste en plus (contrat d'origine)
    assert.match(view, /Régénérer le jeton invalidera l'ancien pour tous les services pont locaux déjà configurés\. Continuer \?/);
});

test('sauvegarde et maintenance : plus de faux bouton ni d interrupteur local', () => {
    const src = readFileSync(new URL('../src/views/SystemConfig.vue', import.meta.url), 'utf8');
    for (const gone of ['handleBackup', 'setTimeout(resolve, 3000)', 'toggleMaintenanceMode', 'isMaintenanceMode']) {
        assert.ok(!src.includes(gone), `${gone} ne doit plus exister`);
    }
    assert.ok(src.includes("t('config.backup_server_info')"));
});
