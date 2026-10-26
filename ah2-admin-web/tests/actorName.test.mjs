import { test } from 'node:test';
import assert from 'node:assert/strict';
import { actorLabel } from '../src/utils/actorName.js';

test('le nom complet est prioritaire', () => {
    assert.equal(actorLabel('Marie Dupont', 7), 'Marie Dupont');
});
test('sans nom : #id', () => {
    assert.equal(actorLabel(null, 7), '#7');
    assert.equal(actorLabel(undefined, 0), '#0');
});
test('sans nom ni id : tiret', () => {
    assert.equal(actorLabel(null, null), '-');
    assert.equal(actorLabel(undefined, undefined), '-');
});
