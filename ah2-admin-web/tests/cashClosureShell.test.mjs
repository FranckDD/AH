// Coquille de la cloture de caisse de la secretaire (Tache 9) : route, menu, chargement, etats de l'ecran.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const router = read('src/router/index.js');
const layout = read('src/components/layout/SecretaireLayout.vue');
const view = read('src/views/modules/caisse/CashClosure.vue');

test('route /secretariat/cloture reservee a la secretaire', () => {
    const i = router.indexOf("path: 'cloture'");
    assert.ok(i > 0, 'route absente');
    const block = router.slice(i, router.indexOf("path: '", i + 5));
    assert.ok(block.includes("name: 'secretariat-cash-closure'"));
    assert.ok(block.includes("import('@/views/modules/caisse/CashClosure.vue')"));
    assert.ok(block.includes('roles: [ROLES.SECRETAIRE]'));
    assert.ok(router.indexOf("path: '/secretariat'") < i, 'enfant de /secretariat');
});

test('menu du secretariat : entree cloture dans le travail du jour', () => {
    const i = layout.indexOf("'/secretariat/cloture'");
    assert.ok(i > 0);
    assert.ok(layout.slice(i, i + 200).includes("'secretariat.nav.cash_closure'"));
    assert.ok(i < layout.indexOf("key: 'follow'"), 'dans le groupe du jour');
    for (const l of ['fr', 'en']) assert.equal(typeof msgs[l].secretariat.nav.cash_closure, 'string');
});

test('ouverture : rattrapage puis statut', () => {
    assert.match(view, /onMounted\(\(\) => \{?\s*store\.load\(\)/);
});

test('caisse non initialisee : message clair, aucun formulaire', () => {
    assert.match(view, /v-if="store\.status && !store\.status\.configured"/);
    assert.match(view, /cashClosure\.not_configured_message/);
    const i = view.indexOf('<form');
    const notConf = view.indexOf('!store.status.configured');
    assert.ok(notConf < i);
    assert.match(view, /v-else-if="store\.status && !store\.result"/);
});

test('un champ par mode : especes comptees, releve operateur pour les modes mobiles', () => {
    assert.match(view, /v-for="m in store\.status\.modes"/);
    assert.match(view, /m\.source === 'physical' \? t\('cashClosure\.field_cash'\) : t\('cashClosure\.field_operator'/);
});

test('lien vers la liste des ventes existante', () => {
    assert.match(view, /to="\/secretariat\/caisse"/);
});

test('apres validation : tableau par mode avec ecart en mots', () => {
    assert.match(view, /gapWords\(/);
    for (const c of ['opening', 'entries', 'exits', 'expected', 'counted', 'gap']) assert.match(view, new RegExp(`key: '${c}'`), c);
});
