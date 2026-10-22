import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { getPostLoginPath, resolveRootPath } from '../src/utils/postLoginRoute.js';

const EXPECTED = {
    admin: '/dashboard/overview', promoteur: '/dashboard/overview',
    psychologist: '/dashboard/toxico-dashboard', spiritualcounsellor: '/dashboard/toxico-dashboard',
    toxicomanager: '/dashboard/toxico-dashboard', assistant: '/dashboard/toxico-dashboard',
    laborantin: '/dashboard/labo/overviewlab', biologiste: '/dashboard/labo/overviewlab',
    stockcontroller: '/dashboard/stock-control',
    medecin: '/medical/doctors', nurse: '/medical/patients',
    secretaire: '/secretariat/',
};

test('mapping role -> page d\'accueil', () => {
    for (const [role, path] of Object.entries(EXPECTED)) assert.equal(getPostLoginPath(role), path, role);
});
test('insensible a la casse, role inconnu ou vide -> defaut inchange', () => {
    assert.equal(getPostLoginPath('Medecin'), '/medical/doctors');
    assert.equal(getPostLoginPath('Nurse'), '/medical/patients');
    assert.equal(getPostLoginPath(undefined), '/dashboard/toxico-dashboard');
    assert.equal(getPostLoginPath('inconnu'), '/dashboard/toxico-dashboard');
});
test('le medecin et le nurse sont rediriges vers une route que leur role peut ouvrir (meta.roles)', () => {
    const src = readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8');
    const i = src.indexOf("path: 'doctors'");
    assert.ok(i > 0);
    const block = src.slice(i, src.indexOf('}', src.indexOf('meta:', i) + 20) + 1);
    assert.match(block, /roles:\s*\[[^\]]*ROLES\.MEDECIN/);
    assert.match(block, /roles:\s*\[[^\]]*ROLES\.NURSE/);
    // L'infirmiere a sa propre accueil (liste des patients) : meme controle sur cette route.
    const j = src.indexOf("name: 'medical-patients'");
    assert.ok(j > 0);
    const patientsBlock = src.slice(j, src.indexOf('}', src.indexOf('meta:', j) + 20) + 1);
    assert.match(patientsBlock, /roles:\s*\[[^\]]*ROLES\.NURSE/);
    assert.equal(getPostLoginPath('nurse'), '/medical/patients');
});

const ALL_ROLES = ['admin', 'promoteur', 'secretaire', 'medecin', 'nurse', 'laborantin',
    'Psychologist', 'SpiritualCounsellor', 'ToxicoManager', 'Assistant', 'StockController'];

test('resolveRootPath : non authentifie -> /login quel que soit le role', () => {
    for (const r of [...ALL_ROLES, undefined, 'inconnu']) assert.equal(resolveRootPath(r, false), '/login', String(r));
});
test('resolveRootPath : chaque role connu atterrit comme au login (casse DB incluse)', () => {
    for (const r of ALL_ROLES) assert.equal(resolveRootPath(r, true), getPostLoginPath(r), r);
    assert.equal(resolveRootPath('admin', true), '/dashboard/overview');
    assert.equal(resolveRootPath('medecin', true), '/medical/doctors');
    assert.equal(resolveRootPath('nurse', true), '/medical/patients');
});
test('resolveRootPath : role inconnu ou vide -> /forbidden (jamais une route refusee)', () => {
    assert.equal(resolveRootPath('inconnu', true), '/forbidden');
    assert.equal(resolveRootPath(undefined, true), '/forbidden');
    assert.equal(resolveRootPath('', true), '/forbidden');
});
test('resolveRootPath : la cible de chaque role est ouvrable par ce role (meta.roles du routeur)', () => {
    const src = readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8');
    const anchors = {
        '/dashboard/overview': "path: 'overview'",
        '/dashboard/toxico-dashboard': "path: 'toxico-dashboard'",
        '/dashboard/labo/overviewlab': "path: 'overviewlab'",
        '/dashboard/stock-control': "path: 'stock-control'",
        '/medical/doctors': "path: 'doctors'",
        '/medical/patients': "name: 'medical-patients'",
        '/secretariat/': "name: 'secretariat-home'",
    };
    const norm = (x) => x.replace(/ROLES\.(\w+)/g, (_, k) => ({
        ADMIN: 'admin', PROMOTEUR: 'promoteur', PSYCHOLOGIST: 'psychologist', SPIRITUAL: 'spiritualcounsellor',
        TOXICO_MANAGER: 'toxicomanager', ASSISTANT: 'assistant', STOCK_CONTROLLER: 'stockcontroller',
        LABORANTIN: 'laborantin', MEDECIN: 'medecin', NURSE: 'nurse', SECRETAIRE: 'secretaire',
    }[k])).toLowerCase();
    for (const role of ALL_ROLES) {
        const target = resolveRootPath(role, true);
        const anchor = anchors[target];
        assert.ok(anchor, 'cible sans ancre de test: ' + target);
        const i = src.indexOf(anchor);
        assert.ok(i > 0, anchor);
        const m = src.slice(i).match(/roles:\s*\[([^\]]*)\]/);
        const roles = norm(m[1]);
        assert.ok(roles.includes(role.toLowerCase()) || role === 'admin', role + ' -> ' + target);
    }
});