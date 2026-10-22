import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TONES, toneClasses, isTone } from '../src/design/tones.js';

test('TONES liste les cinq tonalités', () => {
    assert.deepEqual(TONES, ['danger', 'warning', 'success', 'info', 'neutral']);
});

test('toneClasses renvoie fond, texte et bordure du jeton', () => {
    assert.equal(
        toneClasses('success'),
        'bg-tone-success-bg text-tone-success-text border-tone-success-border',
    );
    for (const t of TONES) {
        const cls = toneClasses(t);
        assert.ok(cls.includes(`bg-tone-${t}-bg`));
        assert.ok(cls.includes(`text-tone-${t}-text`));
        assert.ok(cls.includes(`border-tone-${t}-border`));
    }
});

test('une tonalité inconnue retombe sur neutral, sans exception', () => {
    const neutral = toneClasses('neutral');
    for (const v of ['rose', '', null, undefined, 42, {}, 'DANGER']) {
        assert.equal(toneClasses(v), neutral);
    }
});

test('isTone', () => {
    assert.equal(isTone('danger'), true);
    assert.equal(isTone('rose'), false);
    assert.equal(isTone(undefined), false);
    assert.equal(isTone('toString'), false);
});
