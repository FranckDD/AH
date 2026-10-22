import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
    resolveConnectionState,
    connectionTone,
    connectionLabelKey,
} from '../src/utils/connectionStatus.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const cases = [
    ['connecté sans file', { connected: true }, { state: 'online', pending: 0 }],
    ['connecté, envoi en cours', { connected: true, uploading: true, pending: 2 }, { state: 'syncing', pending: 2 }],
    ['connecté, file non vide', { connected: true, pending: 3 }, { state: 'pending', pending: 3 }],
    ['non connecté', { connected: false }, { state: 'offline', pending: 0 }],
    ['non connecté avec saisies en attente', { connected: false, pending: 4 }, { state: 'offline', pending: 4 }],
    ['non connecté mais en reconnexion : reste hors ligne', { connected: false, connecting: true }, { state: 'offline', pending: 0 }],
    ['erreur', { connected: true, hasError: true, pending: 1 }, { state: 'error', pending: 1 }],
    ['erreur prioritaire sur hors ligne', { connected: false, hasError: true }, { state: 'error', pending: 0 }],
    ['entrées vides', {}, { state: 'offline', pending: 0 }],
    ['undefined', undefined, { state: 'offline', pending: 0 }],
    ['null', null, { state: 'offline', pending: 0 }],
    ['valeurs nulles', { connected: null, uploading: null, pending: null }, { state: 'offline', pending: 0 }],
    ['pending négatif ou invalide ramené à 0', { connected: true, pending: -5 }, { state: 'online', pending: 0 }],
    ['pending non numérique', { connected: true, pending: 'abc' }, { state: 'online', pending: 0 }],
    ['envoi en cours prioritaire sur file', { connected: true, uploading: true }, { state: 'syncing', pending: 0 }],
];

for (const [name, input, expected] of cases) {
    test(`resolveConnectionState : ${name}`, () => {
        assert.deepEqual(resolveConnectionState(input), expected);
    });
}

test('tonalités : hors ligne = orange, erreur = rouge, connecté = vert, synchro = bleu', () => {
    assert.equal(connectionTone('online'), 'success');
    assert.equal(connectionTone('syncing'), 'info');
    assert.equal(connectionTone('pending'), 'warning');
    assert.equal(connectionTone('offline'), 'warning');
    assert.equal(connectionTone('error'), 'danger');
    assert.equal(connectionTone('???'), 'neutral');
});

test('clés de libellé par état', () => {
    for (const s of ['online', 'syncing', 'pending', 'offline', 'error']) {
        assert.equal(connectionLabelKey(s), `medicalShell.connection.${s}`);
    }
    assert.equal(connectionLabelKey('???'), 'medicalShell.connection.offline');
});

test('pluriel du libellé « à envoyer » (1 / n) en FR et EN', () => {
    const { t } = i18n.global;
    const key = 'medicalShell.connection.pending';
    assert.match(t(key, { n: 1 }, { locale: 'fr', plural: 1 }), /^1 élément à envoyer$/);
    assert.match(t(key, { n: 3 }, { locale: 'fr', plural: 3 }), /^3 éléments à envoyer$/);
    assert.match(t(key, { n: 1 }, { locale: 'en', plural: 1 }), /^1 item to send$/);
    assert.match(t(key, { n: 3 }, { locale: 'en', plural: 3 }), /^3 items to send$/);
});

const SHELL_KEYS = [
    'sections.activity', 'sections.medical', 'sections.followup',
    'openMenu', 'closeMenu', 'collapseMenu', 'expandMenu', 'mainNav', 'userMenu',
    'connection.label', 'connection.online', 'connection.syncing', 'connection.pending',
    'connection.offline', 'connection.offlineDetail', 'connection.error',
];

test('clés medicalShell.* présentes en FR et EN', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        for (const k of SHELL_KEYS) {
            const v = k.split('.').reduce((o, p) => o?.[p], msgs[locale].medicalShell);
            assert.equal(typeof v, 'string', `${locale}.medicalShell.${k} manquante`);
            assert.ok(v.length > 0);
        }
    }
});

// --- Contrat du gabarit : aucune entrée de menu, aucune action de la barre ne doit disparaître ---
// Le cadre médical = sa configuration (MedicalLayout.vue) + le cadre partagé (AppShell.vue) : le contrat porte sur les deux.
const layout = ['MedicalLayout.vue', 'AppShell.vue']
    .map((f) => readFileSync(new URL(`../src/components/layout/${f}`, import.meta.url), 'utf8'))
    .join('\n');

const MENU = [
    ['/medical/appointments', 'appointments.title'],
    ['/medical/prescriptions', 'prescriptions.title'],
    ['/medical/medical-records', 'medicalRecords.title'],
    ['/medical/patients', 'patients.title'],
    ['/medical/doctors', 'doctorKpi.title'],
    ['/medical/hospitalizations', 'hospitalization.title'],
    ['/medical/nurse-shifts', 'nurseShift.title'],
    ['/medical/lab-results', 'lab.nav.medical_results'],
    ['/medical/sync-failures', 'secretariat.nav.sync_failures'],
];

for (const [path, labelKey] of MENU) {
    test(`menu : ${path} conserve son chemin et son libellé`, () => {
        assert.ok(layout.includes(`'${path}'`), `${path} absent`);
        assert.ok(layout.includes(`'${labelKey}'`), `${labelKey} absent`);
    });
}

test('menu : l’entrée des échecs de synchronisation reste conditionnée à la quarantaine', () => {
    assert.match(layout, /onlyWhenQuarantine/);
    assert.match(layout, /useSyncQuarantineCount/);
});

test('l’en-tête affiche le nom complet avec repli sur l’identifiant', () => {
    assert.match(layout, /authStore\.user\?\.full_name/);
    assert.match(layout, /authStore\.user\?\.username/);
    assert.match(layout, /\{\{ displayName \}\}/);
});

test('le bouton de réduction du menu (icônes seules) est conservé', () => {
    for (const needle of ['isSidebarOpen', 'toggleSidebar', 'medicalShell.collapseMenu', 'medicalShell.expandMenu', 'Bars3CenterLeftIcon']) {
        assert.ok(layout.includes(needle), `« ${needle} » absent du gabarit`);
    }
});

test('barre du haut : langue, cloche, compte, déconnexion et connexion conservés', () => {
    for (const needle of [
        'changeLanguage', "localStorage.setItem('lang'",
        "bell-roles=\"['medecin', 'nurse']\"", 'authStore.hasRole(bellRoles)', '<NotificationBell',
        'AccountModal', 'showAccountModal',
        'handleLogout', 'await authStore.logout()',
        '<ConnectionStatus', 'resolveAssetUrl', 'fetchStructureInfo', "common.welcome",
    ]) {
        assert.ok(layout.includes(needle), `« ${needle} » absent du gabarit`);
    }
});

test('le gabarit pose le conteneur .app-refonte et n’utilise plus de couleurs de marque en dur', () => {
    assert.match(layout, /app-refonte/);
    assert.doesNotMatch(layout, /#[0-9a-fA-F]{6}\b/);
    assert.doesNotMatch(layout, /\b(indigo|emerald|slate)-\d{2,3}\b/);
});
