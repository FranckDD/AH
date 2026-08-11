# Contexte du projet — AH2 / Glostone-Kare

**Dernière mise à jour :** 2026-08-11
**But de ce document :** donner à quiconque reprend ce projet (humain ou session future) la vision d'ensemble sans avoir à relire les 6+ specs individuelles. Pour le détail d'un chantier précis, voir `docs/superpowers/specs/` et `docs/superpowers/plans/`. Pour l'état d'avancement, voir `docs/superpowers/SUIVI-AVANCEMENT.md`.

## Nature du projet

Système d'information hospitalier (SIH) couvrant : patients, dossiers médicaux, prescriptions, rendez-vous, consultations spirituelles, caisse/retraits, pharmacie/stock, laboratoire, toxicologie, piste d'audit, administration des comptes.

## Architecture

| Composant | Stack | État |
|---|---|---|
| API | FastAPI (`api_backend/backend_app/`), ~180 endpoints | Actif, en développement |
| Noyau métier | `controller/` + `repositories/` + `models/` (SQLAlchemy) | Actif |
| Base de données | PostgreSQL local (`AH2`), via `DatabaseManager` | Actif |
| Client lourd v1 | Tkinter/CustomTkinter (`view/`) | **Legacy** — plus modifié, retiré du suivi Git au chantier 0 |
| Client lourd v2 | PyQt6 (`view_pyqt6/`) | Actif, en développement parallèle |
| Mode hors ligne | SQLite + `repositories/repo_offline/` + `remote_gateway.py` | Actif mais voué à disparaître (voir Trajectoire PowerSync) |
| Console web | Vue 3 / Vite / Pinia / Tailwind 3 (`ah2-admin-web/`) | Actif, en développement — cible principale à terme |
| Async | Celery + Redis (`celery_app.py`, `tasks/`) | Tâches actuellement simulées (`sleep()`), pas de logique réelle |
| Migrations | Alembic (`alembic/`), adopté au chantier 2a | Baseline stampée, jamais exécutée |

## Hébergement et déploiement

- **Railway** et **Supabase** (hébergement d'origine) : projets expirés/supprimés par inactivité. Plus aucun environnement distant actif.
- Tout tourne aujourd'hui en local : PostgreSQL natif (service Windows), API sur `127.0.0.1:8000`, console web sur Vite (port variable selon l'environnement).
- Dépôt GitHub `FranckDD/AH`, **public**. Branche de travail : `AH2_V3-1`. Branche principale (cible des PR) : `AH2_V2`.
- `SUPABASE_URL` dans `.env` est un gabarit jamais renseigné (`https://ton-projet.supabase.co`) — le stockage objet Supabase n'a jamais été réellement configuré.

## Décisions structurantes (à respecter dans les chantiers futurs)

