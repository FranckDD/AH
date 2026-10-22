import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const layout = readFileSync(new URL('../src/components/layout/SecretaireLayout.vue', import.meta.url), 'utf8');

// Chemins et libellés de l'ancien cadre : rien ne doit disparaître (baseline verte avant la refonte).
const ENTRIES = [
    ['/secretariat/', 'secretariat.nav.home'],
    ['/secretariat/patients', 'secretariat.nav.patients'],
    ['/secretariat/stock', 'secretariat.nav.stock'],
    ['/secretariat/caisse', 'secretariat.nav.caisse'],
    ['/secretariat/retrait', 'secretariat.nav.retrait'],
    ['/secretariat/consultations', 'secretariat.nav.consultations'],
    ['/secretariat/discount-history', 'secretariat.nav.discount_history'],
    ['/secretariat/sync-failures', 'secretariat.nav.sync_failures'],
];

for (const [path, labelKey] of ENTRIES) {
    test(`menu : ${path} garde son libellé ${labelKey}`, () => {
        const i = layout.indexOf(`'${path}'`);
        assert.ok(i > 0, `${path} absent`);
        assert.ok(layout.slice(i, i + 200).includes(`'${labelKey}'`), `${labelKey} absent près de ${path}`);
    });
}

test('menu : l’entrée des échecs de synchronisation reste conditionnée à la quarantaine', () => {
    const i = layout.indexOf("'/secretariat/sync-failures'");
    assert.match(layout.slice(i, i + 300), /onlyWhenQuarantine: true/);
});

test('cloche : médecin exclu, admin, promoteur et secrétaire conservés', () => {
    assert.match(layout, /bell-roles="\['admin', 'promoteur', 'secretaire'\]"/);
});

test('le jeton d’impression du ticket reste chargé au montage (sans lui toute impression échoue)', () => {
    assert.match(layout, /configStore\.fetchTicketPrintToken\(\)/);
    assert.match(layout, /onMounted\(/);
});

test('l’accueil du secrétariat n’est actif que sur sa propre page (entrée « exact »)', () => {
    const i = layout.indexOf("'/secretariat/'");
    assert.match(layout.slice(i, i + 200), /exact: true/);
});

// Nouveau : le cadre est une enveloppe autour d'AppShell, avec des intertitres.
test('SecretaireLayout : enveloppe de configuration autour d’AppShell', () => {
    assert.match(layout, /import AppShell from '@\/components\/layout\/AppShell\.vue'/);
    assert.match(layout, /<AppShell/);
    assert.doesNotMatch(layout, /<aside/);
    assert.doesNotMatch(layout, /<header/);
    assert.match(layout, /brand-fallback="AH2 Secrétariat"/);
    assert.match(layout, /sidebar-id="secretariat-sidebar"/);
});

test('intertitres du menu : clés secretariatShell.sections.* en FR et EN, sans caractère typographique interdit', () => {
    for (const key of ['daily', 'follow']) {
        assert.ok(layout.includes(`secretariatShell.sections.${key}`), `intertitre ${key} non utilisé`);
        for (const locale of ['fr', 'en']) {
            const v = msgs[locale].secretariatShell?.sections?.[key];
            assert.equal(typeof v, 'string', `${locale}.secretariatShell.sections.${key}`);
            assert.doesNotMatch(v, /[—–…·]/);
        }
    }
});

test('aucune couleur brute ni hexadécimal dans l’enveloppe', () => {
    assert.doesNotMatch(layout, /#[0-9a-fA-F]{6}\b/);
    assert.doesNotMatch(layout, /\b(emerald|indigo|slate|gray|red|green|blue|teal)-\d{2,3}\b/);
});
