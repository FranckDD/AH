// Garde-fou : aucun caractere "typographique" dans les textes visibles
// (tiret long/demi-cadratin, points de suspension, point median, fleches, puce, emojis).
// Les commentaires sont autorises ; seules les chaines et les gabarits comptent.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const FORBIDDEN = /[—–…·→←↔⇒•☀-➿\u{1F300}-\u{1FAFF}]/u;
// memes caracteres ecrits en entite HTML ou en echappement JS
const FORBIDDEN_ESCAPED = /&(?:mdash|ndash|middot|hellip|bull|rarr|larr|#8212|#8211|#183|#8226);|\\u(?:2014|2013|2026|00b7|2192|2022)/i;
const SRC = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'src');

function flatten(obj, prefix = '', out = {}) {
    for (const [k, v] of Object.entries(obj)) {
        const key = prefix ? `${prefix}.${k}` : k;
        if (v && typeof v === 'object') flatten(v, key, out);
        else out[key] = v;
    }
    return out;
}

function walk(dir, out = []) {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, e.name);
        if (e.isDirectory()) walk(p, out);
        else if (/\.(vue|js)$/.test(e.name) && e.name !== 'i18n.js') out.push(p);
    }
    return out;
}

function stripComments(src) {
    return src
        .replace(/<!--[\s\S]*?-->/g, (m) => m.replace(/[^\n]/g, ' '))
        .replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ' '))
        .split(/\r?\n/)
        .map((l) => (/^\s*(\/\/)?\s*console\./.test(l) ? '' : l.replace(/(^|\s)\/\/.*$/, '$1')))
        .join('\n');
}

test('i18n values contain no forbidden typographic characters', () => {
    const msgs = i18n.global.messages.value;
    const bad = [];
    for (const loc of ['fr', 'en']) {
        for (const [k, v] of Object.entries(flatten(msgs[loc]))) {
            if (typeof v === 'string' && (FORBIDDEN.test(v) || FORBIDDEN_ESCAPED.test(v))) bad.push(`${loc}.${k}: ${v.slice(0, 60)}`);
        }
    }
    assert.deepEqual(bad, []);
});

test('components, views, stores and utils contain no forbidden characters outside comments', () => {
    const bad = [];
    for (const file of walk(SRC)) {
        const lines = stripComments(fs.readFileSync(file, 'utf8')).split('\n');
        lines.forEach((l, i) => {
            if (FORBIDDEN.test(l) || FORBIDDEN_ESCAPED.test(l)) bad.push(`${path.relative(SRC, file)}:${i + 1}: ${l.trim().slice(0, 80)}`);
        });
    }
    assert.deepEqual(bad, []);
});
