import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

const root = new URL('../src/components/layout/', import.meta.url);
const exists = (f) => existsSync(new URL(f, root));
const read = (f) => (exists(f) ? readFileSync(new URL(f, root), 'utf8') : '');

const shell = read('AppShell.vue');
const medical = read('MedicalLayout.vue');

// --- Le cadre partagé porte tout ce que portait le cadre médical ---
const SHELL_NEEDLES = [
    'changeLanguage', "localStorage.setItem('lang'", '<NotificationBell', 'AccountModal', 'showAccountModal',
    'await authStore.logout()', '<ConnectionStatus', 'resolveAssetUrl', 'fetchStructureInfo',
    'toggleSidebar', 'Bars3CenterLeftIcon', 'medicalShell.collapseMenu', 'medicalShell.expandMenu',
    'medicalShell.openMenu', 'medicalShell.closeMenu', 'medicalShell.mainNav',
    'isDrawerOpen', "e.key === 'Escape'", 'displayName', 'roleLine', 'todayLabel',
    'onlyWhenQuarantine', 'useSyncQuarantineCount', 'quarantineCount', 'app-refonte',
    'authStore.hasRole(bellRoles)', 'brandFallback', 'sidebarId', 'menuGroups',
    ':aria-current="isActive(item', 'item.exact',
    '<router-view :key="route.fullPath" />', 'common.welcome', 'common.my_account', 'common.logout',
];

for (const needle of SHELL_NEEDLES) {
    test(`AppShell : « ${needle} » est présent`, () => {
        assert.ok(shell.length > 0, 'AppShell.vue manquant');
        assert.ok(shell.includes(needle), `« ${needle} » absent de AppShell.vue`);
    });
}

test('AppShell : props du cadre', () => {
    for (const p of ['menuGroups', 'bellRoles', 'brandFallback', 'sidebarId']) {
        assert.match(shell, new RegExp(`${p}:\\s*\\{`), `prop ${p}`);
    }
});

test('AppShell : aucune couleur brute ni hexadécimal, aucun caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(shell, /#[0-9a-fA-F]{6}\b/);
    assert.doesNotMatch(shell, /\b(emerald|indigo|slate|gray|red|green|blue|teal)-\d{2,3}\b/);
    assert.doesNotMatch(shell.slice(0, shell.indexOf('<script')), /[—–…·]/);
});

test('AppShell : un groupe sans entrée visible n’est pas affiché et la quarantaine masque l’entrée tant qu’elle est vide', () => {
    assert.match(shell, /!item\.onlyWhenQuarantine \|\| quarantineCount\.value > 0/);
    assert.match(shell, /\.filter\(\(g\) => g\.items\.length\)/);
});

test('AppShell : page active exacte pour une entrée « exact », sinon par inclusion (comportement du cadre médical)', () => {
    assert.match(shell, /route\.path\.includes\(item\.path\)/);
});

// --- Le cadre médical n'est plus qu'une configuration ---
const MEDICAL_ENTRIES = [
    ['/medical/appointments', 'appointments.title', 'activity'],
    ['/medical/prescriptions', 'prescriptions.title', 'medical'],
    ['/medical/medical-records', 'medicalRecords.title', 'medical'],
    ['/medical/patients', 'patients.title', 'activity'],
    ['/medical/doctors', 'doctorKpi.title', 'followup'],
    ['/medical/hospitalizations', 'hospitalization.title', 'activity'],
    ['/medical/nurse-shifts', 'nurseShift.title', 'activity'],
    ['/medical/lab-results', 'lab.nav.medical_results', 'medical'],
    ['/medical/sync-failures', 'secretariat.nav.sync_failures', 'followup'],
];

test('MedicalLayout : enveloppe de configuration autour d’AppShell, sans gabarit de menu', () => {
    assert.match(medical, /import AppShell from '@\/components\/layout\/AppShell\.vue'/);
    assert.match(medical, /<AppShell/);
    assert.doesNotMatch(medical, /<aside/);
    assert.doesNotMatch(medical, /<header/);
});

for (const [path, labelKey, group] of MEDICAL_ENTRIES) {
    test(`MedicalLayout : ${path} garde son libellé ${labelKey} dans le groupe ${group}`, () => {
        const i = medical.indexOf(`'${path}'`);
        assert.ok(i > 0, `${path} absent`);
        const entry = medical.slice(i, i + 200);
        assert.ok(entry.includes(`'${labelKey}'`), `${labelKey} absent près de ${path}`);
        const groupStart = medical.lastIndexOf(`key: '${group}'`, i);
        assert.ok(groupStart > 0, `groupe ${group} absent avant ${path}`);
    });
}

test('MedicalLayout : intertitres, cloche réservée au médecin et à l’infirmière, entrée de quarantaine conditionnelle', () => {
    for (const key of ['activity', 'medical', 'followup']) {
        assert.ok(medical.includes(`medicalShell.sections.${key}`), `intertitre ${key}`);
    }
    assert.match(medical, /bell-roles="\['medecin', 'nurse'\]"/);
    assert.match(medical, /onlyWhenQuarantine: true/);
});
