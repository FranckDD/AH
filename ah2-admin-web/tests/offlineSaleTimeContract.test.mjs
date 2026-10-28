import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const connector = readFileSync(join(root, 'src/powersync-client/DossierConnector.js'), 'utf8');
const store = readFileSync(join(root, 'src/stores/caisseStore.js'), 'utf8');
const gateway = readFileSync(join(root, 'src/services/CaisseGateway.js'), 'utf8');

function block(src, marker) {
  const i = src.indexOf(marker);
  assert.ok(i >= 0, marker);
  return src.slice(i, i + 2500);
}

test('caisse:PUT envoie paid_at lu sur la ligne locale', () => {
  const b = block(connector, "case 'caisse:PUT'");
  assert.match(b, /paid_at:\s*await readLocalColumn\(database, 'caisse', op\.id, 'paid_at'/);
  assert.match(connector, /SELECT \$\{column\} AS v FROM \$\{table\} WHERE id = \?/);
});

test('versement hors ligne envoie payment_date lu sur la ligne locale', () => {
  const b = block(connector, "case 'paiement_echelonne:PUT'");
  assert.match(b, /payment_date:\s*await readLocalColumn\(database, 'paiement_echelonne'/);
});

test('la vente locale ecrit toujours paid_at en ISO UTC', () => {
  assert.match(store, /new Date\(\)\.toISOString\(\)/);
});

test('le chemin en ligne (gateway) n envoie pas paid_at', () => {
  assert.doesNotMatch(gateway, /paid_at|payment_date/);
});
