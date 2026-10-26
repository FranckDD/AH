// MainLayout (cadre de l'admin, du promoteur, du labo, de la toxico et du stock-control) : le menu de chaque rôle,
// la cloche, le jeton d'impression et les actions du cadre restent identiques après le passage sur AppShell.
// Les listes ci-dessous ont été relevées sur l'ancien MainLayout (avant la refonte) : elles figent le contrat.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseMenuItems, hasRoleFor, readMainLayout } from './helpers_mainLayoutMenu.mjs';
import { readFileSync } from 'node:fs';
import { buildMenu } from '../src/utils/sidebarMenu.js';

const src = readMainLayout();

const EXPECTED_ITEMS = [
    {"path":"/dashboard/overview","labelKey":"common.dashboard","roles":["admin","promoteur"]},
    {"path":"/dashboard/toxico-dashboard","labelKey":"toxico.dashboard.title","roles":["Psychologist","SpiritualCounsellor","ToxicoManager","Assistant"]},
    {"path":"/dashboard/toxico","labelKey":"toxico.title","roles":["Psychologist","SpiritualCounsellor","ToxicoManager","Assistant","promoteur"]},
    {"path":"/dashboard/labo","labelKey":"lab.title","roles":["laborantin","ToxicoManager"]},
    {"path":"/dashboard/finance","labelKey":"finance.title","roles":["admin"]},
    {"path":"/dashboard/discount-review","labelKey":"discount_review.title","roles":["admin","promoteur"]},
    {"path":"/dashboard/discount-history","labelKey":"discount_history.title","roles":["admin","promoteur"]},
    {"path":"/dashboard/cash-closures","labelKey":"cashClosure.review_title","roles":["admin","promoteur"]},
    {"path":"/dashboard/reductions-personnel","labelKey":"staffDiscount.title","roles":["admin","promoteur"]},
    {"path":"/dashboard/reports","labelKey":"reports.menu","roles":["admin","promoteur"]},
    {"path":"/dashboard/users","labelKey":"common.users","roles":["admin"]},
    {"path":"/dashboard/patients","labelKey":"patients.title","roles":["ToxicoManager"]},
    {"path":"/dashboard/stock","labelKey":"stock.title","group":"stock","roles":["ToxicoManager","Assistant"]},
    {"path":"/dashboard/stock-lots","labelKey":"stockOps.menu_lots","group":"stock","adminHidden":true,"roles":["admin","Assistant"]},
    {"path":"/dashboard/stock-receipts","labelKey":"stockOps.menu_receipts","group":"stock","adminHidden":true,"roles":["admin","Assistant"]},
    {"path":"/dashboard/stock-incidents","labelKey":"stockOps.menu_incidents","group":"stock","adminHidden":true,"roles":["admin","Assistant"]},
    {"path":"/dashboard/stock-control","labelKey":"stockControl.menu_control","group":"stock","adminHidden":true,"roles":["StockController","admin"]},
    {"path":"/dashboard/stock-movements","labelKey":"stockControl.menu_movements","group":"stock","roles":["StockController","admin","Assistant"]},
    {"path":"/dashboard/stock-count","labelKey":"stockCount.menu","group":"stock","roles":["StockController","admin","promoteur"]},
    {"path":"/dashboard/stock-adjustment-requests","labelKey":"stockAdjust.menu_admin","group":"stock","roles":["admin"]},
    {"path":"/dashboard/lab-stock-products","labelKey":"labStock.menu_products","group":"labstock","roles":["laborantin","StockController","promoteur","ToxicoManager"]},
    {"path":"/dashboard/lab-stock-requests","labelKey":"labStock.menu_requests","group":"labstock","roles":["laborantin","StockController","promoteur","ToxicoManager"]},
    {"path":"/dashboard/lab-stock-receipts","labelKey":"labStock.menu_receipts","group":"labstock","roles":["StockController","promoteur"]},
    {"path":"/dashboard/lab-stock-count","labelKey":"labStock.menu_count","group":"labstock","adminHidden":true,"roles":["laborantin"]},
    {"path":"/dashboard/lab-stock-alerts","labelKey":"labStock.menu_alerts","group":"labstock","roles":["laborantin","StockController","promoteur","ToxicoManager"]},
    {"path":"/dashboard/lab-stock-movements","labelKey":"labStock.menu_movements","group":"labstock","roles":["laborantin","StockController","promoteur","ToxicoManager"]},
    {"path":"/dashboard/lab-stock-expenses","labelKey":"labStock.menu_expenses","group":"labstock","roles":["promoteur","ToxicoManager"]},
    {"path":"/dashboard/fabrication-lots","labelKey":"fabrication.menu_lots","group":"fabrication","roles":["ProductionManager","promoteur"]},
    {"path":"/dashboard/fabrication-intrants","labelKey":"fabrication.menu_intrants","group":"fabrication","roles":["ProductionManager","promoteur"]},
    {"path":"/dashboard/fabrication-suivi","labelKey":"fabrication.menu_suivi","group":"fabrication","roles":["ProductionManager","promoteur"]},
    {"path":"/dashboard/logs","labelKey":"tech.title","roles":["ToxicoManager"]},
    {"path":"/dashboard/configuration","labelKey":"config.title","separator":true,"roles":["ToxicoManager"]},
];
const EXPECTED_MENU = {"admin":["/dashboard/overview","/dashboard/toxico-dashboard","/dashboard/toxico","/dashboard/labo","/dashboard/finance","/dashboard/discount-review","/dashboard/discount-history","/dashboard/cash-closures","/dashboard/reductions-personnel","/dashboard/reports","/dashboard/users","/dashboard/patients","stock:stock,stock-movements,stock-count,stock-adjustment-requests","labstock:lab-stock-products,lab-stock-requests,lab-stock-receipts,lab-stock-alerts,lab-stock-movements,lab-stock-expenses","fabrication:fabrication-lots,fabrication-intrants,fabrication-suivi","/dashboard/logs","/dashboard/configuration"],"promoteur":["/dashboard/overview","/dashboard/toxico","/dashboard/discount-review","/dashboard/discount-history","/dashboard/cash-closures","/dashboard/reductions-personnel","/dashboard/reports","/dashboard/stock-count","labstock:lab-stock-products,lab-stock-requests,lab-stock-receipts,lab-stock-alerts,lab-stock-movements,lab-stock-expenses","fabrication:fabrication-lots,fabrication-intrants,fabrication-suivi"],"laborantin":["/dashboard/labo","labstock:lab-stock-products,lab-stock-requests,lab-stock-count,lab-stock-alerts,lab-stock-movements"],"ToxicoManager":["/dashboard/toxico-dashboard","/dashboard/toxico","/dashboard/labo","/dashboard/patients","/dashboard/stock","labstock:lab-stock-products,lab-stock-requests,lab-stock-alerts,lab-stock-movements,lab-stock-expenses","/dashboard/logs","/dashboard/configuration"],"Psychologist":["/dashboard/toxico-dashboard","/dashboard/toxico"],"SpiritualCounsellor":["/dashboard/toxico-dashboard","/dashboard/toxico"],"Assistant":["/dashboard/toxico-dashboard","/dashboard/toxico","stock:stock,stock-lots,stock-receipts,stock-incidents,stock-movements"],"StockController":["stock:stock-control,stock-movements,stock-count","labstock:lab-stock-products,lab-stock-requests,lab-stock-receipts,lab-stock-alerts,lab-stock-movements"],"ProductionManager":["fabrication:fabrication-lots,fabrication-intrants,fabrication-suivi"]};

