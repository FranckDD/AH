# Fenêtre médicale — périmètre patient et résultats labo — Design

**Statut** : approuvé par l'utilisateur le 2026-09-22, prêt pour le plan d'implémentation.

## Contexte

Dette technique identifiée par l'utilisateur en test réel du portage web (sous-projet C de la passe de correction 2026-09-22, après B — recherche stock réactive, et A — ligne "Examen" en caisse, tous deux déjà livrés). Contrairement à A et B, ce sous-projet touche une vraie règle d'accès aux dossiers patients et **revient sur une décision déjà tranchée** au chantier 6 (registre `L5`, 2026-09-15) :

> *« Qui voit quoi entre clinique/toxico/spirituel ? Tranché le 2026-09-15 : ouverture large aux soignants, plus admin et promoteur, protection par traçabilité forte (journalisation de chaque accès) plutôt que par cloisonnement. »*

L'utilisateur a explicitement confirmé ce revirement pendant le brainstorming (voir Décisions ci-dessous), **restreint aux rôles `medecin`/`nurse` uniquement** — tous les autres rôles caregivers (`laborantin`, `psychologist`, `spiritualcounsellor`, `toxicomanager`, `assistant`, `admin`, `promoteur`) gardent l'accès large existant, inchangé par ce chantier.

## Décisions actées pendant le brainstorming

1. **Périmètre du revirement** : `medecin`/`nurse` uniquement. Aucun autre rôle n'est touché.
2. **Traçabilité** : la journalisation d'accès existante (`AuditUserAction`, action `VIEW_DOSSIER_COMPLET`) est **conservée en plus** du cloisonnement, pas remplacée. Double protection.
3. **Pas de duplication, pas de blocage inter-services** : l'identité patient reste unifiée (`patient_id` unique, chantier 6). Les drapeaux `is_clinical`/`is_toxicology`/`is_spiritual` (`compute_domain_flags()`, `repositories/patient_repo.py:238-254`) sont indépendants — un patient peut avoir plusieurs drapeaux vrais simultanément. Ce chantier ne touche **aucune donnée**, seulement ce que `medecin`/`nurse` voient à travers deux endpoints précis. Le dossier consolidé réel (accessible aux autres rôles) n'est ni modifié ni appauvri.
4. **Cas limite patient sans historique clinique** : `GET /patients/{id}/dossier` ne bloque jamais l'accès (pas de 403/404 sur la base du domaine) — la section clinique est simplement vide tant qu'aucun `MedicalRecord` n'existe. Nécessaire pour que le medecin puisse ouvrir la fiche d'un patient toxico avant même sa première consultation (recherche via "nouvelle consultation").

## Section 1 — Filtrage du dossier consolidé

**Fichier** : `controller/patient_dossier_controller.py` (construction de la réponse, lignes 33-114), consommé par `api_backend/backend_app/routes/patient_dossier/patient_dossier_endpoint.py:69-87`.

Pour un appelant `medecin`/`nurse` (déterminé via `current_user.roles`, même pattern que `list_patients()`) :
- `dossier_toxico` : omis de la réponse (pas `null`, la clé n'existe pas — cohérent avec la dégradation gracieuse déjà en place pour `domaines_indisponibles`, mais sémantiquement distinct : ici c'est un refus d'accès, pas une panne).
- `historique_spirituel` : omis, même règle.
- `flags` (`is_clinical`/`is_toxicology`/`is_spiritual`) : **conservé tel quel**, renvoyé à tous les rôles autorisés sans exception. Savoir qu'un patient a *aussi* un dossier toxico est cliniquement pertinent (ex. interactions médicamenteuses, contexte de prise en charge) sans exposer le détail.
- `resume_clinique`, `historique_medical`, `prescriptions`, `historique_labo` : inchangés, déjà strictement cliniques.
- `patient` (identité) : inchangé.
- Journalisation (`AuditUserAction`, `VIEW_DOSSIER_COMPLET`) : appelée exactement comme aujourd'hui, avant le filtrage de rôle — un accès filtré reste un accès tracé.

**Pas de nouveau paramètre de requête, pas de nouvelle route** — le filtrage se fait sur la réponse existante, selon le rôle du token déjà décodé par `get_current_user`.

## Section 2 — Verrouillage des onglets patients par domaine

**Fichiers** : routeur des patients (`api_backend/backend_app/routes/patients/patients_endpoints.py`, endpoints `/patients/toxicology` et `/patients/spiritual/list`).

Aujourd'hui ces deux endpoints n'ont **aucune** restriction de rôle propre (seul le routeur global les protège, avec le même jeu de rôles que tout le reste). Ajout d'une dépendance de route (même motif que le chantier `L4b-e` : dépendance de route ET-ée avec le routeur, jamais un remplacement) qui exclut `medecin`/`nurse` de ces deux routes spécifiquement — `/patients/clinical` reste inchangé (c'est leur périmètre).

`/patients/` (liste par défaut) n'a besoin d'aucun changement : le filtre `is_clinical` s'applique déjà pour ce rôle quand `search` est vide (`controller/patient_controller.py:303-322`), et reste volontairement inerte pendant une recherche explicite (mécanisme de rattachement "nouvelle consultation" — comportement voulu, pas un bug, à ne pas toucher).

