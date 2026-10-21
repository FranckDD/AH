import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
    LOCKED_MESSAGE_FR,
    latestRecordKeys,
    isRecordEditable,
    isPrescriptionEditable,
} from '../src/utils/consultationLock.js';

const r = (o) => ({ patient_id: 1, ...o });

test('server flag wins when present', () => {
    const recs = [r({ record_id: 1, consultation_date: '2026-01-01T10:00:00', is_editable: true }),
                  r({ record_id: 2, consultation_date: '2026-02-01T10:00:00', is_editable: false })];
    assert.equal(isRecordEditable(recs[0], recs), true);
    assert.equal(isRecordEditable(recs[1], recs), false);
});

test('latest by date, tie broken by server id', () => {
    const a = r({ server_id: 5, consultation_date: '2026-03-01T10:00:00' });
    const b = r({ server_id: 9, consultation_date: '2026-01-01T10:00:00' });
    const c = r({ server_id: 7, consultation_date: '2026-03-01T10:00:00' });
    const all = [a, b, c];
    assert.equal(isRecordEditable(c, all), true);
    assert.equal(isRecordEditable(a, all), false);
    assert.equal(isRecordEditable(b, all), false); // retroactive date = older, even with a bigger id
});

test('unsynced local consultation (no server id) is the newest', () => {
    const synced = r({ id: 'u1', server_id: 3, consultation_date: '2026-03-01T10:00:00' });
    const local = r({ id: 'u2', server_id: null, consultation_date: null });
    const all = [synced, local];
    assert.equal(isRecordEditable(local, all), true);
    assert.equal(isRecordEditable(synced, all), false);
});

test('patients are independent (patient_id or patient_uuid)', () => {
    const p1 = r({ record_id: 1, consultation_date: '2026-01-01' });
    const p2 = { patient_id: null, patient_uuid: 'pu', id: 'x', consultation_date: '2025-01-01' };
    const all = [p1, p2];
    assert.equal(isRecordEditable(p1, all), true);
    assert.equal(isRecordEditable(p2, all), true);
    assert.equal(latestRecordKeys(all).size, 2);
});

test('prescriptions follow their consultation', () => {
    const old = r({ record_id: 1, id: 'a', consultation_date: '2026-01-01' });
    const neu = r({ record_id: 2, id: 'b', consultation_date: '2026-02-01' });
    const all = [old, neu];
    assert.equal(isPrescriptionEditable({ medical_record_id: 1 }, all), false);
    assert.equal(isPrescriptionEditable({ medical_record_id: 2 }, all), true);
    assert.equal(isPrescriptionEditable({ medical_record_id: 'a' }, all), false); // local uuid link
    assert.equal(isPrescriptionEditable({ medical_record_id: null }, all), true);
    assert.equal(isPrescriptionEditable({ medical_record_id: 99 }, all), true); // unknown locally: server decides
    assert.equal(isPrescriptionEditable({ medical_record_id: 2, is_editable: false }, all), false);
});

test('french message matches backend', () => {
    assert.match(LOCKED_MESSAGE_FR, /plus récente existe pour ce patient/);
});

import { samePatientRecords, isConsultationLockedRejection, buildLockedQuarantineEntry, findLinkedRecord } from '../src/utils/consultationLock.js';

test('local consultation with null patient_id + uuid joins synced rows of the same patient', () => {
    const synced1 = { server_id: 4, patient_id: 7, patient_uuid: 'pu7', consultation_date: '2026-01-01' };
    const synced2 = { server_id: 5, patient_id: 7, consultation_date: '2026-02-01' };
    const local = { id: 'l1', server_id: null, patient_id: null, patient_uuid: 'pu7', consultation_date: null };
    const all = [synced1, synced2, local];
    // regroupement global (union patient_id / patient_uuid)
    assert.deepEqual(all.map((r) => isRecordEditable(r, all)), [false, false, true]);
    // siblings deja filtres par l'appelant
    assert.deepEqual(all.map((r) => isRecordEditable(r, all, { samePatient: true })), [false, false, true]);
    const sib = samePatientRecords({ patient_id: null, patient_uuid: 'pu7' }, all);
    assert.equal(sib.length, 2); // synced1 (uuid) + local ; synced2 sans uuid exclu par uuid...
    const sib2 = samePatientRecords({ patient_id: 7, patient_uuid: 'pu7' }, all);
    assert.equal(sib2.length, 3);
});

test('tie among unsynced local consultations: exactly one newest, deterministic', () => {
    const a = { id: 'aaa', server_id: null, patient_id: 1, consultation_date: null };
    const b = { id: 'bbb', server_id: null, patient_id: 1, consultation_date: null };
    const all = [a, b];
    const flags = all.map((r) => isRecordEditable(r, all));
    assert.equal(flags.filter(Boolean).length, 1);
    assert.deepEqual([...all].reverse().map((r) => isRecordEditable(r, [b, a])), [true, false]);
    const c = { id: 'aaa', server_id: null, patient_id: 1, consultation_date: '2026-06-02T10:00:00' };
    const d = { id: 'zzz', server_id: null, patient_id: 1, consultation_date: '2026-06-01T10:00:00' };
    assert.equal(isRecordEditable(c, [c, d]), true); // local date first, then uuid
});

test('locked rejection detection and quarantine entry keep clinical text', () => {
    const err = { response: { status: 409, data: { detail: LOCKED_MESSAGE_FR } } };
    assert.equal(isConsultationLockedRejection(err), true);
    assert.equal(isConsultationLockedRejection({ response: { status: 409, data: { detail: 'Conflit en base de données' } } }), false);
    const e = buildLockedQuarantineEntry({ table: 'medical_records', op: 'PATCH', id: 'x', opData: { diagnosis: 'd' } },
        { id: 'x', diagnosis: 'd', notes: 'texte clinique', patient_uuid: 'pu' }, err);
    assert.equal(e.kind, 'medical_record_locked');
    assert.equal(e.payload.notes, 'texte clinique');
    assert.equal(e.patientUuid, null);
    assert.equal(buildLockedQuarantineEntry({ table: 'prescriptions', id: 'p' }, null, err).kind, 'prescription_locked');
    assert.equal(findLinkedRecord(null, []), null);
});
