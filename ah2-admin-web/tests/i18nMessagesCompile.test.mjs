import { test } from 'node:test';
import assert from 'node:assert/strict';
import { baseCompile } from '@intlify/message-compiler';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

function flatten(obj, prefix = '', out = {}) {
    for (const [k, v] of Object.entries(obj)) {
        const key = prefix ? `${prefix}.${k}` : k;
        if (v && typeof v === 'object') flatten(v, key, out);
        else out[key] = v;
    }
    return out;
}

const msgs = i18n.global.messages.value;
const fr = flatten(msgs.fr);
const en = flatten(msgs.en);

for (const [locale, flat] of [['fr', fr], ['en', en]]) {
    test(`every ${locale} message compiles without syntax error`, () => {
        const errors = [];
        for (const [key, src] of Object.entries(flat)) {
            if (typeof src !== 'string') continue;
            try {
                baseCompile(src, { onError: (e) => { throw e; }, mode: 'arrow' });
            } catch (e) {
                errors.push(`${key}: ${e.message}`);
            }
        }
        assert.deepEqual(errors, []);
    });
}

test('fr and en expose the same keys', () => {
    const onlyFr = Object.keys(fr).filter((k) => !(k in en));
    const onlyEn = Object.keys(en).filter((k) => !(k in fr));
    assert.deepEqual({ onlyFr, onlyEn }, { onlyFr: [], onlyEn: [] });
});

test('runtime smoke: params and plural in both locales', () => {
    const t = i18n.global.t;
    for (const locale of ['fr', 'en']) {
        const r = t('common.welcome', {}, { locale });
        assert.ok(r && r !== 'common.welcome');
    }
    assert.equal(t('stockAdjust.current_stock_n', { n: 3 }, { locale: 'fr' }), 'Stock actuel : 3');
    assert.equal(t('stockAdjust.current_stock_n', { n: 3 }, { locale: 'en' }), 'Current stock: 3');
    const k = 'lab.patient_table.abnormal_count';
    assert.equal(t(k, { n: 1 }, { plural: 1, locale: 'fr' }), '1 anormal');
    assert.equal(t(k, { n: 2 }, { plural: 2, locale: 'fr' }), '2 anormaux');
    assert.equal(t(k, { n: 2 }, { plural: 2, locale: 'en' }), '2 abnormal');
});
