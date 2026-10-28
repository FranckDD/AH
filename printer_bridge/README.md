# Service pont impression POS

Service Python autonome qui tourne sur le poste secrétariat (pas sur le serveur backend). Reçoit le contenu JSON d'un ticket depuis le frontend et l'imprime via ESC/POS.

## Serveur HTTP

`server.py` expose deux routes sur `http://127.0.0.1:<port>` (port configuré dans `config.json`, `9123` par défaut) :

- `GET /health` — public, aucune authentification, utilisé par le frontend pour détecter si le pont tourne.
- `POST /print` — protégé par l'en-tête `X-Print-Token`, comparé au `token` de `config.json`. Rejette avec `401` toute requête sans jeton ou avec un jeton incorrect, **avant** tout accès à l'imprimante. Retourne `503` si l'imprimante est injoignable (ex. non branchée, nom d'imprimante Windows incorrect), `500` en cas d'échec pendant le rendu/l'envoi du ticket.

Ce jeton existe spécifiquement pour empêcher qu'une page web ouverte dans un autre onglet du navigateur du poste secrétariat ne déclenche une impression silencieuse sur ce port local partagé.

## Installation (développement, avec l'émulateur POS Windows)

1. `pip install -r requirements.txt`
2. Installer/lancer "POS Printer Emulator for Windows" — il s'enregistre comme une imprimante Windows classique.
3. Copier `config.example.json` vers `config.json`, renseigner `printer_name` avec le nom exact affiché dans les imprimantes Windows, et `token` avec la valeur générée dans Configuration Système > Régénérer.
4. `python server.py`

## Bascule vers une vraie imprimante USB

Dans `config.json`, changer `connection_type` à `"usb"` et renseigner `vendor_id`/`product_id` (visibles dans le Gestionnaire de périphériques Windows) — aucun changement de code nécessaire.

## Tests

`python -m pytest tests/ -v` — utilise `escpos.printer.Dummy` et des mocks (`unittest.mock.patch`) pour `config`/l'imprimante, aucune imprimante ni émulateur nécessaire.

## Vérification manuelle contre l'émulateur

Avec l'émulateur POS Windows installé et `config.json` renseigné (nom d'imprimante exact, jeton copié depuis Configuration Système) :

```bash
cd printer_bridge && python server.py
```

Dans un autre terminal :

```bash
curl -X POST http://localhost:9123/print -H "X-Print-Token: <le jeton>" -H "Content-Type: application/json" -d @tests/sample_ticket.json
```

La fenêtre de l'émulateur doit afficher le ticket rendu (en-tête, articles, totaux, bloc réduction si `discount` est renseigné dans le JSON).

## Utilisation depuis le site de production (HTTPS)

Le site de production (`https://app.ahandtohumanity-ngo.org`) est en HTTPS alors que le pont écoute en HTTP sur `127.0.0.1`. Chrome et Edge autorisent cet appel (127.0.0.1 est considéré comme une origine "potentiellement fiable", donc pas de blocage de contenu mixte) à deux conditions :

1. **CORS** : l'origine exacte du site doit figurer dans `allowed_origins` de `config.json` (jamais `*` : une entrée `*` est ignorée et signalée dans les logs).
2. **Private Network Access (PNA)** : pour le preflight `OPTIONS` qui porte `Access-Control-Request-Private-Network: true`, le pont répond `Access-Control-Allow-Private-Network: true`, uniquement pour une origine autorisée (géré dans `server.py`, rien à configurer).

Dans `config.json` du poste secrétariat, ajouter l'origine de production à côté des origines de développement :

```json
"allowed_origins": ["http://localhost:4173", "http://localhost:5173", "https://app.ahandtohumanity-ngo.org"]
```

Si la clé `allowed_origins` est absente, seules les deux origines localhost sont autorisées (le domaine de production n'est jamais ajouté implicitement). Redémarrer le pont après modification.

Le jeton `X-Print-Token` reste la vraie protection : CORS/PNA limitent seulement quelles pages peuvent tenter l'appel.

### Vérifier dans Chrome

1. Ouvrir le site de production, F12 > onglet **Network**.
2. Déclencher une impression (ou rechargement de la page caisse qui interroge `/health`).
3. Repérer la requête `OPTIONS` vers `127.0.0.1:9123` : ses en-têtes de réponse doivent contenir `Access-Control-Allow-Origin: https://app.ahandtohumanity-ngo.org` et `Access-Control-Allow-Private-Network: true`. La requête `POST /print` suivante doit répondre `200`.
4. Si la requête est "blocked" ou en erreur CORS : vérifier l'orthographe exacte de l'origine (schéma, pas de `/` final) et que le pont a été redémarré.

### Compatibilité navigateurs

- Chrome et Edge : PNA appliqué, ce mécanisme est nécessaire et suffisant.
- Firefox : n'applique pas encore PNA ; l'appel fonctionne dès que CORS est correct.
- Safari : non garanti (traitement de `127.0.0.1` depuis une page HTTPS différent) ; utiliser Chrome ou Edge sur le poste secrétariat.
