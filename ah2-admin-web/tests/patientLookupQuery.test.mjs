import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildPatientLookupQuery, mapLookupRow } from '../src/utils/patientLookupQuery.js';

test('escapes % and _ and backslash, lowercases', () => {
    const { params } = buildPatientLookupQuery('  Ab%_\\c ');
    assert.deepEqual(params, ['%ab\\%\\_\\\\c%', '%ab\\%\\_\\\\c%', '%ab\\%\\_\\\\c%']);
});

test('sql searches first/last name and code, escape clause, limit 8', () => {
    const { sql } = buildPatientLookupQuery('x');
    assert.match(sql, /FROM patients_lookup/);
    assert.match(sql, /LOWER\(first_name\) LIKE \? ESCAPE '\\'/);
    assert.match(sql, /LOWER\(last_name\) LIKE \?/);
    assert.match(sql, /LOWER\(code_patient\) LIKE \?/);
    assert.match(sql, /LIMIT 8/);
    assert.doesNotMatch(sql, /is_deleted/);
});

test('mapLookupRow returns REST shape with boolean is_staff', () => {
    const r = mapLookupRow({ id: '5', patient_id: 5, code_patient: 'P5', first_name: 'A', last_name: 'B', contact_phone: 'x', is_staff: 1 });
    assert.deepEqual(r, { patient_id: 5, code_patient: 'P5', first_name: 'A', last_name: 'B', is_staff: true });
    assert.equal(mapLookupRow({ is_staff: 0 }).is_staff, false);
});

test('mapLookupRow keeps NULL is_staff as null (not yet replicated), not false', () => {
    assert.equal(mapLookupRow({ is_staff: null }).is_staff, null);
    assert.equal(mapLookupRow({}).is_staff, null);
    assert.equal(mapLookupRow({ is_staff: 0 }).is_staff, false);
    assert.equal(mapLookupRow({ is_staff: 1 }).is_staff, true);
});
