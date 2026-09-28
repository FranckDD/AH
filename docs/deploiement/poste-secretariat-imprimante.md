# Installer l'impression de tickets sur le poste secrétariat

Ce document liste tout ce qu'il faut installer et configurer sur l'ordinateur
**de la secrétaire** (un poste qui n'existe pas encore — à faire le jour où
il sera acheté et installé) pour que les tickets de caisse s'impriment
automatiquement (en ligne comme hors ligne). **Rien de ce document ne
concerne ta machine actuelle** (poste de développement) — les deux
n'ont rien à voir : ci-dessous, "le poste" veut toujours dire le futur
poste de la secrétaire, jamais celui-ci.

Le service qui fait l'impression s'appelle le **pont d'impression**
(`printer_bridge/`) : un petit programme qui tourne en arrière-plan sur ce
poste (jamais sur le serveur), reçoit le contenu du ticket depuis le
navigateur, et l'envoie à l'imprimante.

**Ce qu'il faut sur ce poste** : uniquement Python (étape 2) — pas de Node,
pas de git, pas d'outil de développement. C'est le même besoin qu'installer
n'importe quel petit logiciel : la secrétaire n'a besoin de rien d'autre que
l'application web AH2 (dans son navigateur, comme d'habitude) et ce service
qui tourne discrètement à côté.

**Deux adresses différentes, à ne pas confondre** (source de confusion la
plus probable en suivant ce guide) :
- **L'adresse du pont d'impression** (`http://localhost:9123`, utilisée par
  le navigateur pour lui envoyer le ticket) — reste **toujours**
  `localhost`, même en production, sur n'importe quel poste. Ce n'est pas
  un oubli : le pont tourne toujours sur le MÊME poste que le navigateur qui
  s'en sert, donc "cette machine-ci" (`localhost`) est la bonne adresse
  partout, pour toujours. Rien à changer ici au déploiement.
- **L'adresse de l'application web AH2** (`allowed_origins`, étape 5) — elle,
  au contraire, **change forcément** au déploiement : ce n'est plus
  `localhost:xxxx` (adresse de développement) mais la vraie adresse publique
  de l'application (ex. `https://ah2.exemple.org`), celle que la secrétaire
  tape ou a en favori dans son navigateur. C'est la seule adresse à adapter
  dans ce document.

## 1. Matériel nécessaire

Une imprimante thermique de tickets (format 80mm), compatible ESC/POS —
c'est le standard de fait pour ce type d'imprimante, presque tous les
modèles du marché le sont. Deux façons courantes de la brancher :

- **USB** (la plus courante) — installée comme une imprimante Windows
  classique, ou reconnue directement par son identifiant USB.
- **Réseau (Ethernet/Wi-Fi)** — a une adresse IP sur le réseau du secrétariat.

Si le matériel n'est pas encore choisi, privilégier une imprimante USB
"plug-and-play" (ex. gamme Epson TM-T20/TM-T88, ou équivalent générique
ESC/POS) : c'est la configuration la plus simple à installer et dépanner.

## 2. Installer Python

1. Installer **Python 3.11 ou plus récent** (https://python.org/downloads) —
   cocher "Add python.exe to PATH" pendant l'installation.
2. Vérifier : ouvrir une invite de commande et taper `python --version`.

## 3. Copier et installer le pont d'impression

1. Copier le dossier `printer_bridge/` du projet sur ce poste (ex.
   `C:\AH2\printer_bridge`).
2. Ouvrir une invite de commande dans ce dossier et lancer :
   ```
   pip install -r requirements.txt
   ```

## 4. Brancher l'imprimante

### Cas A — USB, avec pilote Windows classique
Installer le pilote fourni par le fabricant de l'imprimante (souvent une
imprimante "virtuelle" qui apparaît dans *Windows > Imprimantes et
scanners*). Noter le **nom exact** tel qu'il apparaît dans cette liste.

### Cas B — USB, sans pilote Windows (accès direct)
Ouvrir le *Gestionnaire de périphériques* Windows, trouver l'imprimante,
onglet *Détails > ID matériel* — noter le `VID_xxxx` (vendor ID) et
`PID_xxxx` (product ID).

### Cas C — Réseau (Ethernet/Wi-Fi)
Noter l'adresse IP de l'imprimante (souvent affichée sur un ticket de test
imprimé en maintenant un bouton de l'imprimante à l'allumage). Le port est
presque toujours `9100` sauf indication contraire du fabricant.

## 5. Configurer le pont

