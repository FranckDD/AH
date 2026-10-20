# Réduction personnel — design

Date : 2026-10-20 · Statut : validé en brainstorming par l'utilisateur (item 7 du backlog pré-déploiement)

## Contexte et intention

Le centre souhaite accorder une réduction de prix à son propre personnel quand
il se fait soigner ou achète des médicaments : **types de produits concernés,
montant minimal de facture, taux réduit**, le tout configuré uniquement par
l'admin et le promoteur. Aujourd'hui la caisse n'a aucune notion de « membre
du personnel » : les factures (`caisse`) sont liées à un patient, et les
comptes `users` ne sont reliés à aucun dossier patient. Le seul mécanisme de
réduction existant est la validation manuelle ponctuelle
(`discount_requests`, chantier notifications/réduction caisse, 2026-09-25).

Succès = un patient marqué « Personnel » est facturé automatiquement au tarif
réduit selon les règles en vigueur, y compris hors ligne, sans qu'un poste
modifié puisse s'accorder une réduction libre.

## Décisions utilisateur (2026-10-20)

1. **Identification** : case « Personnel » sur le dossier patient
   (`patients.is_staff`). Pas de lien dossier ↔ compte, pas de liste séparée —
   couvre aussi le personnel sans compte.
2. **Circuit** : application **automatique** dès la facture. Aucune demande
   à un manager (la règle est déjà définie par l'admin/promoteur).
3. **Catégories ciblables** (fines) : `medicament`, `examen`, `consultation`
   (médicale et spirituelle), `carnet`, `autre_soin` (ex. désintox). Chaque
   type d'article existant est rattaché à une catégorie, y compris les
   variantes de saisie (« Vente Médicament », « Médicament », « Sale
   Medication » → `medicament` ; « Examen », « Examens » → `examen`…).
4. **Seuil et base** : le montant minimal se compare au **total de la
   facture** ; le taux ne s'applique qu'aux **lignes de la catégorie visée**.
   Exemple : règle médicaments, minimum 5 000, taux 50 % ; facture 3 000
   médicaments + 4 000 examens → total 7 000 ≥ 5 000, réduction = 50 % × 3 000
   = 1 500.
5. **Droits** : seuls `admin` et `promoteur` configurent les règles et
   cochent/décochent « Personnel ». Il n'existe pas de rôle « manager »
   dans l'application (rôles : admin, promoteur, ToxicoManager, secretaire,
   medecin…) : « admin et manager » du backlog a été tranché en
   `admin` + `promoteur`.
