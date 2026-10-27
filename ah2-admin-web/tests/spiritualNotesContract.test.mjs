import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseMenuItems } from './helpers_mainLayoutMenu.mjs';
import { parseRoutes } from './helpers_routerRoutes.mjs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;
const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');
const view = read('views/modules/spiritual/SpiritualNotes.vue');
const form = read('components/spiritual/SpiritualNoteForm.vue');
const gateway = read('services/SpiritualNoteGateway.js');

const ROLES3 = ['SpiritualCounsellor', 'admin', 'promoteur'];

test('menu : une seule entree, reservee aux trois roles', () => {
    const items = parseMenuItems().filter((i) => i.path === '/dashboard/spiritual-notes');
    assert.equal(items.length, 1);
    assert.deepEqual([...items[0].roles].sort(), [...ROLES3].sort());
    assert.equal(items[0].labelKey, 'spiritualNotes.menu');
});

test('route : /dashboard/spiritual-notes pour les trois roles seulement', () => {
    const r = parseRoutes().filter((x) => x.path === '/dashboard/spiritual-notes');
    assert.equal(r.length, 1);
    assert.deepEqual([...r[0].roles].sort(), [...ROLES3].sort());
});

test('boutons d ecriture conditionnes au role et a can_edit', () => {
    assert.match(view, /const canWrite = computed\(\(\) => authStore\.hasRole\(\['SpiritualCounsellor'\]\)\)/);
    assert.match(view, /<div v-if="canWrite" class="flex">/);
    assert.match(view, /v-if="canWrite && n\.can_edit"/);
    assert.match(view, /function openEdit\(n\) \{ if \(!canWrite\.value \|\| !n\.can_edit\) return;/);
    assert.match(view, /async function askDelete\(n\) \{\s*if \(deleting\.value \|\| !canWrite\.value \|\| !n\.can_edit\) return;/);
    assert.match(view, /window\.confirm\(t\('spiritualNotes\.confirm_delete'/);
    // les boutons Modifier / Supprimer n'existent que dans le bloc garde
    for (const m of view.matchAll(/<AppButton[^>]*@click="(openEdit|askDelete)\(n\)"/g)) {
        const before = view.slice(0, m.index);
        assert.ok(before.lastIndexOf('v-if="canWrite && n.can_edit"') > before.lastIndexOf('</li>'));
    }
});

test('passerelle : les quatre appels sur /spiritual-notes', () => {
    assert.match(gateway, /api\.get\('\/spiritual-notes\/'/);
    assert.match(gateway, /api\.post\('\/spiritual-notes\/'/);
    assert.match(gateway, /api\.put\(`\/spiritual-notes\/\$\{id\}`/);
    assert.match(gateway, /api\.delete\(`\/spiritual-notes\/\$\{id\}`/);
});

function keysUsed(src) {
    return [...src.matchAll(/['"`](spiritualNotes\.[a-z_A-Z]+)/g)].map((m) => m[1]);
}
const flat = (o) => Object.keys(o);

test('cles i18n FR et EN identiques et toutes presentes', () => {
    const fr = msgs.fr.spiritualNotes;
    const en = msgs.en.spiritualNotes;
    assert.ok(fr && en);
    assert.deepEqual(flat(fr).sort(), flat(en).sort());
    const used = new Set([...keysUsed(view), ...keysUsed(form), ...keysUsed(read('utils/spiritualNote.js'))]);
    for (const k of used) {
        if (k.endsWith('_')) continue; // prefixe de cle dynamique (item_ + champ)
        const name = k.replace('spiritualNotes.', '');
        assert.ok(name in fr, `cle manquante FR: ${k}`);
        assert.ok(name in en, `cle manquante EN: ${k}`);
    }
    for (const f of ['counsel', 'prayer', 'verse_read', 'discussion', 'text_given', 'qa']) assert.ok(`item_${f}` in fr);
    assert.equal(en.last_note, 'Last note');
    assert.equal(en.no_one_spoke, 'People did not want to talk');
    assert.equal(en.menu, 'Spiritual notes');
    assert.equal(fr.menu, 'Notes spirituelles');
});

test('aucun caractere typographique interdit dans les nouveaux textes', () => {
    const FORBIDDEN = /[\u2014\u2013\u2026\u00b7\u2192\u2190\u2022]/;
    for (const lang of ['fr', 'en']) {
        for (const [k, v] of Object.entries(msgs[lang].spiritualNotes)) assert.doesNotMatch(v, FORBIDDEN, `${lang}.${k}`);
    }
    for (const src of [view, form]) assert.doesNotMatch(src, FORBIDDEN);
});