const GROUPS = { stock: { labelKey: 'stockOps.menu_group' }, labstock: { labelKey: 'labStock.menu_group' }, fabrication: { labelKey: 'fabrication.menu_group' } };

test('les entrées du menu (chemin, libellé, rôles, groupe, adminHidden, séparateur) sont inchangées', () => {
    assert.deepEqual(JSON.parse(JSON.stringify(parseMenuItems(src))), EXPECTED_ITEMS);
});

for (const [role, expected] of Object.entries(EXPECTED_MENU)) {
    test(`menu du rôle ${role} : mêmes entrées, mêmes sous-menus`, () => {
        const entries = buildMenu(parseMenuItems(src), { isAdmin: role === 'admin', hasRole: hasRoleFor(role), groups: GROUPS });
        const got = entries.map((x) => (x.type === 'link' ? x.item.path : `${x.key}:${x.children.map((c) => c.path.replace('/dashboard/', '')).join(',')}`));
        assert.deepEqual(got, expected);
    });
}

test('les groupes de sous-menus sont inchangés', () => {
    assert.match(src, /stock: \{ labelKey: 'stockOps\.menu_group', icon: CubeIcon \}/);
    assert.match(src, /labstock: \{ labelKey: 'labStock\.menu_group', icon: BeakerIcon \}/);
});

