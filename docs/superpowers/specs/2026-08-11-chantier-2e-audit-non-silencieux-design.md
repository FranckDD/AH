# Chantier 2e — Piste d'audit non silencieuse

**Date :** 2026-08-11
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** audit `OPS-01` ; 3ᵉ des 5 sous-chantiers du chantier 2 (après 2a, ordre confirmé : 2e → 2d → 2b → 2c)

## Contexte

L'audit initial signalait que les écritures d'audit et le rafraîchissement des rôles étaient enveloppés dans des `except Exception: pass`, rendant tout échec totalement invisible. En creusant, la question transactionnelle sous-jacente a été vérifiée : `AuditRepository` ne fait volontairement aucun commit isolé (délègue à l'appelant), et les contrôleurs qui l'utilisent commitent bien l'entrée d'audit dans la même transaction que l'opération métier (vérifié sur `patient_controller.sync_simple_patient_creation`). **Ce n'est donc pas un problème d'atomicité** — c'est précisément le pattern `except Exception: pass` qui transforme un échec réel (contrainte violée, sérialisation impossible, etc.) en silence total : ni exception, ni trace, ni log.

## Périmètre — ampleur validée avec l'utilisateur

**11 sites** répartis sur **6 contrôleurs**, tous en travail en cours (chaque fichier a un diff de 100 à 270+ lignes par rapport à `HEAD`) :

| Fichier | Sites | Logger existant |
|---|---|---|
| `controller/auth_controller.py` | 2 (`LOGIN_SUCCESS`, `LOGIN_FAILURE`) | Non |
| `controller/caisse_controller.py` | 1 (`CANCEL` transaction) | Non |
| `controller/medical_controller.py` | 3 (`CREATE`/`UPDATE`/`DELETE` dossier) | Oui (`self.logger`) |
| `controller/patient_controller.py` | 1 (`SOFT_DELETE`) | Oui (`self.logger`) |
| `controller/pharmacy_controller.py` | 1 (helper `_audit()`, couvre 4 usages) | Non |
| `controller/prescription_controller.py` | 3 (`CREATE`/`UPDATE`/`DELETE`) | Oui (`self.logger`) |

C'est le chantier à la surface la plus large de la session — décision explicite de l'utilisateur de le traiter en entier plutôt que de se limiter aux sites déjà committables.

**Vérifié pendant le cadrage** : les 11 sites existent bien sur `HEAD`, avec parfois des différences cosmétiques mineures (commentaires, mise en forme du `except` sur une ou deux lignes) par rapport à la copie de travail — sans impact sur l'isolation, qui se construit toujours à partir du texte exact de `HEAD`, pas de la copie de travail.

**Deux sites explicitement exclus, cohérent avec SEC-09** : `PASSWORD_CHANGE_FAILED` et `PASSWORD_CHANGE_SUCCESS` dans `auth_controller.py` — ils appartiennent à `change_user_password()`, une méthode entièrement absente de `HEAD` (travail en cours non commité, déjà identifié au chantier SEC-09).

## Détail du correctif

Pattern uniforme sur les 11 sites : `except Exception: pass` (ou `except Exception:\n    pass`) → `except Exception: logger.exception("...")` (ou `self.logger.exception(...)` où un logger d'instance existe déjà).

Préserve le comportement actuel — un incident d'audit ne bloque jamais l'opération métier (décision déjà en place, cohérente pour un outil de gestion hospitalière : un souci de journalisation ne doit pas empêcher un médecin de créer un dossier). Le changement porte uniquement sur la visibilité : l'échec est désormais tracé.

Pour les 3 contrôleurs sans logger (`auth_controller.py`, `caisse_controller.py`, `pharmacy_controller.py`) : ajout de `import logging` + `logger = logging.getLogger(__name__)` au niveau module.

Message de log volontairement générique (`"Échec de l'écriture d'audit"`) plutôt que personnalisé par site : `logger.exception(...)` capture déjà la trace complète (fichier, ligne, type d'exception), qui identifie précisément le site en échec sans avoir besoin d'un message sur mesure à chaque emplacement.

## Vérification

- Pour chaque site, un test qui force l'échec de l'écriture d'audit (mock `audit_repo` levant une exception) et vérifie : (1) l'opération métier réussit quand même, (2) `logger.exception`/`self.logger.exception` a été appelé
- Suite de tests complète : aucune régression sur le comportement métier existant
- Vérification manuelle par grep : plus aucun `except Exception: pass` ni `except: pass` directement adjacent à un appel `audit_repo.log_*` sur les 6 fichiers, en dehors des 2 sites exclus documentés

## Hors périmètre

- `change_user_password()` (`PASSWORD_CHANGE_FAILED`/`PASSWORD_CHANGE_SUCCESS`) — n'existe pas sur `HEAD`, recommandation documentée pour quand cette fonctionnalité sera commitée : appliquer le même pattern (`logger.exception`) à ce moment-là
- Refonte de l'architecture transactionnelle d'audit (par exemple, garantir la persistance de l'audit même en cas de rollback de l'opération métier) — hors sujet, le pattern actuel (audit dans la même transaction que l'opération) est un choix de conception existant, pas un bug
