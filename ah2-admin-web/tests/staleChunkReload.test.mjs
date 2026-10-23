// Rechargement apres un build perime (chunk introuvable) : la base locale OPFS est fermee avant de recharger,
// sinon l'ancienne page garde le fichier ouvert et PowerSync echoue (« Access Handles cannot be created »).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const router = readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8');
const block = router.slice(router.indexOf('router.onError'), router.indexOf('router.afterEach'));

test('chunk perime : la base locale est fermée avant le rechargement de la page', () => {
    assert.match(block, /import\('@\/powersync-client\/client'\)/);
    assert.match(block, /\.then\(\(\{ db \}\) => db\.close\(\)\)/);
    assert.match(block, /\.finally\(\(\) => window\.location\.assign\(to\.fullPath\)\)/);
});

test('chunk perime : le rechargement garde sa protection contre les boucles et ne se déclenche que pour un module introuvable', () => {
    assert.match(block, /Failed to fetch dynamically imported module\|Importing a module script failed/);
    assert.match(block, /if \(sessionStorage\.getItem\(RELOAD_FLAG\)\) \{/);
    assert.match(block, /sessionStorage\.setItem\(RELOAD_FLAG, '1'\);/);
});

test('le rechargement ne dépend pas de la fermeture : un échec de fermeture recharge quand même', () => {
    assert.match(block, /\.catch\(\(\) => \{\}\)\s*\.finally/);
});
