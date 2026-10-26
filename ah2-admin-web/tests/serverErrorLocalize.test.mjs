import { test } from 'node:test';
import assert from 'node:assert/strict';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');
const { RULES, localizeDetail, localizeAxiosError } = await import('../src/utils/serverErrorLocalize.js');

const g = i18n.global;
const tIn = (lang) => (k, p) => g.t(k, p, { locale: lang });
const teIn = (lang) => (k) => g.te(k, lang);

test('every rule key exists in both languages', () => {
    for (const lang of ['fr', 'en']) {
        for (const [, key] of RULES) assert.ok(g.te(`serverErrors.${key}`, lang), `${lang}: ${key}`);
        for (const key of ['forbidden', 'not_found', 'unauthorized']) assert.ok(g.te(`serverErrors.${key}`, lang));
    }
});

test('known French server messages are translated in English only', () => {
    const cases = [
        ['Ce dossier a déjà été pris en charge.', 409, /already been taken over/],
        ["L'ancien mot de passe est incorrect", 400, /password .* incorrect/i],
        ['Cette ligne de facture a deja ete recue au laboratoire.', 409, /already been received/],
        ['Cet achat est annule.', 409, /cancelled/],
        ['Une cloture de caisse est deja en cours. Reessayez.', 409, /already in progress/],
        ['Cette demande ne vous est pas adressée.', 403, /not addressed to you/],
        ['Patient non trouvé', 404, /not found/i],
    ];
    for (const [fr, status, re] of cases) {
        assert.match(localizeDetail(fr, status, 'en', tIn('en'), teIn('en')), re, fr);
        assert.equal(localizeDetail(fr, status, 'fr', tIn('fr'), teIn('fr')), undefined, `fr keeps ${fr}`);
    }
});

test('unknown text and validation lists are left alone', () => {
    assert.equal(localizeDetail('Texte inconnu du serveur', 400, 'en', tIn('en'), teIn('en')), undefined);
    assert.equal(localizeDetail([{ loc: ['body', 'x'], msg: 'Field required' }], 422, 'en', tIn('en'), teIn('en')), undefined);
});

test('English FastAPI defaults are translated in French', () => {
    assert.match(localizeDetail('Forbidden', 403, 'fr', tIn('fr'), teIn('fr')), /droit/);
    assert.match(localizeDetail('Not Found', 404, 'fr', tIn('fr'), teIn('fr')), /introuvable/);
});

test('code objects: known code translated, unknown kept (nurse shift pattern untouched)', () => {
    const t = tIn('en'); const te = teIn('en');
    assert.equal(localizeDetail({ code: 'shift_night_exclusive', message: 'x' }, 409, 'en', t, te), undefined);
    assert.equal(localizeDetail({ code: 'not_found', message: 'x' }, 404, 'en', t, te), 'Item not found.');
});

test('localizeAxiosError rewrites detail and keeps the original', () => {
    const err = { response: { status: 409, data: { detail: 'Cet achat est annule.' } } };
    localizeAxiosError(err, 'en', tIn('en'), teIn('en'));
    assert.equal(err.response.data.detail, 'This purchase is cancelled.');
    assert.equal(err.response.data.detail_raw, 'Cet achat est annule.');
    assert.doesNotThrow(() => localizeAxiosError({ message: 'network' }, 'en', tIn('en'), teIn('en')));
});

test('Forbidden page has no hard-coded French', async () => {
    const fs = await import('node:fs');
    const src = fs.readFileSync(new URL('../src/views/errors/Forbidden.vue', import.meta.url), 'utf8');
    assert.doesNotMatch(src, /Accès|Désolé|Tableau de bord|Utilisateur/);
});