test('filtrage : buildMenu avec isAdmin (authStore.isAdmin ou rôle admin) et hasRole du store', () => {
    assert.match(src, /buildMenu\(menuItems, \{/);
    assert.match(src, /isAdmin: authStore\.isAdmin \|\| authStore\.hasRole\(\[ROLES\.ADMIN\]\)/);
    assert.match(src, /hasRole: \(roles\) => authStore\.hasRole\(roles\)/);
});

test('cloche des notifications réservée aux mêmes rôles', () => {
    assert.ok(src.includes("authStore.hasRole(['admin', 'promoteur', 'secretaire', 'Assistant', 'StockController', 'laborantin', 'ToxicoManager', 'ProductionManager'])")
        || src.includes(":bell-roles=\"['admin', 'promoteur', 'secretaire', 'Assistant', 'StockController', 'laborantin', 'ToxicoManager', 'ProductionManager']\""));
});

test('au montage : jeton d’impression pour admin et promoteur seulement ; informations de la structure chargées par le cadre', () => {
    assert.match(src, /authStore\.hasRole\(\[ROLES\.ADMIN, ROLES\.PROMOTEUR\]\)/);
    assert.match(src, /configStore\.fetchTicketPrintToken\(\)/);
    // depuis la refonte, AppShell charge les informations de la structure (comme avant dans MainLayout)
    assert.match(readFileSync(new URL('../src/components/layout/AppShell.vue', import.meta.url), 'utf8'), /configStore\.fetchStructureInfo\(\)/);
});

test('le cadre fournit routes enfants (clé fullPath), compte, langue, déconnexion et cloche', () => {
    const shell = readFileSync(new URL('../src/components/layout/AppShell.vue', import.meta.url), 'utf8');
    assert.match(shell, /<router-view :key="route\.fullPath"/);
    assert.match(shell, /<AccountModal/);
    assert.match(shell, /changeLanguage\(/);
    assert.match(shell, /authStore\.logout\(\)/);
    assert.match(shell, /<NotificationBell v-if="authStore\.hasRole\(bellRoles\)"/);
});

// --- Refonte : cadre commun et palette par rôle ---
test('MainLayout passe par AppShell, avec la palette du rôle et le menu au format du cadre', () => {
    assert.match(src, /import AppShell from '@\/components\/layout\/AppShell\.vue'/);
    assert.match(src, /<AppShell[\s>]/);
    assert.match(src, /:palette="paletteForRole\(authStore\.userRole\)"/);
    assert.match(src, /toShellGroups\(menuEntries\.value\)/);
    assert.doesNotMatch(src.slice(src.indexOf('<script')), /(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}/);
    assert.doesNotMatch(src.slice(0, src.indexOf('<script')), /bg-gray|text-gray/);
});

test('paletteForRole : une palette par rôle, repli sur le bleu nuit', async () => {
    const { paletteForRole, NAV_PALETTES } = await import('../src/design/navPalettes.js');
    const expected = {
        admin: 'slate', promoteur: 'gold', secretaire: 'forest', medecin: 'night', nurse: 'rose', laborantin: 'lagoon',
        ToxicoManager: 'ember', Psychologist: 'indigo', SpiritualCounsellor: 'burgundy', Assistant: 'olive',
        StockController: 'violet', ProductionManager: 'sky', inconnu: 'night', '': 'night',
    };
    for (const [role, palette] of Object.entries(expected)) assert.equal(paletteForRole(role), palette, role);
    assert.equal(paletteForRole(undefined), 'night');
    assert.equal(paletteForRole('ADMIN'), 'slate');
    for (const p of ['slate', 'lagoon', 'ember', 'violet']) assert.ok(NAV_PALETTES[p], p);
});
