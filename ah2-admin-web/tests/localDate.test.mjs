import { test } from 'node:test';
import assert from 'node:assert/strict';
import { todayLocalISO } from '../src/utils/localDate.js';

test('date locale construite depuis les composants locaux', () => {
    assert.equal(todayLocalISO(new Date(2026, 0, 5, 23, 59)), '2026-01-05');
    assert.equal(todayLocalISO(new Date(2026, 11, 31, 0, 1)), '2026-12-31');
});
test('sans argument : format AAAA-MM-JJ', () => {
    assert.match(todayLocalISO(), /^\d{4}-\d{2}-\d{2}$/);
});
