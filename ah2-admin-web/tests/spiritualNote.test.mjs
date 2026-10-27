import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateNote, emptyNote } from '../src/utils/spiritualNote.js';

const TODAY = '2026-10-28';
const withDate = (d, extra = {}) => ({ ...emptyNote(d), ...extra });

test('la date du jour est acceptee', () => {
    assert.equal(validateNote(withDate(TODAY), TODAY).ok, true);
});
test('demain est refuse', () => {
    const r = validateNote(withDate('2026-10-29'), TODAY);
    assert.equal(r.ok, false);
    assert.equal(r.errors.meeting_date, 'spiritualNotes.err_date_future');
});
test('365 jours en arriere acceptes, 366 refuses', () => {
    assert.equal(validateNote(withDate('2025-10-28'), TODAY).ok, true);
    const r = validateNote(withDate('2025-10-27'), TODAY);
    assert.equal(r.ok, false);
    assert.equal(r.errors.meeting_date, 'spiritualNotes.err_date_old');
});
test('ancienne note : date inchangee acceptee, date modifiee trop ancienne refusee', () => {
    assert.equal(validateNote(withDate('2025-01-01'), TODAY, '2025-01-01').ok, true);
    assert.equal(validateNote(withDate('2025-01-02'), TODAY, '2025-01-01').errors.meeting_date, 'spiritualNotes.err_date_old');
    assert.equal(validateNote(withDate('2026-10-29'), TODAY, '2026-10-29').errors.meeting_date, 'spiritualNotes.err_date_future');
});
test('date absente ou illisible refusee', () => {
    assert.equal(validateNote(withDate(''), TODAY).errors.meeting_date, 'spiritualNotes.err_date_required');
    assert.equal(validateNote(withDate('2026-02-31'), TODAY).ok, false);
});
test('verset de 121 caracteres refuse, 120 accepte', () => {
    assert.equal(validateNote(withDate(TODAY, { verse_reference: 'a'.repeat(121) }), TODAY).errors.verse_reference, 'spiritualNotes.err_verse_long');
    assert.equal(validateNote(withDate(TODAY, { verse_reference: 'a'.repeat(120) }), TODAY).ok, true);
});
test('texte de 5001 caracteres refuse, 5000 accepte', () => {
    assert.equal(validateNote(withDate(TODAY, { content: 'a'.repeat(5001) }), TODAY).errors.content, 'spiritualNotes.err_content_long');
    assert.equal(validateNote(withDate(TODAY, { content: 'a'.repeat(5000) }), TODAY).ok, true);
});
test('une note vide avec une date est acceptee', () => {
    assert.equal(validateNote(emptyNote(TODAY), TODAY).ok, true);
});
test('emptyNote met la date du jour et rien de coche', () => {
    const n = emptyNote(TODAY);
    assert.equal(n.meeting_date, TODAY);
    for (const k of ['counsel', 'prayer', 'verse_read', 'discussion', 'text_given', 'qa', 'no_one_spoke']) assert.equal(n[k], false);
    assert.equal(n.verse_reference, '');
    assert.equal(n.content, '');
});
