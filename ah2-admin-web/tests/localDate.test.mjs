import { test } from 'node:test';
import assert from 'node:assert/strict';
import { todayLocalISO } from '../src/utils/localDate.js';

test('date locale construite depuis les composants locaux', () => {
    assert.equal(todayLocalISO(new Date(2026, 0, 5, 23, 59)), '2026-01-05');
    assert.equal(todayLocalISO(new Date(2026, 11, 31, 0, 1)), '2026-12-31');
});
test('00:30 heure locale : date locale (pas la veille UTC)', () => {
    assert.equal(todayLocalISO(new Date(2026, 9, 24, 0, 30)), '2026-10-24');
});

// Ecrans caisse/finance : aucune date seule derivee de toISOString (decalage UTC).
import { readFileSync } from 'node:fs';
const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
for (const file of [
    'src/views/modules/caisse/DiscountRequestsHistory.vue',
    'src/stores/caisseStore.js',
    'src/components/finance/FinanceModal.vue',
]) {
    test(`${file} : pas de toISOString pour une date seule`, () => {
        const src = read(file);
        assert.doesNotMatch(src, /toISOString\(\)\.(slice|substring|split)/);
        assert.match(src, /import \{ todayLocalISO \} from '@\/utils\/localDate'/);
    });
}
test('sans argument : format AAAA-MM-JJ', () => {
    assert.match(todayLocalISO(), /^\d{4}-\d{2}-\d{2}$/);
});
