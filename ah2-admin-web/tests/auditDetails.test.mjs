import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { auditSummary } from '../src/utils/auditDetails.js';

test('details explicites gardes', () => {
    assert.equal(auditSummary({ new_values: { details: 'Prix 1 -> 2' } }), 'Prix 1 -> 2');
});
test('resume avant -> apres sans details', () => {
    assert.equal(auditSummary({ old_values: { prix: 1000 }, new_values: { prix: 1500 } }), 'prix : 1000 -> 1500');
});
test('valeurs nouvelles seules et cles sensibles masquees', () => {
    assert.equal(auditSummary({ new_values: { status: 'APPROVED', password: 'x' } }), 'status : APPROVED');
});
test('rien a dire : tiret', () => {
    assert.equal(auditSummary({}), '-');
});
test('l ecran utilise le resume', () => {
    const v = readFileSync(new URL('../src/views/modules/tech/SystemLogs.vue', import.meta.url), 'utf8');
    assert.ok(v.includes('auditSummary(act)'));
});
