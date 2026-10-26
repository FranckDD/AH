import { test } from 'node:test';
import assert from 'node:assert/strict';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const msgs = i18n.global.messages.value;

test('le comptage parle de la periode depuis la derniere cloture, pas d aujourd hui', () => {
    for (const l of ['fr', 'en']) {
        const help = msgs[l].cashClosure.field_operator_help;
        assert.ok(!/aujourd|today/i.test(help), `${l} : ${help}`);
        assert.ok(/derni|last/i.test(help), help);
        assert.ok(msgs[l].cashClosure.last_closed.includes('{date}'));
        assert.ok(/p.riode|period/i.test(msgs[l].cashClosure.last_closed));
    }
});