6. **Pas de cumul** avec une réduction manuelle : si la secrétaire demande une
   réduction manuelle sur une facture personnel et que le manager approuve, la
   décision **remplace** la réduction personnel (calculée sur le montant brut
   d'origine). Si elle est refusée, la réduction personnel reste.
7. **Hors ligne** : la réduction se calcule localement (règles et `is_staff`
   synchronisés), avec **contrôle serveur à la synchro**. Une facture dont la
   réduction ne correspond pas aux règles est refusée et va en quarantaine,
   visible dans « Échecs de synchro ».

## Approche retenue

Règles dédiées (`staff_discount_rules`) + fonction de calcul pure + montants
enregistrés sur la facture. Écartées :

- Réutiliser `discount_requests` avec approbation automatique : mélange deux
  workflows (la table impose `requested_to`, notification, mot de passe de
  reconfirmation…).
- Ligne négative dans les articles de la facture : fausse le stock, les
  exports et le grand livre financier.

## Architecture

### 1. Modèle de données

Migration Alembic (appliquée sans demande préalable par instance, voir
politique de migration relâchée du 2026-09-25 ; vérifier l'état réel de la
base avant et après).

**`patients.is_staff`** — `Boolean NOT NULL DEFAULT false`. Écriture réservée
à `admin`/`promoteur` : sur `PUT`/`PATCH /patients/{id}`, un rôle non autorisé
dont le payload contient une valeur de `is_staff` **différente de l'actuelle**
reçoit **403** (jamais d'ignorance silencieuse : l'utilisateur doit savoir que
sa case n'a pas été prise en compte). Une valeur identique à l'actuelle est
tolérée (formulaires qui renvoient l'objet entier). Le même garde-fou couvre
la synchronisation PowerSync — voir §4.

**Nouvelle table `staff_discount_rules`** :

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `category` | String(30) | `medicament` / `examen` / `consultation` / `carnet` / `autre_soin` ; CHECK constraint sur ces 5 valeurs |
| `min_invoice_amount` | Numeric(10,2) NOT NULL DEFAULT 0 | seuil sur le **total** de la facture |
| `rate_percent` | Integer NOT NULL | CHECK 1..100 |
| `is_active` | Boolean NOT NULL DEFAULT true | |
| `created_by`, `created_at`, `updated_by`, `updated_at` | audit | |

Une seule règle **active** par catégorie : index unique partiel
`(category) WHERE is_active`.

**`caisse`** gagne :

- `staff_discount_amount` — `Numeric(10,2) NOT NULL DEFAULT 0` ;
- `staff_discount_details` — `JSONB NULL` : snapshot des règles appliquées
  (catégorie, taux, base de calcul, seuil), pour que le ticket, l'audit et les
  rapports n'aient jamais à re-interpréter des règles qui auraient changé
  depuis.

`caisse.amount` reste le **montant net dû**, comme aujourd'hui (décision déjà
actée au chantier réductions : tout consommateur de `amount` — paiement, PDF,
affichage, ledger — n'a pas à connaître le concept de réduction). Le montant
brut = somme des `line_total` des articles = `amount + staff_discount_amount`.

**Table de correspondance type d'article → catégorie** : fonction pure
(`normalize_item_category(item_type)`) côté serveur et côté client, insensible
à la casse/aux accents, avec repli explicite `autre_soin` pour tout type
inconnu (jamais d'erreur sur un type imprévu — les données existantes sont
déjà incohérentes, vérifié en base le 2026-10-20 : 8 libellés distincts pour
~4 notions).

### 2. Calcul et contrôle

**Fonction pure** `compute_staff_discount(lines, is_staff, rules)` →
`{amount, details}` :

1. Si `is_staff` est faux ou `lines` vide → `0`.
2. `total = Σ line_total` (lignes `status = active`).
3. Pour chaque règle active dont `total >= min_invoice_amount` :
   `réduction += rate_percent/100 × Σ line_total des lignes de la catégorie`.
4. Arrondi au centime, une seule fois sur la somme.

Implémentée **en Python** (`api_backend`/`controller`) et **en JS**
(frontend), avec le **même jeu de cas de test** des deux côtés (seuil,
catégories multiples, aucune règle, patient non personnel, arrondi).

**Contrôle serveur** (`CaisseController.create_transaction`) : la vérification
actuelle « Σ lignes = amount » devient « Σ lignes − staff_discount_amount =
amount ». Le serveur **recalcule** la réduction depuis `patients.is_staff` et
les règles actives et la compare à `staff_discount_amount` reçu :

- écart → `ValueError` / 422 (en ligne : message clair à l'écran ; à la
  synchro : mise en quarantaine, voir §4) ;
- patient non personnel avec `staff_discount_amount > 0` → refusé ;
- facture sans patient (`patient_id` NULL, patient de passage) → jamais de
  réduction personnel.

Le serveur fait foi : en cas de désaccord sur la valeur de `is_staff` ou des
règles (règle modifiée entre le calcul local et la synchro), la facture est
rejetée plutôt que corrigée silencieusement — comportement identique au
contrôle de cohérence de montant actuel.

**Interaction avec la réduction manuelle** (`discount_requests`) :

- À la création de la demande, `discount_requests.original_amount` = montant
  **brut** (Σ lignes), pas le net.
- À l'approbation : `caisse.amount = original_amount × (1 − pct/100)`,
  `staff_discount_amount` repasse à `0` et `staff_discount_details` est
  conservé avec la mention « remplacée par réduction manuelle #id » (traçabilité).
- Au refus ou à l'annulation : `caisse.amount` et `staff_discount_amount`
  inchangés.

### 3. Backend — endpoints

- `GET /staff-discount-rules` (admin, promoteur, secretaire — la caisse en
  ligne en a besoin pour calculer) : liste des règles.
- `PUT /staff-discount-rules/{category}` (admin, promoteur) : crée/met à jour
  la règle d'une catégorie (`min_invoice_amount`, `rate_percent`,
  `is_active`). Journalisé dans `audit_user_actions` (qui, ancien → nouveau).
- `PATCH /patients/{id}` : accepte `is_staff` pour admin/promoteur
  uniquement (§1) ; journalisé.

### 4. PowerSync (hors ligne) — 4 couches, motif déjà établi

Zone sensible, déjà documentée deux fois (chantier 4 sous-projet 3,
chantier triage). Tout nouveau champ d'un formulaire qui écrit via les stores
locaux doit traverser **4 couches** : `AppSchema.js`, INSERT/UPDATE locaux,
`DossierConnector.js` (PUT + PATCH), payload Gateway.

- `patients.is_staff` : colonne ajoutée à la table patients locale
  (`AppSchema.js`) et au stream `sync-config.yaml` déjà utilisé par la
  secrétaire/caisse. **Lecture seule côté client** : la case n'est modifiable
  qu'en ligne par admin/promoteur ; le connecteur ne doit jamais pousser
  `is_staff` (sinon un poste hors ligne contournerait le garde-fou de rôle).
- `staff_discount_rules` : nouvelle table locale en **lecture seule**
  (données de référence, comme `exam_catalog`/`referenceData.js`), ajoutée au
  stream de la caisse.
- `caisse` : `staff_discount_amount` et `staff_discount_details` ajoutés à
  la table locale et au connecteur (INSERT de la facture) — et au payload du
  Gateway de la caisse.
- Facture refusée par le contrôle serveur à la synchro : quarantaine
  existante (`syncQuarantine.js`, vue « Échecs de synchro »), message
  explicite (« réduction personnel incohérente avec les règles »).

### 5. Frontend

- **Écran de configuration** (admin, promoteur) : tableau des 5 catégories
  avec montant minimal, taux et actif/inactif, bouton enregistrer par ligne.
  Emplacement proposé : une section « Réductions personnel » dans la
  configuration existante de la caisse/du centre (à confirmer en revue de
  l'écran lors de l'implémentation).
- **Fiche patient** (`PatientForm`/en-tête patient) : case « Personnel »,
  visible et modifiable uniquement par admin/promoteur (`authStore.hasRole`).
  Badge « Personnel » dans la liste et le dossier.
- **Caisse** (`CaisseInvoiceModal.vue` et écran de saisie) : si le patient est
  « Personnel », calcul automatique à chaque modification des lignes ; ligne
  « Réduction personnel −X » visible avant validation, total net affiché.
  Le bouton « Demander une réduction » reste disponible (décision §6 : il
  remplace la réduction personnel s'il est approuvé — message d'avertissement
  à l'ouverture de la demande).
- **Ticket thermique** : la réduction personnel s'affiche avec la même
  structure que la réduction manuelle actuelle (prix normal / réduction /
  montant dû) — champs lus depuis `staff_discount_details`.
- **i18n** : toutes les nouvelles chaînes en FR et EN dès le départ.

## Gestion d'erreurs

- Règle invalide (`rate_percent` hors 1..100, seuil négatif) → 422.
- Deux règles actives sur une même catégorie → impossible (index unique) ;
  l'écran de configuration met à jour la règle existante, il n'en crée pas
  une seconde.
- Facture dont la réduction ne correspond pas aux règles → 422 en ligne,
  quarantaine à la synchro.
- Modification de `is_staff` par un rôle non autorisé → 403.
- Type d'article inconnu → catégorie `autre_soin` (jamais d'erreur).
- Règle désactivée ou modifiée → n'affecte que les factures créées après
  (le snapshot `staff_discount_details` fige les anciennes).

## Tests

Backend (pytest) :

- `compute_staff_discount` : seuil atteint/non atteint, plusieurs catégories,
  patient non personnel, aucune règle active, arrondi, lignes annulées
  ignorées, type d'article inconnu → `autre_soin`, variantes de libellé.
- Contrôle serveur : facture cohérente acceptée ; réduction trop élevée,
  réduction sur patient non personnel, réduction sans patient → refusées.
- Droits : `is_staff` modifiable par admin/promoteur, refusé pour secrétaire,
  médecin, etc. ; règles : écriture admin/promoteur seulement.
- Réduction manuelle : approbation remplace la réduction personnel
  (`staff_discount_amount` à 0, `amount` recalculé sur le brut) ; refus la
  conserve.
- Index unique partiel : deuxième règle active sur la même catégorie refusée.

Frontend : mêmes cas pour la fonction JS (test unitaire ou script Node), build
de production vert.

Non-régression : une facture de patient non personnel garde exactement le
comportement actuel (`staff_discount_amount = 0`, contrôle de cohérence
inchangé en pratique).

## Hors périmètre

- Plafond de réduction par période ou par employé.
- Rapport/KPI dédié aux réductions personnel (peut être consommé plus tard par
  l'onglet Rapports, item 8 du backlog — le snapshot `staff_discount_details`
  le permet).
- Lien automatique entre compte utilisateur et dossier patient.
- Validité temporelle des règles (dates de début/fin) : seul `is_active`.

## Révisions après lecture du code (2026-10-20, avant le plan)

Ces points corrigent le design ci-dessus ; le plan
(`docs/superpowers/plans/2026-10-20-reduction-personnel.md`) fait foi en cas d'écart.

1. **`is_staff` via un endpoint dédié.** `PUT/PATCH /patients/{id}` passent par
   des procédures stockées Postgres (`create_patient`/`update_patient`) :
   les modifier pour un seul booléen risque une régression. La bascule se fait
   par `PUT /patients/{patient_id}/staff` (admin, promoteur), et `is_staff`
   n'est pas dans `PatientUpdate` (un `PUT /patients` ne peut donc pas le
   changer). Remplace la règle « 403 si valeur différente » du §1.
2. **`staff_discount_details` produit par le serveur seul.** Le poste n'envoie
   que `staff_discount_amount` ; un snapshot fourni par le client ne serait pas
   fiable.
3. **Limite préexistante de la caisse hors ligne.** La recherche patient de
   `CaisseInvoiceModal` est en ligne seulement (aucun secours local). `is_staff`
   voyage donc dans la réponse `GET /patients/`, pas dans le stream
   `patients_lookup` ; seules les règles ont un secours hors ligne. Un patient
   personnel n'est sélectionnable hors ligne que s'il l'a été avant la coupure.
4. **Écran des règles** : vue dédiée `/reductions-personnel` (admin, promoteur),
   car la route `system-config` exclut `promoteur`.

