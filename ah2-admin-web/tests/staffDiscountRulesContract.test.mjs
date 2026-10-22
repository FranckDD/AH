import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
const rules = read('../src/views/modules/caisse/StaffDiscountRules.vue');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);
const templateOf = (src) => src.slice(0, src.indexOf('<script'));

function check(name, src, needles) {
    for (const needle of needles) {
        test(`${name} : « ${needle} » est conservé`, () => {
            assert.ok(src.includes(needle), `« ${needle} » a disparu de ${name}`);
        });
    }
}

// --- Contrat : règles par catégorie et membres du personnel (aucun changement de règle ni d'appel) ---
check('StaffDiscountRules', rules, [
    // règles
    'StaffDiscountGateway.list()', 'CATEGORIES.map((c) => [c, {', 'min_invoice_amount: 0, rate_percent: null, is_active: false, saving: false, message: \'\', isError: false,',
    'rows[r.category].min_invoice_amount = Number(r.min_invoice_amount) || 0;', 'rows[r.category].rate_percent = Number(r.rate_percent) || null;', 'rows[r.category].is_active = Boolean(r.is_active);',
    'if (!Number.isInteger(rate) || rate < 1 || rate > 100) {', "row.message = t('staffDiscount.invalid_rate');", 'if (!Number.isFinite(min) || min < 0) {', "row.message = t('staffDiscount.invalid_min');",
    'StaffDiscountGateway.save(cat, { min_invoice_amount: min, rate_percent: rate, is_active: Boolean(row.is_active) })', "row.message = t('staffDiscount.saved');",
    'saveRule(cat)', 'rows[cat].saving', 'rows[cat].message', 'rows[cat].isError', 'rulesLoadError',
    '.min_invoice_amount', '.rate_percent', '.is_active', 'type="number"', 'min="0"', 'min="1" max="100"', 'type="checkbox"',
    // membres
    'StaffDiscountGateway.lookupStaff({ onlyStaff: true })', 'StaffDiscountGateway.lookupStaff({ q })', 'StaffDiscountGateway.setStaff(p.patient_id, !p.is_staff)',
    'await Promise.all([loadMembers(), runSearch()]);', 'setTimeout(runSearch, 300)', 'if (q.length < 2) {', 'searchQuery.trim().length >= 2',
    'v-model="searchQuery"', '@input="onSearchInput"', 'toggleStaff(p)', ':disabled="togglingId === p.patient_id"', 'p.is_staff', 'p.code_patient', 'p.first_name', 'p.last_name',
    ':loading="isSearching"', ':rows="searchResults"', ':rows="members"', 'membersError',
    // les etats vides (search_empty, members_empty) sont ceux du tableau commun (empty-title)
    // erreurs
    "if (status === 403) return t('staffDiscount.error_forbidden');", "return detail.map((d) => d.msg || String(d)).join(' ; ')".replace('return ', "if (Array.isArray(detail) && detail.length) return "),
    'onMounted(() => {', 'loadRules();', 'loadMembers();',
    // clés
    "$t('staffDiscount.title')", "$t('staffDiscount.rules_title')", "$t('staffDiscount.rules_hint')", "t('staffDiscount.col_category')", "$t('staffDiscount.col_min_amount')",
    "$t('staffDiscount.col_rate')", "t('staffDiscount.col_active')", "t('staffDiscount.col_action')", "$t('staffDiscount.saving')", "$t('staffDiscount.save')",
    "$t('staffDiscount.matching_hint')", "$t('staffDiscount.members_title')", "$t('staffDiscount.search_placeholder')", "$t('staffDiscount.search_empty')",
    "$t('staffDiscount.unmark_staff')", "$t('staffDiscount.mark_staff')", "$t('staffDiscount.members_empty')", "t('staffDiscount.col_code')", "t('staffDiscount.col_name')", "$t('staffDiscount.col_staff')",
]);

test('toutes les clés staffDiscount.* et staffDiscountScreens.* citées existent en FR et EN', () => {
    const used = new Set();
    for (const m of rules.matchAll(/['"`(]((?:staffDiscount|staffDiscountScreens)\.[a-zA-Z_.]+)['"`)]/g)) used.add(m[1]);
    assert.ok(used.size >= 20);
    for (const k of used) {
        if (k.includes('${')) continue;
        for (const locale of ['fr', 'en']) {
            const v = pick(msgs[locale], k);
            assert.ok(v !== undefined && v !== null && v !== '', `${locale}.${k} manquante`);
        }
    }
});

// --- Refonte (rouge tant que non refondu) ---
test('StaffDiscountRules : composants ui/, tableaux responsives, champs étiquetés', () => {
    assert.match(rules, /from '@\/components\/ui'/);
    for (const c of ['PageHeader', 'AppCard', 'ResponsiveTable', 'FormField', 'AppButton']) assert.match(rules, new RegExp(`\\b${c}\\b`), c);
    assert.match(rules, /role="alert"/);
    assert.match(rules, /role="status"|'status'/);
});

test('StaffDiscountRules : jetons du thème, texte >= 13 px, aucun caractère typographique interdit dans le gabarit', () => {
    assert.doesNotMatch(rules, /\b(emerald|indigo|slate|yellow|red|gray|blue|teal|amber|purple|rose|orange|green)-\d{2,3}\b/);
    assert.doesNotMatch(rules, /text-xs|text-\[(?:[0-9]|1[0-2])px\]/);
    assert.doesNotMatch(templateOf(rules), /[—–…·]|\p{Extended_Pictographic}/u);
});

test('clés staffDiscountScreens.* en FR et EN', () => {
    const keys = ['search_label', 'rule_active_label'];
    for (const locale of ['fr', 'en']) {
        for (const k of keys) {
            const v = msgs[locale].staffDiscountScreens?.[k];
            assert.equal(typeof v, 'string', `${locale}.staffDiscountScreens.${k}`);
            assert.doesNotMatch(v, /[—–…·]/, `${locale}.staffDiscountScreens.${k}`);
        }
    }
});
