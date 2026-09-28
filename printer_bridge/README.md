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
