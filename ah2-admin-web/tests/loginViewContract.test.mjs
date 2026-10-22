import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, statSync } from 'node:fs';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

const src = readFileSync(new URL('../src/views/LoginView.vue', import.meta.url), 'utf8');
const msgs = i18n.global.messages.value;

// Liste figée de ce que la page faisait avant la refonte : rien de cela ne doit disparaître.
const CONTRACT = [
    'authStore.login(username.value, password.value)',
    "import { getPostLoginPath } from '@/utils/postLoginRoute'",
    'getRedirectPath(role)',
    'router.push(targetRoute)',
    'err.response.status === 401',
    '@submit.prevent="handleLogin"',
    'v-model="username"',
    'v-model="password"',
    'id="username"',
    'id="password"',
    'showForgotPasswordModal',
    'isLoading',
    'type="submit"',
];

for (const needle of CONTRACT) {
    test(`contrat : « ${needle} » est conservé`, () => {
        assert.ok(src.includes(needle), `« ${needle} » a disparu de LoginView.vue`);
    });
}

test('le champ mot de passe reste de type password par défaut (affichage sur demande)', () => {
    assert.match(src, /showPassword\s*\?\s*'text'\s*:\s*'password'/);
});

test('l’identifiant est focalisé au chargement', () => {
    assert.match(src, /usernameInput\.value\?\.focus\(\)/);
});

test('aucune couleur de marque ou d’état en dur', () => {
    assert.doesNotMatch(src, /#[0-9a-fA-F]{6}\b/);
    assert.doesNotMatch(src, /\b(green|red|gray|indigo|emerald|slate)-\d{2,3}\b/);
});

test('maquette : photo du médecin et logo A.H2 légers (< 100 Ko), « se souvenir de moi » absent (aucun comportement inventé)', () => {
    for (const f of ['medecin.webp', 'ah2-logo.webp']) {
        const size = statSync(new URL(`../src/assets/login/${f}`, import.meta.url)).size;
        assert.ok(size > 0 && size < 100 * 1024, `${f} : ${size} octets`);
        assert.ok(src.includes(`@/assets/login/${f}`), `${f} non utilisé par la page`);
    }
    assert.doesNotMatch(src, /type="checkbox"/);
});

test('le conteneur .app-refonte est posé', () => {
    assert.match(src, /app-refonte/);
});

// Textes d'avant la refonte, conservés mot pour mot en français (le texte de « mot de passe oublié » est imposé).
const FR_FROZEN = {
    'loginPage.forgotMessage': "Veuillez vous rapprocher de l'administration.",
    'loginPage.errorInvalid': 'Identifiants ou mot de passe incorrects. Veuillez vérifier.',
    'loginPage.errorGeneric': 'Une erreur inattendue est survenue. Le serveur est peut-être inaccessible.',
    'loginPage.forgot': 'Mot de passe oublié ?',
    'loginPage.submit': 'Se connecter',
    'loginPage.submitting': 'Connexion en cours...',
    'loginPage.username': 'Identifiant',
    'loginPage.password': 'Mot de passe',
};

const pick = (obj, path) => path.split('.').reduce((o, p) => o?.[p], obj);

for (const [key, text] of Object.entries(FR_FROZEN)) {
    test(`texte français inchangé : ${key}`, () => {
        assert.equal(pick(msgs.fr, key), text);
    });
}

const NEW_KEYS = [
    'title', 'heroTitle', 'heroOrg', 'heroAddress', 'subtitle', 'copyright', 'usernamePlaceholder', 'passwordPlaceholder',
    'showPassword', 'hidePassword', 'errorPrefix', 'close', 'security',
    ...Object.keys(FR_FROZEN).map((k) => k.replace('loginPage.', '')),
];

test('toutes les clés loginPage.* utilisées existent en FR et EN', () => {
    for (const locale of ['fr', 'en']) {
        for (const k of NEW_KEYS) {
            const v = msgs[locale].loginPage?.[k];
            assert.equal(typeof v, 'string', `${locale}.loginPage.${k} manquante`);
            assert.ok(v.length > 0);
        }
    }
});

test('chaque clé loginPage.* référencée dans la vue existe', () => {
    const used = [...src.matchAll(/loginPage\.([a-zA-Z]+)/g)].map((m) => m[1]);
    assert.ok(used.length > 0);
    for (const k of new Set(used)) {
        assert.equal(typeof msgs.fr.loginPage?.[k], 'string', `loginPage.${k} absente (fr)`);
        assert.equal(typeof msgs.en.loginPage?.[k], 'string', `loginPage.${k} absente (en)`);
    }
});
