import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const { localizeDetail } = await import('../src/utils/serverErrorLocalize.js');
const { readBlobDetail } = await import('../src/utils/serverError.js');

const g = i18n.global;
const MSG = 'Numero de dossier non attribue : synchronisez le poste puis reessayez';

test('the error detail of a blob response is read back', async () => {
    const blob = new Blob([JSON.stringify({ detail: MSG })], { type: 'application/json' });
    assert.equal(await readBlobDetail({ response: { data: blob } }), MSG);
    assert.equal(await readBlobDetail({ response: { data: new Blob(['not json']) } }), undefined);
    assert.equal(await readBlobDetail({ response: { data: { detail: 'x' } } }), 'x');
    assert.equal(await readBlobDetail({}), undefined);
});

test('both PDF downloads of the lab store show the server refusal', () => {
    const src = readFileSync(new URL('../src/stores/labStore.js', import.meta.url), 'utf8');
    assert.equal((src.match(/await pdfFailureMessage\(err,/g) || []).length, 2);
    assert.match(src, /notifyText\(this\.error\)/);
});
