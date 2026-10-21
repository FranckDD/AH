import { test } from 'node:test';
import assert from 'node:assert/strict';
import { monthRange, buildMonthBars, sumAmounts } from '../src/utils/labStockExpenses.js';

test('monthRange covers every month between from and to, across years', () => {
    assert.deepEqual(monthRange('2025-11-15', '2026-02-01'), ['2025-11', '2025-12', '2026-01', '2026-02']);
    assert.deepEqual(monthRange('2026-03-01', '2026-03-31'), ['2026-03']);
    assert.deepEqual(monthRange('2026-05-01', '2026-03-01'), []);
    assert.deepEqual(monthRange(null, '2026-03-01'), []);
});

test('buildMonthBars fills empty months with 0 and computes proportional widths', () => {
    const bars = buildMonthBars([{ month: '2026-01', total: '200.00' }, { month: '2026-03', total: 50 }],
        '2026-01-01', '2026-04-10');
    assert.deepEqual(bars.map((b) => b.month), ['2026-01', '2026-02', '2026-03', '2026-04']);
    assert.deepEqual(bars.map((b) => b.total), [200, 0, 50, 0]);
    assert.deepEqual(bars.map((b) => b.pct), [100, 0, 25, 0]);
    assert.equal(bars[1].empty, true);
    assert.equal(bars[0].empty, false);
});

test('a tiny non-zero month stays visible (min width), all-zero gives zero widths', () => {
    const bars = buildMonthBars([{ month: '2026-01', total: 10000 }, { month: '2026-02', total: 1 }], '2026-01-01', '2026-02-01');
    assert.equal(bars[1].pct, 2);
    const none = buildMonthBars([], '2026-01-01', '2026-02-01');
    assert.deepEqual(none.map((b) => b.pct), [0, 0]);
});

test('months returned by the server outside the range are still shown, garbage totals become 0', () => {
    const bars = buildMonthBars([{ month: '2025-12', total: 'abc' }, { month: '2026-01', total: 10 }], '2026-01-01', '2026-01-01');
    assert.deepEqual(bars.map((b) => [b.month, b.total]), [['2025-12', 0], ['2026-01', 10]]);
});

test('sumAmounts adds decimal strings without float drift', () => {
    assert.equal(sumAmounts([{ total: '0.10' }, { total: '0.20' }]), 0.3);
    assert.equal(sumAmounts([]), 0);
});