## Section 3 — Résultats de laboratoire : lecture seule, statut "complet" uniquement

**Constat** : `medecin`/`nurse` n'ont déjà aucun droit d'écriture sur le labo — vérifié, `create_single_result`/`update_result_values` (rôles `laborantin, admin, ToxicoManager`) et `delete_result` (`admin` seul) les excluent déjà. Rien à changer côté écriture.

**Ce qui manque, ce qui change** — trois endpoints de lecture (`api_backend/backend_app/routes/labo/lab_endpoints.py`), pour l'appelant `medecin`/`nurse` uniquement :
- `GET /labo/history/paginated` (ligne 141-153) : le paramètre `status` fourni par l'appelant est **ignoré et forcé à `'completed'`** pour ce rôle, plutôt que simplement documenté comme optionnel. Empêche toute tentative de lister du `pending`/`partial` via manipulation de paramètre.
- `GET /labo/patient/{id}/history` (ligne 234-236) : même règle, filtre forcé côté contrôleur (`controller/lab_controller.py::get_patient_lab_history`).
- `GET /labo/results/{id}` (détail, ligne 192-198) : si le résultat demandé n'a pas `status='completed'` et que l'appelant est `medecin`/`nurse`, renvoyer 403 (pas 404 — la ressource existe, l'accès est refusé, distinction utile pour le diagnostic futur).

**Statut `'completed'`** (`models/lab.py:63`, colonne texte libre sans contrainte) est la seule valeur qui signifie réellement "terminé" côté serveur — confirmé par grep exhaustif du repo/controller. `'validated'`, présent uniquement dans le menu déroulant de `LabHistory.vue` (jamais posé côté serveur), est retiré de ce menu à cette occasion — option fantôme, source de confusion.

## Section 4 — Écran labo dédié dans la fenêtre médicale

**Constat** : l'entrée de menu `MedicalLayout.vue:178-182` pointe vers `/dashboard/labo/history` (`router/index.js:97`), une route qui vit dans l'arbre de `MainLayout.vue` (shell admin), pas dans celui de `MedicalLayout.vue`. Cliquer dessus fait donc sortir intégralement de la fenêtre médicale — tout le menu de navigation (RDV, Prescriptions, Dossier Médical, Patients, Médecins, Consultations) disparaît parce qu'on a changé de shell, pas à cause d'un bug de toggle.

**Correctif** : nouvelle route `/medical/lab-results`, montée dans l'arbre de `MedicalLayout.vue` (même famille que `/medical/appointments`, `/medical/prescriptions`, etc.), rendant un composant dédié (réutilise `LabGateway.getPaginatedHistory()`/`getPatientHistory()`, désormais filtrés côté serveur par la Section 3 — le composant n'a donc **pas besoin** de reproduire le filtre côté client, juste de ne plus exposer le sélecteur de statut à ce rôle, puisqu'il n'y a plus qu'une seule valeur possible). L'ancienne route `/dashboard/labo/history` reste inchangée pour les rôles qui l'utilisent légitimement (`laborantin`, `admin`, `ToxicoManager`).

**Renommage** : clé i18n `lab.nav.history` ("Historique") remplacée, côté menu `MedicalLayout.vue` uniquement, par une nouvelle clé dédiée — proposition retenue : **"Résultats d'examens"** (distincte de `lab.nav.history`, qui reste "Historique" pour l'écran labo lui-même où ce mot a du sens dans son propre contexte de navigation).

## Hors périmètre

- Aucune autre route labo (worklist, paillasse, batch, création) — déjà hors de portée de `medecin`/`nurse`.
- Aucun changement au comportement de recherche "nouvelle consultation" (`AppointmentModal.vue::lookupPatient`) — déjà non-scopé par domaine, ce qui est nécessaire au parcours de rattachement.
- Aucun changement à la politique d'accès pour les autres rôles (`laborantin`, `psychologist`, `spiritualcounsellor`, `toxicomanager`, `assistant`, `admin`, `promoteur`) — accès large inchangé, conforme à `L5`.

## Tests à prévoir (indicatif, détaillé dans le plan)

- `GET /patients/{id}/dossier` par un compte `medecin`/`nurse` sur un patient ayant les 3 domaines : `dossier_toxico`/`historique_spirituel` absents de la réponse, `flags` présent avec les 3 booléens corrects, `resume_clinique` présent.
- Même appel par `admin` : les 5 domaines toujours présents (non-régression du comportement existant).
- `GET /patients/toxicology` et `/patients/spiritual/list` par `medecin`/`nurse` → 403.
- `GET /labo/history/paginated?status=pending` par `medecin` → résultats tous `completed` malgré le paramètre.
- `GET /labo/results/{id}` sur un résultat `pending` par `nurse` → 403.
- Même appel par `laborantin` → 200, comportement inchangé.
- Vérification manuelle navigateur : clic sur "Résultats d'examens" depuis `MedicalLayout` conserve le menu médical visible.
