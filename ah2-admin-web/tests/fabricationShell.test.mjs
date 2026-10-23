import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const { paletteForRole, NAV_PALETTES } = await import('../src/design/navPalettes.js');

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

const router = read('src/router/index.js');
const layout = read('src/components/layout/MainLayout.vue');
const userModal = read('src/components/users/UserModal.vue');

const READ_ROLES = '[ROLES.PRODUCTION_MANAGER, ROLES.PROMOTEUR, ROLES.ADMIN]';

test('le role ProductionManager est declare partout', () => {
    for (const [name, src] of [['router', router], ['MainLayout', layout]]) {
        assert.ok(src.includes("PRODUCTION_MANAGER: 'ProductionManager'"), `${name} : constante absente`);
    }
    assert.ok(userModal.includes("'ProductionManager'"), 'UserModal : role absent de la liste');
    assert.ok(/ProductionManager:\s*'Responsable de production'/.test(userModal), 'UserModal : libelle absent');
});

for (const [path, name, file] of [
    ['fabrication-intrants', null, 'FabIntrants'],
    ['fabrication-lots', null, 'FabLots'],
    ['fabrication-lots/:id', 'fabrication-lot', 'FabLotDetail'],
    ['fabrication-suivi', null, 'FabSuivi'],
]) {
    test(`route ${path}`, () => {
        const i = router.indexOf(`path: '${path}'`);
        assert.ok(i > 0, 'route absente');
        const block = router.slice(i, router.indexOf('},\n', i) + 3);
        if (name) assert.ok(block.includes(`name: '${name}'`));
        assert.ok(block.includes(`import('@/views/modules/fabrication/${file}.vue')`), 'composant');
        assert.ok(block.includes(`roles: ${READ_ROLES}`), 'roles de lecture');
        assert.ok(existsSync(new URL(`../src/views/modules/fabrication/${file}.vue`, import.meta.url)), 'coquille absente');
    });
}

test('palette du role', () => {
    const p = paletteForRole('ProductionManager');
    assert.notEqual(p, 'night');
    assert.ok(p in NAV_PALETTES);
});

test('menu : groupe fabrication et entrees', () => {
    assert.ok(/fabrication:\s*\{\s*labelKey:\s*'fabrication\.menu_group'/.test(layout));
    for (const p of ['intrants', 'lots', 'suivi']) {
        const i = layout.indexOf(`path: '/dashboard/fabrication-${p}'`);
        assert.ok(i > 0, p);
        const block = layout.slice(i, layout.indexOf('}', i));
        assert.ok(block.includes("group: 'fabrication'"));
        assert.ok(block.includes(`labelKey: 'fabrication.menu_${p}'`));
        assert.ok(block.includes('ROLES.PRODUCTION_MANAGER') && block.includes('ROLES.PROMOTEUR'));
    }
});

test('cles i18n fabrication.menu_* en FR et EN, sans caractere interdit', () => {
    for (const lang of ['fr', 'en']) {
        for (const k of ['menu_group', 'menu_intrants', 'menu_lots', 'menu_suivi']) {
            const v = pick(msgs[lang], `fabrication.${k}`);
            assert.ok(typeof v === 'string' && v.length > 0, `${lang} fabrication.${k}`);
            assert.ok(!/[–—…·→←]/.test(v), `${lang} ${k} caractere interdit`);
        }
        const role = pick(msgs[lang], 'users.roles.ProductionManager') ?? JSON.stringify(msgs[lang]).includes('ProductionManager');
        assert.ok(role, `${lang} libelle de role`);
    }
});

test('passerelle : toutes les methodes', () => {
    // l'alias @/ n'existe pas sous node : on lit la source
    const gw = read('src/services/FabricationGateway.js');
    for (const m of ['listIntrants', 'createIntrant', 'updateIntrant', 'setThreshold', 'listPurchases', 'createPurchase',
        'updatePurchase', 'cancelPurchase', 'listBatches', 'createBatch', 'getBatch', 'updateBatch', 'startBatch',
        'finishBatch', 'reopenBatch', 'cancelBatch', 'shipBatch', 'getSettings', 'updateSettings', 'getAnomalies',
        'getSummary', 'getProductCost', 'getTrace', 'listProducts']) {
        assert.ok(gw.includes(`async ${m}(`), m);
    }
    assert.ok(gw.includes("api.get('/fabrication/products')"), 'route des produits');
});
