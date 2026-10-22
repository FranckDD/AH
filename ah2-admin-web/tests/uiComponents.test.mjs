import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { describedBy, buttonClasses, normalizeColumns, alignClass } from '../src/utils/ui.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

test('describedBy : aide et erreur relient les ids, rien sinon', () => {
    assert.equal(describedBy('nom', {}), undefined);
    assert.equal(describedBy('nom', { help: 'Aide' }), 'nom-help');
    assert.equal(describedBy('nom', { error: 'Oups' }), 'nom-error');
    assert.equal(describedBy('nom', { help: 'Aide', error: 'Oups' }), 'nom-error nom-help');
    assert.equal(describedBy('nom'), undefined);
    assert.equal(describedBy('', { help: 'x' }), undefined);
});

test('buttonClasses : variantes et tailles issues des jetons, repli sur primary/md', () => {
    assert.match(buttonClasses('primary', 'md'), /bg-brand-600/);
    assert.match(buttonClasses('secondary', 'md'), /border-brand-600/);
    assert.match(buttonClasses('danger', 'md'), /bg-tone-danger-text/);
    assert.match(buttonClasses('ghost', 'md'), /bg-transparent/);
    assert.match(buttonClasses('primary', 'md'), /min-h-11/);
    assert.match(buttonClasses('primary', 'lg'), /min-h-12/);
    assert.equal(buttonClasses('nope', 'xx'), buttonClasses('primary', 'md'));
    assert.equal(buttonClasses(), buttonClasses('primary', 'md'));
});

test('buttonClasses : aucune couleur Tailwind brute ni hexadécimal', () => {
    for (const v of ['primary', 'secondary', 'danger', 'ghost']) {
        const cls = buttonClasses(v, 'md');
        assert.doesNotMatch(cls, /#[0-9a-f]{3,6}|(slate|gray|indigo|emerald|red|green|blue)-\d/);
        assert.match(cls, /focus-visible:/);
    }
});

test('normalizeColumns : défauts, alignement, colonnes invalides ignorées', () => {
    const cols = normalizeColumns([
        { key: 'name', label: 'Nom' },
        { key: 'qty', label: 'Qté', align: 'right', class: 'w-20' },
        { key: 'x', label: 'X', align: 'weird' },
        { label: 'sans clé' },
        null,
        'str',
    ]);
    assert.deepEqual(cols, [
        { key: 'name', label: 'Nom', align: 'left', class: '' },
        { key: 'qty', label: 'Qté', align: 'right', class: 'w-20' },
        { key: 'x', label: 'X', align: 'left', class: '' },
    ]);
    assert.deepEqual(normalizeColumns(undefined), []);
    assert.deepEqual(normalizeColumns('x'), []);
});

test('alignClass', () => {
    assert.equal(alignClass('right'), 'text-right');
    assert.equal(alignClass('center'), 'text-center');
    assert.equal(alignClass('left'), 'text-left');
    assert.equal(alignClass('?'), 'text-left');
});

const UI_KEYS = ['noResults', 'noResultsHelp', 'close', 'retry', 'loading', 'required', 'expand', 'collapse', 'actions'];

test('clés ui.* présentes en FR et EN', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        for (const k of UI_KEYS) {
            assert.equal(typeof msgs[locale].ui?.[k], 'string', `${locale}.ui.${k} manquante`);
            assert.ok(msgs[locale].ui[k].length > 0);
        }
    }
});

const COMPONENTS = [
    'AppButton', 'AppCard', 'PageHeader', 'StatusBadge', 'EmptyState',
    'FormField', 'FormSection', 'ActionBar', 'ResponsiveTable',
];

test('les neuf composants existent et sont réexportés par ui/index.js', () => {
    const index = readFileSync(new URL('../src/components/ui/index.js', import.meta.url), 'utf8');
    for (const c of COMPONENTS) {
        assert.ok(existsSync(new URL(`../src/components/ui/${c}.vue`, import.meta.url)), `${c}.vue manquant`);
        assert.match(index, new RegExp(`${c}\\b`), `${c} non réexporté`);
    }
});

test('les composants ui/ n’utilisent aucune couleur de marque ou d’état en dur', () => {
    for (const c of COMPONENTS) {
        const src = readFileSync(new URL(`../src/components/ui/${c}.vue`, import.meta.url), 'utf8');
        assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/, `${c}: hexadécimal en dur`);
        assert.doesNotMatch(src, /\b(indigo|emerald|slate|rose|amber)-\d{2,3}\b/, `${c}: couleur Tailwind brute`);
    }
});

test('la route du guide de style n’existe qu’en développement', () => {
    const router = readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8');
    assert.match(router, /import\.meta\.env\.DEV/);
    assert.match(router, /\/dev\/styleguide/);
});
