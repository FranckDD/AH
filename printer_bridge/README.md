# Service pont impression POS

Service Python autonome qui tourne sur le poste secrétariat (pas sur le serveur backend). Reçoit le contenu JSON d'un ticket depuis le frontend et l'imprime via ESC/POS.

## Installation (développement, avec l'émulateur POS Windows)

1. `pip install -r requirements.txt`
2. Installer/lancer "POS Printer Emulator for Windows" — il s'enregistre comme une imprimante Windows classique.
3. Copier `config.example.json` vers `config.json`, renseigner `printer_name` avec le nom exact affiché dans les imprimantes Windows, et `token` avec la valeur générée dans Configuration Système > Régénérer.
4. `python server.py`

## Bascule vers une vraie imprimante USB

Dans `config.json`, changer `connection_type` à `"usb"` et renseigner `vendor_id`/`product_id` (visibles dans le Gestionnaire de périphériques Windows) — aucun changement de code nécessaire.

## Tests

`python -m pytest tests/ -v` — utilise `escpos.printer.Dummy`, aucune imprimante ni émulateur nécessaire.