1. Dans `printer_bridge/`, copier `config.example.json` vers `config.json`.
2. Remplir selon le cas retenu à l'étape 4 :

   | Champ | Cas A (USB, pilote) | Cas B (USB, direct) | Cas C (réseau) |
   |---|---|---|---|
   | `connection_type` | `"win32raw"` | `"usb"` | `"network"` |
   | `printer_name` | nom exact noté à l'étape 4 | — | — |
   | `vendor_id` / `product_id` | — | valeurs notées (en entier, ex. `0x04b8` → `1208`) | — |
   | `printer_host` / `printer_port` | — | — | IP notée / `9100` |
   | `profile` | `"TM-T88V"` (convient à la plupart des imprimantes 80mm génériques — ne pas modifier sauf besoin identifié) | idem | idem |

   `allowed_origins` : **mettre l'adresse exacte de l'application web AH2
   telle qu'elle apparaît dans la barre d'adresse du navigateur** (ex.
   `"https://ah2.exemple.org"`), sinon le navigateur bloque l'impression
   (erreur "CORS" dans la console).

   `port` (9123) est le port local du pont lui-même — laisser tel quel sauf
   conflit avec un autre programme sur ce poste.

3. **Générer le jeton d'impression** : se connecter à l'application en tant
   qu'admin ou promoteur → *Configuration Système* → section impression →
   *Régénérer*. Copier la valeur affichée dans le champ `token` de
   `config.json` (elle doit être identique des deux côtés — c'est ce qui
   empêche un site tiers ouvert dans un autre onglet du navigateur
   d'imprimer silencieusement).

## 6. Démarrer le pont

Manuellement (pour un premier test) :
```
cd printer_bridge
python server.py
```
Une ligne `Uvicorn running on http://127.0.0.1:9123` doit apparaître, et
`http://localhost:9123/health` doit répondre `{"status":"ok"}` dans un
navigateur sur ce poste.

**Pour qu'il démarre automatiquement à chaque ouverture de session** (sans
fenêtre visible), créer une tâche dans le *Planificateur de tâches Windows* :
- Déclencheur : à l'ouverture de session de l'utilisateur secrétariat.
- Action : lancer `pythonw.exe` (pas `python.exe`, pour éviter la fenêtre
  console) avec l'argument `C:\chemin\vers\printer_bridge\server.py`,
  répertoire de démarrage `C:\chemin\vers\printer_bridge`.

## 7. Vérifier

1. Se connecter à l'application en secrétaire sur ce poste.
2. Créer ou réimprimer une facture caisse — le ticket doit sortir sans
   action manuelle.
3. Si erreur, voir le dépannage ci-dessous.

## Dépannage

| Message | Cause | Solution |
|---|---|---|
| "Jeton d'impression non configuré." | Aucun jeton n'a encore été généré côté serveur, ou le navigateur ne l'a pas encore récupéré | Générer le jeton (étape 5.3), recharger la page |
| "Jeton d'impression non configuré ou invalide" après réimpression | `token` dans `config.json` ne correspond pas à celui généré côté serveur | Recopier exactement la valeur, redémarrer le pont |
| Ticket non imprimé — imprimante indisponible | Le pont ne répond pas (pas démarré), ou l'imprimante est éteinte/débranchée/mauvais nom | Vérifier que `python server.py` tourne, vérifier le câble/l'alimentation, revérifier `printer_name`/`vendor_id`/`printer_host` |
| Le pont démarre mais rien ne s'imprime, pas d'erreur visible | `connection_type`/nom/IP incorrect mais silencieusement acceptés | Vérifier les logs affichés dans la fenêtre de `server.py` |
| Logo absent ou mal centré | Fichier logo introuvable côté serveur, ou profil imprimante non standard | Non bloquant — le ticket s'imprime quand même sans logo |

## Notes pour qui prépare/dépanne ce document

- Aucune ouverture de pare-feu nécessaire : le pont n'écoute que sur
  `127.0.0.1` (ce poste uniquement), jamais accessible depuis le réseau.
- `config.json` n'est jamais versionné dans le dépôt (contient un secret) —
  chaque poste a le sien, créé à partir de `config.example.json`.
- Le poste doit avoir accès à l'application web AH2 comme n'importe quel
  poste secrétariat (aucune configuration réseau spécifique liée à
  l'impression).
- L'adresse du **serveur backend** (API, aujourd'hui `127.0.0.1:8200` en
  développement) n'a rien à voir avec ce document — c'est une adresse
  différente, réglée une seule fois au moment de construire l'application
  pour la production (`VITE_API_URL`), pas poste par poste. Ne pas la
  confondre avec `allowed_origins` ci-dessus, qui est l'adresse de
  l'application elle-même (le site que la secrétaire visite), pas celle du
  serveur qui la fait fonctionner en coulisses.
