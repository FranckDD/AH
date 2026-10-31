import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/modules/labo/LabReception.vue', import.meta.url), 'utf8');
const template = view.slice(0, view.indexOf('<script'));
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

// --- Contrat : prescripteur libre, patient externe seulement ---
test('le champ libre n est affiche que pour un patient externe, la liste des medecins reste pour l interne', () => {
    const ext = template.indexOf(`v-if="mode === 'external'" class="grid max-w-2xl`);
    const doctors = template.indexOf('<div v-else class="max-w-md">');
    assert.ok(ext > -1 && doctors > ext, 'bloc externe puis bloc medecins en v-else');
    assert.ok(template.includes('id="lab-reception-doctor"'));
    assert.ok(template.indexOf('lab-ext-prescriber-title') < doctors);
    assert.ok(template.indexOf('lab-ext-prescriber-name') < doctors);
    assert.ok(template.indexOf('lab-reception-doctor') > doctors);
});

test('les titres autorises sont exactement la liste fermee', () => {
    assert.ok(view.includes("['Dr', 'I.D.E.', 'Fr', 'Br', 'M.', 'Mme', 'Volontaire', 'Autre']"));
});

test('titre obligatoire, nom obligatoire sauf Volontaire', () => {
    assert.ok(view.includes("!!extPrescriber.value.title && (extPrescriber.value.title === 'Volontaire' || !!extPrescriber.value.name.trim())"));
    assert.ok(view.includes("mode.value === 'external') return hasExam && hasPatient && hasExtPrescriber"));
    assert.match(template, /lab-ext-prescriber-title"[^>]*required|:label="\$t\('labScreens.ext_prescriber_title'\)" required/);
});

test('l envoi interne est inchange et l externe ne porte pas de medecin interne', () => {
    assert.ok(view.includes('prescribed_by_id: selectedDoctorId.value,'));
    assert.ok(view.includes('const hasDoctor = !!selectedDoctorId.value;'));
    // le menu des medecins est cache en externe et remis a zero au changement de mode : l'identifiant reste nul
    assert.ok(view.includes('selectedDoctorId.value = null;'));
    assert.ok(view.includes('prescriber_title: extPrescriber.value.title'));
    assert.ok(view.includes('prescriber_name: extPrescriber.value.name'));
    // les champs ne sont ajoutes que dans le bloc du patient externe
    const ext = view.indexOf('payload.external_patient_info = {');
    assert.ok(view.indexOf('prescriber_title:') > ext);
    assert.ok(view.indexOf('payload.patient_id = selectedPatient.value.id;') < ext);
});

test('memoire des noms : suggestions serveur, saisie libre conservee hors ligne', () => {
    assert.ok(view.includes("api.get('/labo/external-prescribers'"));
    assert.ok(view.includes('list="lab-ext-prescriber-list"'));
    assert.ok(view.includes('<datalist id="lab-ext-prescriber-list">'));
    assert.ok(view.includes('prescriberSuggestions.value = [];'));
});

test('le prescripteur est remis a zero avec le patient', () => {
    assert.ok(view.includes("extPrescriber.value = { title: '', name: '' };"));
});

test('i18n FR et EN : memes cles, ASCII dans les textes ajoutes', () => {
    const keys = ['ext_prescriber_title', 'ext_prescriber_choose_title', 'ext_prescriber_name', 'ext_prescriber_name_help', 'ext_prescriber_name_optional'];
    for (const k of keys) {
        const fr = pick(msgs.fr, `labScreens.${k}`);
        const en = pick(msgs.en, `labScreens.${k}`);
        assert.ok(fr && en, `${k} manque en FR ou EN`);
        assert.ok(!/[\u2013\u2014\u2026\u00b7\u2192]/.test(fr + en), `${k} contient un caractere interdit`);
        assert.ok(!/[\u2013\u2014\u2026\u00b7\u2192]/.test(en));
    }
});

test('aucune classe de taille inferieure a 14 px ni couleur en dur dans le bloc ajoute', () => {
    const block = template.slice(template.indexOf('data-testid="external-prescriber"'), template.indexOf('<div v-else class="max-w-md">'));
    assert.ok(!/text-\[(\d|1[0-3])px\]|text-xs|#[0-9a-fA-F]{3,6}/.test(block));
    assert.ok(block.includes(':class="fieldClass"'));
});
