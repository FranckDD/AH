import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const home = read('views/modules/secretariat/SecretariatHomeView.vue');
const patientList = read('views/modules/patients/PatientList.vue');
const tilePath = new URL('../src/components/ui/StatTile.vue', import.meta.url);
const tile = existsSync(tilePath) ? readFileSync(tilePath, 'utf8') : '';

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat de l'accueil : tout ce que faisait l'écran avant la refonte (baseline verte) ---
check('SecretariatHomeView', home, [
    'homeStore.fetchHomeData()', 'homeStore.setDates(homeStore.filters.startDate, homeStore.filters.endDate)',
    'v-model="homeStore.filters.startDate"', 'v-model="homeStore.filters.endDate"', '@change="applyFilters"',
    "valeurAffichee('totalPaid'", "valeurAffichee('totalWithdrawn'", "valeurAffichee('remainingDue'", 'soldeAffiche',
    'homeStore.stats.totalPaid - homeStore.stats.totalWithdrawn',
    "homeStore.indisponibles.includes(nomBloc) ? 'Indisponible' : valeur",
    "homeStore.indisponibles.includes('totalPaid') || homeStore.indisponibles.includes('totalWithdrawn')",
    "style: 'currency', currency: 'XAF', minimumFractionDigits: 0", ".replace('XOF', 'FCFA')",
    'homeStore.stats.criticalStockCount', 'homeStore.stats.expiringStockCount', 'homeStore.stats.consultationsCount',
    "homeStore.indisponibles.includes('criticalStockItems')", 'homeStore.criticalStockItems', 'row-key="medication_id"',
    'item.drug_name', 'item.medication_type', 'item.quantity', 'item.threshold', 'item.quantity === 0',
    "t('secretariat.home.title')", "t('secretariat.home.period_from')", "t('secretariat.home.period_to')",
    "t('secretariat.home.total_paid')", "t('secretariat.home.total_withdrawn')", "t('secretariat.home.balance')",
    "t('secretariat.home.remaining_due')", "t('secretariat.home.critical_stock')", "t('secretariat.home.expiring_stock')",
    "t('secretariat.home.consultations_period')", "t('secretariat.home.critical_stock_table_title')",
    "t('secretariat.home.critical_stock_table_error')", "t('secretariat.home.critical_stock_table_empty')",
    "t('secretariat.home.critical_stock_table.out_of_stock')", "t('secretariat.home.critical_stock_table.low_stock')",
]);

test('toutes les clés secretariat.home.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of home.matchAll(/['"`(]secretariat\.home\.([a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 10);
    for (const k of used) {
        for (const locale of ['fr', 'en']) assert.ok(pick(msgs[locale].secretariat.home, k), `${locale}.secretariat.home.${k}`);
    }
});

// --- Nouveau : actions rapides ---
test('trois actions rapides vers la caisse, les retraits et les patients, avec le paramètre nouveau=1', () => {
    for (const to of ['/secretariat/caisse?nouveau=1', '/secretariat/retrait?nouveau=1', '/secretariat/patients?nouveau=1']) {
        assert.ok(home.includes(to), `lien ${to} absent`);
    }
    assert.match(home, /<router-link/);
    assert.match(home, /buttonClasses\(/);
});

test('les actions rapides viennent avant les statistiques', () => {
    assert.ok(home.indexOf('secretariatHome.quick_title') > 0);
    assert.ok(home.indexOf('secretariatHome.quick_title') < home.indexOf("t('secretariat.home.total_paid')"));
});

test('StatTile : composant ui/ réexporté, props attendues, jetons seulement', () => {
    assert.ok(tile.length > 0, 'StatTile.vue manquant');
    assert.match(read('components/ui/index.js'), /StatTile/);
    for (const p of ['title', 'value', 'note', 'icon', 'tone']) assert.match(tile, new RegExp(`${p}:\\s*\\{`), `prop ${p}`);
    assert.doesNotMatch(tile, /#[0-9a-fA-F]{6}\b/);
    assert.doesNotMatch(tile, /\b(emerald|indigo|slate|gray|red|green|blue|teal|amber|orange)-\d{2,3}\b/);
    assert.doesNotMatch(tile, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
});

test('l’ancienne carte partagée StatCard n’est plus utilisée par l’accueil (et reste inchangée)', () => {
    assert.doesNotMatch(home, /StatCard/);
});

// --- Liste des patients : ouverture directe du formulaire depuis une action rapide ---
test('PatientList : ?nouveau=1 ouvre le formulaire, et le paramètre est retiré à la fermeture (pas à l’ouverture)', () => {
    assert.match(patientList, /route\.query\.nouveau === '1'/);
    assert.match(patientList, /openCreateModal\(\)/);
    const close = patientList.slice(patientList.indexOf('const closeModal'), patientList.indexOf('const closeModal') + 400);
    assert.match(close, /router\.replace\(\{ query: \{\} \}\)/);
});

// --- Refonte ---
test('l’accueil utilise des composants ui/, des couleurs par jetons et des textes conformes', () => {
    assert.match(home, /@\/components\/ui/);
    assert.match(home, /ResponsiveTable/);
    assert.match(home, /StatTile/);
    assert.doesNotMatch(home, /#[0-9a-fA-F]{6}\b/);
    assert.doesNotMatch(home, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
    assert.doesNotMatch(home.slice(0, home.indexOf('<script')), /[—–…·]/);
    assert.doesNotMatch(home, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
});

test('clés secretariatHome.* en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        for (const k of ['quick_title', 'quick_invoice', 'quick_withdrawal', 'quick_patient', 'money_title', 'stock_title']) {
            const v = msgs[locale].secretariatHome?.[k];
            assert.equal(typeof v, 'string', `${locale}.secretariatHome.${k}`);
            assert.doesNotMatch(v, /[—–…·]/);
        }
    }
});