1. **Mode hors ligne → PowerSync, pas de maintien du mécanisme maison.** Décision prise avant le chantier SEC-09. Conséquence directe : le JWT reste en `localStorage` (pas de migration vers cookie `httpOnly`), car PowerSync a besoin de lire le token côté JS. Voir `docs/superpowers/specs/2026-08-10-sec-09-cycle-de-vie-jwt-design.md`.
2. **Pas de refresh token.** Un seul token, révocation via une colonne `token_version` sur `users` (incrémentée à la déconnexion). Décision utilisateur explicite, pour ne pas payer le coût d'un flux de renouvellement silencieux.
3. **`role_map.py` est la source de vérité canonique des rôles sur le chemin web.** 9 rôles réels en base (`admin`, `medecin`, `nurse`, `secretaire`, `laborantin`, `Psychologist`, `SpiritualCounsellor`, `ToxicoManager`, `Assistant`) + `manager`, un 10ᵉ rôle **réservé** (prévu par l'utilisateur, niveau d'accès inférieur à `admin`, en développement — aucune ligne en base pour l'instant). `patient_controller.py`, le mode hors ligne, et `UserModal.vue` ont chacun leur propre mécanisme de résolution de rôle, **non unifié** — connu et documenté, pas un oubli.
4. **Alembic adopté sur une base déjà peuplée.** La migration baseline (`6ea9b46b7a65`) a été générée puis **stampée, jamais exécutée** — son `upgrade()` supprimerait 17 tables réelles sans modèle SQLAlchemy (`admin`, `doctor`, `nurse`, `secretaire`, `laborantin`, `audit_logs`, etc.). Ces 17 tables sont explicitement exclues de l'autogénération (`alembic/env.py`, `include_object`) pour ne plus jamais être proposées à la suppression.
5. **`view_pyqt6/` est actif, `view/` est mort.** Ne jamais untrack ou supprimer du contenu dans `view_pyqt6/` sans vérifier d'abord s'il fait partie du travail en cours (chantier 0 a failli le faire par erreur, corrigé avant commit).

## Contrainte d'exécution la plus importante : le travail en cours de l'utilisateur

Le dépôt contient en permanence un volume important de modifications non commitées (généralement 60-90 fichiers modifiés + quelques nouveaux fichiers non suivis) : nouveau module labo, refonte du changement de mot de passe, redesign de la page 403, etc. **Ce travail ne doit jamais être perdu, écrasé, ni committé sans que ce soit son objet explicite.**

Technique établie pour isoler un correctif d'un fichier par ailleurs modifié par ce travail en cours :

1. Appliquer le correctif normalement sur la copie de travail (le fichier réel), pour que le comportement corrigé soit actif immédiatement.
2. Récupérer le contenu de `HEAD` (`git show HEAD:chemin/fichier.py`) dans un fichier temporaire.
3. Appliquer la **même transformation textuelle exacte** sur cette copie basée sur `HEAD` (via un script Python avec `assert old in content` pour valider avant remplacement).
4. Injecter ce contenu directement dans l'index (`git hash-object -w` + `git update-index --cacheinfo`), sans jamais toucher au fichier de travail.
5. Vérifier via `git diff --cached` que seul le hunk voulu est staged.
6. Committer.

Si le correctif porte sur du code qui **n'existe pas du tout sur `HEAD`** (entièrement nouveau dans le travail en cours, ex. `change_user_password()` dans `auth_controller.py`), il ne peut pas être isolé — il reste appliqué à la copie de travail (pour que ça fonctionne immédiatement) mais **non commité**, documenté comme tel dans le message du prochain commit qui touche ce fichier.

## Registre des secrets (jamais de valeur en clair dans ce dépôt)

Toutes les valeurs vivent dans `.env` (racine, ignoré par Git) ou ont été communiquées directement à l'utilisateur en session (jamais écrites dans un fichier commité) :
- `DATABASE_URL`, `JWT_SECRET` : rotés au chantier 0 suite à la fuite historique (`SEC-01`, dépôt public)
- Mot de passe du compte `admin_test` : roté au chantier 0 (`SEC-04`, ancien mot de passe exposé dans `README.md`)
- `IS_PROD=true` déjà positionné dans `.env` local — l'en-tête HSTS (chantier SEC-09) est donc actif même en développement sur cette machine

## Environnement de développement — particularités connues

- **Redis** : aucun serveur natif installé/démarré sur cette machine. Le conteneur Docker `mangu-redis` appartient à un **autre projet**, ne pas l'utiliser pour AH2. `slowapi` (limitation de débit, chantier 0) retombe sur un stockage en mémoire en son absence — fonctionnel mais non partagé entre process.
- **Vite / console web** : `EACCES: permission denied ::1:PORT` au démarrage sur cette machine, reproductible sur plusieurs ports (5173, 5174, 5175). Cause non confirmée (piste : réservation de ports Windows/Hyper-V/Docker Desktop, ou restriction IPv6). `npm run build` fonctionne sans problème — donc la CI (chantier 2b, Linux) ne sera pas affectée. Non résolu à ce jour.
- **Pas d'outil de navigateur automatisé disponible** dans l'environnement d'exécution de l'assistant — toute vérification visuelle (CSP, rendu UI) doit être faite manuellement par l'utilisateur, ou remplacée par une analyse statique quand c'est possible.
- **Suite de tests** : 4 échecs pré-existants et non liés aux chantiers de sécurité, présents depuis le chantier 0 — `test_patient_repo.py` (2), `test_prescription_repo.py` (2). Cause : problème d'enregistrement de modèles SQLAlchemy (`ConsultationSpirituel` non importé dans le contexte du test) et une fragilité d'isolation entre tests (ordre de collecte). Non traités — hors périmètre de tout chantier de sécurité, candidats naturels pour le chantier 2d (tests des chemins critiques).

## Méthode de travail établie pour tout nouveau chantier

1. **Brainstorming** (`superpowers:brainstorming`) — explorer, poser les questions de cadrage, proposer un design
2. **Spec** écrite dans `docs/superpowers/specs/YYYY-MM-DD-<nom>-design.md`, relue à froid, commitée
3. **Plan** (`superpowers:writing-plans`) écrit dans `docs/superpowers/plans/YYYY-MM-DD-<nom>.md`, avec code exact (pas de placeholder), commité
4. **Exécution** (`superpowers:executing-plans`), tâche par tâche, TDD (test qui échoue → correctif → test qui passe), isolation du travail en cours à chaque commit, vérification manuelle quand c'est possible
5. Mise à jour du fichier `docs/superpowers/SUIVI-AVANCEMENT.md` en fin de chantier
