import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
    requestOriginLabel, requestStatusLabel, levelLabel, labNotificationLabel,
} from '../src/utils/labStockLabels.js';

test('origin labels: known -> key, unknown/missing -> raw fallback, no throw', () => {
    for (const o of ['signalement', 'seuil', 'peremption']) {
        assert.deepEqual(requestOriginLabel(o), { key: `labStock.origin.${o}` });
    }
    assert.deepEqual(requestOriginLabel('zzz'), { key: null, raw: 'zzz' });
    assert.deepEqual(requestOriginLabel(undefined), { key: null, raw: '?' });
});

test('status labels', () => {
    for (const s of ['a_commander', 'commande', 'recu', 'annule']) {
        assert.deepEqual(requestStatusLabel(s), { key: `labStock.status.${s}` });
    }
    assert.deepEqual(requestStatusLabel('weird'), { key: null, raw: 'weird' });
    assert.deepEqual(requestStatusLabel(null), { key: null, raw: '?' });
});

test('level labels (null level is legitimate for non-signal requests)', () => {
    assert.deepEqual(levelLabel('bientot_fini'), { key: 'labStock.level.bientot_fini' });
    assert.deepEqual(levelLabel('fini'), { key: 'labStock.level.fini' });
    assert.deepEqual(levelLabel(null), { key: null, raw: '' });
    assert.deepEqual(levelLabel('nope'), { key: null, raw: 'nope' });
});

test('notification: signal by level', () => {
    const r = labNotificationLabel('lab_stock_signal', { product_name: 'Gants', level: 'fini' });
    assert.equal(r.key, 'notifications.lab_stock_signal_fini');
    assert.deepEqual(r.params, { product: 'Gants' });
    const b = labNotificationLabel('lab_stock_signal', { product_name: 'Gants', level: 'bientot_fini' });
    assert.equal(b.key, 'notifications.lab_stock_signal_bientot_fini');
    const u = labNotificationLabel('lab_stock_signal', { product_name: 'Gants', level: 'x' });
    assert.equal(u.key, 'notifications.lab_stock_signal_other');
});

test('notification: low, expiry, received, reminder', () => {
    assert.deepEqual(
        labNotificationLabel('lab_stock_low', { product_name: 'A', quantity: 2, alert_threshold: 5 }),
        { key: 'notifications.lab_stock_low', params: { product: 'A', quantity: 2, threshold: 5 } });
    assert.deepEqual(
        labNotificationLabel('lab_stock_expiry', { product_name: 'A', lot_number: 'L1', days_left: 12 }),
        { key: 'notifications.lab_stock_expiry', params: { product: 'A', lot: 'L1', days: 12 } });
    assert.deepEqual(
        labNotificationLabel('lab_stock_received', { supplier: 'Medi', products: [{}, {}] }),
        { key: 'notifications.lab_stock_received', params: { supplier: 'Medi', count: 2 } });
    assert.deepEqual(
        labNotificationLabel('lab_stock_count_reminder', { days_since: 9 }),
        { key: 'notifications.lab_stock_count_reminder', params: { days: 9 } });
    assert.deepEqual(labNotificationLabel('lab_stock_count_reminder', { days_since: null }),
        { key: 'notifications.lab_stock_count_reminder_never', params: {} });
    assert.deepEqual(labNotificationLabel('lab_stock_count_reminder', {}),
        { key: 'notifications.lab_stock_count_reminder_never', params: {} });
});

test('notification: missing payload and unknown type never throw', () => {
    for (const t of ['lab_stock_signal', 'lab_stock_low', 'lab_stock_expiry', 'lab_stock_received', 'lab_stock_count_reminder']) {
        const r = labNotificationLabel(t, undefined);
        assert.ok(r.key.startsWith('notifications.lab_stock_'));
        assert.equal(typeof r.params, 'object');
    }
    assert.equal(labNotificationLabel('lab_stock_low', undefined).params.product, '?');
    const u = labNotificationLabel('lab_stock_future', {});
    assert.equal(u.key, 'notifications.lab_stock_other');
    assert.deepEqual(u.params, { type: 'lab_stock_future' });
});
