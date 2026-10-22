import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const view = readFileSync(new URL('../src/views/dashboards/DashboardOverview.vue', import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : ce que l'écran fait aujourd'hui (aucun changement de chiffre ni de comportement) ---
check('DashboardOverview', view, [
    // chargement, filtres, rafraîchissement
    'dashboardStore.fetchDashboardData()', 'dashboardStore.setDates(today, today)', "new Date().toISOString().substring(0, 10)",
    'v-model="dashboardStore.filters.startDate"', 'v-model="dashboardStore.filters.endDate"', '@click="resetToToday"', '@click="applyFilters"',
    'configStore.fetchStructureInfo()',
    // tolérance aux pannes : jamais 0 à la place d'un bloc en échec
    "dashboardStore.indisponibles.includes(nomBloc) ? 'Indisponible' : valeur",
    "dashboardStore.indisponibles.includes('income') || dashboardStore.indisponibles.includes('expense')",
    'dashboardStore.stats.income - dashboardStore.stats.withdrawals',
    "valeurAffichee('income', formatCurrency(dashboardStore.stats.income))", "valeurAffichee('expense', formatCurrency(dashboardStore.stats.withdrawals))",
    'soldeAffiche', "valeurAffichee('toxico', dashboardStore.stats.toxicoAdmissionsThisMonth)",
    "valeurAffichee('users', `${dashboardStore.stats.onlineUsers} inscrits`)", "valeurAffichee('hospitalized', dashboardStore.stats.hospitalizedCount)",
    'dashboardStore.stats.income >= dashboardStore.stats.withdrawals',
    // activités récentes
    'dashboardStore.recentActivities', 'dashboardStore.isLoading', 'item.label', 'item.description && item.description !== item.label', 'formatDate(item.date)',
    'formatCurrency(item.amount)', "item.type === 'INCOME'", "item.status === 'active' || item.status === 'Validé'", 'item.status',
    "dashboardStore.indisponibles.includes('activites')", 'Activités indisponibles (erreur de chargement).', 'Aucune activité récente.',
    // navigation et actions rapides
    "$router.push('/dashboard/finance')", "$router.push('/dashboard/users')", "$router.push('/dashboard/toxico')",
    '@click="showAdmissionModal = true"', '@click="showFinanceModal = true"', 'Support technique : 674 69 79 08',
    // modales et leur enregistrement
    '<ToxicoAdmissionModal', '@close="showAdmissionModal = false"', '@save="handleAdmissionSaved"', '<FinanceModal', '@close="showFinanceModal = false"', '@save="handleFinanceSaved"',
    'await financialStore.addTransaction(transactionData);', "alert(\"Échec de l'enregistrement : la transaction n'a pas été enregistrée.\");",
    'showFinanceModal.value = false;', 'alert("Transaction enregistrée !");', 'alert("Admission enregistrée !");',
    "new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value)",
    // clés
    "$t('dashboard.title')", "$t('dashboard.subtitle')", "$t('dashboard.filters.start_date')", "$t('dashboard.filters.end_date')", "$t('dashboard.filters.apply')",
    "$t('dashboard.actions.refresh')", "$t('dashboard.actions.manage_staff')", "$t('dashboard.actions.new_admission')", "$t('dashboard.actions.payment')",
    "$t('dashboard.stats.income')", "$t('dashboard.stats.withdrawals')", "$t('finance.balance')", "$t('dashboard.stats.patients')",
    "$t('dashboard.stats.users_online')", "$t('dashboard.stats.alerts')", "$t('dashboard.stats.bed_occupancy')",
]);

test('toutes les clés dashboard.*, finance.* et adminDashboard.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of view.matchAll(/['"`(]((?:dashboard|finance|adminDashboard)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size > 12);
    for (const k of used) {
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que l'écran n'est pas refondu) ---
test('DashboardOverview : composants ui/ (en-tête, tuiles, tableau, champs, boutons)', () => {
    assert.match(view, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'StatTile', 'StatusBadge', 'ResponsiveTable', 'FormField', 'AppButton', 'AppCard']) assert.match(view, new RegExp(`\\b${c}\\b`), c);
    assert.doesNotMatch(view, /StatCard/, 'StatCard est remplacé par StatTile');
});

test('DashboardOverview : montants alignés à droite, entrée et sortie écrites, tableau à lignes alternées', () => {
    assert.match(view, /align: 'right'/);
    assert.match(view, /<StatusBadge/);
    assert.match(view, /\n\s+striped\s*\n/);
});

test('DashboardOverview : aucun emoji ni caractère typographique interdit, jetons du thème, texte >= 13 px', () => {
    assert.doesNotMatch(templateOf(view), /[—–…·]|\p{Extended_Pictographic}/u);
    assert.doesNotMatch(view, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
    assert.doesNotMatch(view, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
});

test('clés adminDashboard.* en FR et EN', () => {
    const keys = ['filters', 'income_note', 'expense_note', 'balance_note', 'toxico_note', 'see_all', 'see_alerts', 'entry', 'sortie', 'col_description',
        'col_date', 'col_amount', 'col_type', 'col_status', 'quick_actions', 'quick_actions_help'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].adminDashboard?.[k];
            assert.equal(typeof v, 'string', `${locale}.adminDashboard.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.adminDashboard.${k}`);
        }
    }
});

test('les dates du tableau de bord suivent la langue choisie (FR ou EN)', () => {
    assert.match(view, /const \{ t, locale \} = useI18n\(\);/);
    assert.match(view, /locale\.value === 'en' \? 'en-GB' : 'fr-FR'/);
    assert.doesNotMatch(view, /toLocale(?:Date|Time)String\('fr-FR'/);
});
