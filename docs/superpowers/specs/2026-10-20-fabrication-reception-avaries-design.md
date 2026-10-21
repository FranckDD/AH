# Fabrication, réception et avaries du stock — design

Date : 2026-10-20 · Statut : validé en brainstorming par l'utilisateur (items 1 et 2 du backlog pré-déploiement)

## Contexte et intention

Le centre fabrique certains produits (le « miel », etc.) et les livre ensuite à son stock. Le stock actuel (`pharmacy` + journal `stock_movement`) ne connaît ni réception, ni lot, ni fournisseur, ni avarie : le seul moyen d'ajouter du stock est le bouton « Réapprovisionner » (`POST /pharmacy/{id}/renew`) et la modification directe de la quantité (`PUT /pharmacy/{id}`), tous deux ouverts à `secretaire`, `admin`, `Assistant` et `ToxicoManager` (le routeur `/pharmacy` n'a qu'une garde de rôle globale) et **sans aucun contrôle**. Le centre veut :

1. une fenêtre de **fabrication** (quantité produite, date de production, date de livraison au centre, etc.) ;
2. la gestion de la **réception** des marchandises et des **avaries** (quantités endommagées, perdues, défectueuses) ;
3. un **contrôle** : une personne distincte valide ce qui entre ou sort, sur le même esprit que la validation des réductions (le circuit papier du « Okey » avait été falsifié).

Succès = aucune entrée en stock (hors action exceptionnelle de l'admin) ni sortie hors vente sans la validation d'un second compte ; chaque lot fabriqué est traçable jusqu'à sa réception ; le centre voit ce qui a été reçu bon, endommagé, perdu ou défectueux.

## Décisions utilisateur (2026-10-20)

1. **Un seul flux** : lot fabriqué → livraison → réception → stock. La même réception sert aux livraisons d'un fournisseur (champ « origine »).
2. **Rôles** : l'`Assistant` saisit. Un **nouveau rôle « Contrôleur de stock »** valide ; son écran est limité à ce qui concerne son rôle (entrées et sorties de stock). L'`admin` voit tout.
3. **Validation en deux étapes** : l'Assistant enregistre → statut « à contrôler », stock **non modifié** ; le contrôleur confirme (le stock est mis à jour), corrige les quantités, ou rejette avec un motif.
4. **Avaries** : à la réception (reçu bon / endommagé / perdu / défectueux) **et** plus tard sur le stock en rayon (déclaration d'avarie), les deux soumises à la même validation.
5. **Champs du lot de fabrication** (en plus de quantité produite, date de production, date de livraison) : produit + n° de lot, date de péremption, responsable / site de production. (Coût de revient et notes : écartés.)
6. **Lots** : traçabilité sans toucher aux ventes. Le stock reste une quantité globale par produit ; les ventes en caisse ne changent pas.
7. **Réception** : bon de livraison **multi-lignes** (une ligne par produit).
8. **Actions directes sur le stock** (réapprovisionner, modifier une quantité, supprimer) : **réservées à l'admin**, tracées. Tout le reste passe par une réception ou une avarie contrôlée. Le `ToxicoManager` **perd** la capacité de réapprovisionner ou de modifier une quantité (ajouté le 2026-10-20, demande explicite).
9. **Secrétaire** : elle ne peut plus réapprovisionner ni modifier une quantité elle-même. Pour **chaque** réapprovisionnement ou modification de quantité, elle envoie une **demande d'autorisation à l'admin** (ajouté le 2026-10-20, demande explicite). Rien ne change dans le stock tant que l'admin n'a pas approuvé.

## Approche retenue

Tables dédiées avec statut, l'entrée en stock étant faite par la validation via le journal `stock_movement` existant. Écartées : mouvements « en attente » dans `stock_movement` (mélange historique réel et brouillons), table « opération » générique (trop abstraite pour trois cas).

## Architecture

### 1. Modèle de données

Migration Alembic (SQL brut idempotent, motif des migrations 017/018 ; reporter le même DDL dans `ci/schema_only.sql`). **Vérifié le 2026-10-20** : `stock_movement.movement_type`, `pharmacy.stock_status`, `pharmacy.medication_type` et `notifications.type` n'ont **aucune** contrainte CHECK (chaînes libres) ; les valeurs de `movement_type` déjà utilisées sont `initial`, `update`, `renew` (pharmacie) et `VENTE`, `ANNULATION_VENTE` (caisse). Les nouveaux types sont `reception`, `avarie_endommage`, `avarie_perdu`, `avarie_defectueux`. En revanche `users.postgres_role` a une CHECK (`app_secretaire`, `app_medical`, `app_laborantin`, `app_admin`, `app_toxico_web`) — voir « Rôle » plus bas.

**`production_lots`**

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `lot_number` | String(30) UNIQUE NOT NULL | généré : `LOT-AAAAMMJJ-NNN` (NNN = incrément du jour) |
| `product_id` | FK `pharmacy.medication_id` NOT NULL | produit fabriqué (choisi dans le stock existant) |
| `quantity_produced` | Integer NOT NULL, CHECK > 0 | |
| `production_date` | Date NOT NULL | |
| `delivery_date` | Date NULL | date de livraison au centre (prévue, puis réelle) |
| `expiry_date` | Date NULL | péremption du lot |
| `producer` | String(150) NULL | responsable / site (texte libre) |
| `status` | String(20) NOT NULL DEFAULT `produit` | CHECK ∈ `produit`, `livre`, `recu`, `annule` |
| `created_by`, `created_at` | audit | |

Aucun effet sur le stock : un lot est un enregistrement de production. `produit` → `livre` (renseigné par l'Assistant quand la livraison arrive ; condition pour créer la réception liée) → `recu` (automatique à la validation de la réception liée) ; `annule` (admin ou créateur tant qu'aucune réception n'y est liée).

**`stock_receipts`** (bon de livraison)

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `receipt_number` | String(30) UNIQUE | généré `REC-AAAAMMJJ-NNN` |
| `origin` | String(20) NOT NULL | CHECK ∈ `fabrication`, `fournisseur` |
| `production_lot_id` | FK `production_lots.id` NULL | obligatoire si `origin = fabrication`, NULL sinon (CHECK de cohérence) |
| `supplier` | String(150) NULL | texte libre, si `origin = fournisseur` |
| `delivery_ref` | String(100) NULL | référence du bon du fournisseur |
| `received_date` | Date NOT NULL | |
| `status` | String(20) NOT NULL DEFAULT `a_controler` | CHECK ∈ `a_controler`, `valide`, `rejete` |
| `created_by`, `created_at` | | l'Assistant ou l'admin qui a saisi |
| `controlled_by`, `controlled_at` | NULL | qui a décidé, quand |
| `reject_reason` | Text NULL | obligatoire si `rejete` |

**`stock_receipt_lines`**

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `receipt_id` | FK `stock_receipts.id` ON DELETE CASCADE | |
| `product_id` | FK `pharmacy.medication_id` NOT NULL | |
| `qty_expected` | Integer NULL | quantité annoncée (lot ou bon) ; NULL si inconnue |
| `qty_good` | Integer NOT NULL DEFAULT 0, CHECK >= 0 | entre en stock à la validation |
| `qty_damaged` | Integer NOT NULL DEFAULT 0, CHECK >= 0 | |
| `qty_lost` | Integer NOT NULL DEFAULT 0, CHECK >= 0 | |
| `qty_defective` | Integer NOT NULL DEFAULT 0, CHECK >= 0 | |
| `lot_number`, `expiry_date` | String(30) NULL, Date NULL | repris du lot de fabrication, ou saisis |

Règles : au moins une ligne ; sur chaque ligne `qty_good + qty_damaged + qty_lost + qty_defective > 0` et, si `qty_expected` est renseignée, la somme ne peut pas la dépasser (l'écart inférieur est autorisé : livraison partielle). Pour une réception de fabrication, une seule ligne, produit et quantité attendue préremplis depuis le lot. Le contrôleur corrige les quantités **sur ces mêmes colonnes** ; la déclaration d'origine reste dans le journal d'audit existant (`audit_user_actions.old_values/new_values`).

**`stock_incidents`** (avaries sur le stock en rayon)

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `product_id` | FK `pharmacy.medication_id` NOT NULL | |
| `kind` | String(20) NOT NULL | CHECK ∈ `endommage`, `perdu`, `defectueux` |
| `quantity` | Integer NOT NULL, CHECK > 0 | |
| `reason` | Text NOT NULL | motif de la déclaration |
| `incident_date` | Date NOT NULL | |
| `status` | String(20) NOT NULL DEFAULT `a_controler` | CHECK ∈ `a_controler`, `valide`, `rejete` |
| `created_by`, `created_at`, `controlled_by`, `controlled_at`, `reject_reason` | | comme ci-dessus |

**`stock_adjustment_requests`** (demandes d'autorisation de la secrétaire à l'admin)

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `product_id` | FK `pharmacy.medication_id` NOT NULL | |
| `kind` | String(20) NOT NULL | CHECK ∈ `reapprovisionnement` (ajouter `quantity`), `correction` (fixer la quantité à `quantity`) |
| `quantity` | Integer NOT NULL, CHECK >= 0 (et > 0 pour `reapprovisionnement`) | |
| `reason` | Text NOT NULL | motif de la demande |
| `status` | String(20) NOT NULL DEFAULT `en_attente` | CHECK ∈ `en_attente`, `approuve`, `refuse`, `annule` |
| `requested_by`, `requested_at` | | la secrétaire |
| `decided_by`, `decided_at`, `decision_note` | NULL | l'admin ; motif obligatoire si `refuse` |
| `stock_before`, `stock_after` | Integer NULL | valeurs relevées à l'approbation (traçabilité) |

Une demande par action et par produit : pas de demande « en lot ». Le stock est lu au moment de l'approbation (la quantité a pu changer par des ventes depuis la demande).

### 2. Flux et effets sur le stock

**Validation d'une réception** (`POST /stock/receipts/{id}/validate`, contrôleur ou admin, jamais l'auteur de la saisie) — **dans une seule transaction** :
- pour chaque ligne, `pharmacy.quantity += qty_good` par un `UPDATE … SET quantity = quantity + :n` atomique (ou `SELECT … FOR UPDATE` sur la ligne produit), car les ventes de la caisse modifient la même quantité en parallèle (la déduction de caisse actuelle lit puis écrit : ne pas répliquer ce motif) ; recalcul de `stock_status` (`Pharmacy.update_stock_status`) ;
- un `StockMovement` de type `reception` (`change_qty = +qty_good`, `note` citant le n° de réception et, le cas échéant, les quantités endommagée/perdue/défectueuse) par ligne dont `qty_good > 0` ;
- péremption : si la ligne porte une `expiry_date`, `pharmacy.expiry_date` devient la **plus proche** entre l'actuelle et celle de la ligne (alerte prudente) ;
- si l'origine est `fabrication` : `production_lots.status = recu` ;
- `stock_receipts.status = valide`, `controlled_by/at` ; entrée dans `audit_user_actions` ; notification à l'auteur.

**Rejet** (`POST /stock/receipts/{id}/reject`) : motif obligatoire, aucun changement de stock, statut `rejete`, notification à l'auteur ; l'Assistant peut ressaisir un nouveau bon (le lot de fabrication reste `livre`).

**Correction par le contrôleur** : avant de valider, `PUT /stock/receipts/{id}/lines` (contrôleur/admin, statut `a_controler` seulement) modifie les quantités ; audité (anciennes → nouvelles valeurs).

**Avarie** (`POST /stock/incidents`, Assistant/admin → `a_controler`) ; **validation** (`…/validate`, contrôleur/admin ≠ auteur) : `pharmacy.quantity -= quantity` (atomique, refusée si la quantité dépasse le stock, au moment de la validation), `StockMovement` `avarie_<kind>` avec `change_qty = −quantity`, recalcul de `stock_status`, audit, notification. **Rejet** : motif obligatoire.

**Demande d'autorisation de la secrétaire** (`POST /stock/adjustment-requests`, rôle `secretaire`) → statut `en_attente`, stock inchangé, notification `stock_adjustment_request` à tous les admins actifs. **Approbation** (`POST …/approve`, `admin` seulement, ≠ demandeur) — dans une seule transaction : `reapprovisionnement` → `pharmacy.quantity += quantity` (atomique) avec un `StockMovement` de type `renew` ; `correction` → `pharmacy.quantity = quantity` avec un `StockMovement` de type `update` dont `change_qty` = différence (nouvelle − quantité relevée au moment de l'approbation ; 0 autorisé, tracé) ; recalcul de `stock_status` ; `stock_before`/`stock_after` renseignés ; audit ; notification `stock_decided` à la secrétaire. **Refus** (`…/reject`, motif obligatoire) : aucun changement. **Annulation** par la demandeuse tant que `en_attente`. Une demande décidée n'est jamais modifiable. Ce circuit réutilise les types de mouvement `renew`/`update` existants pour que l'historique reste lisible.

**Règle des deux comptes** : `controlled_by != created_by` imposé côté serveur (403 sinon), y compris pour l'admin. Un admin qui a saisi une opération ne peut pas la valider lui-même.

**Annulation d'une opération `a_controler`** : par son auteur ou l'admin (statut → supprimée logiquement via `rejete` avec motif « annulé par l'auteur ») ; une opération `valide` n'est jamais modifiable ni annulable (la correction passe par une avarie ou un ajustement admin).

**Notifications** : système générique existant (`notifications`, polling 30 s, popup). Types `stock_to_check` (aux utilisateurs actifs de rôle `StockController`, et à l'admin) à la création d'une réception ou d'une avarie ; `stock_adjustment_request` (à tous les admins actifs) à la création d'une demande de la secrétaire ; `stock_decided` (à l'auteur / à la demandeuse) à la décision. Voir le motif de câblage des dépendances optionnelles : le contrôleur doit être réellement câblé dans la fonction d'injection de dépendances utilisée par les routes (un défaut déjà rencontré une fois sur ce projet : `notification_repo` jamais passé au contrôleur), avec un test de bout en bout par vrai appel HTTP vérifiant qu'une ligne `Notification` existe.

### 3. Endpoints et droits

Nouveau routeur `/stock` (garde de rôle **par route**, pas globale) :

| Route | Rôles |
|---|---|
| `POST/GET /stock/lots`, `POST /stock/lots/{id}/deliver`, `POST /stock/lots/{id}/cancel` | `Assistant`, `admin` ; `GET` aussi `StockController` |
| `POST /stock/receipts`, `GET /stock/receipts`, `GET /stock/receipts/{id}` | création : `Assistant`, `admin` ; lecture : + `StockController` |
| `PUT /stock/receipts/{id}/lines`, `POST …/validate`, `POST …/reject` | `StockController`, `admin` (≠ auteur pour validate/reject) |
| `POST /stock/incidents`, `GET /stock/incidents` | création : `Assistant`, `admin` ; lecture : + `StockController` |
| `POST /stock/incidents/{id}/validate`, `…/reject` | `StockController`, `admin` (≠ auteur) |
| `POST /stock/adjustment-requests` (demande), `GET /stock/adjustment-requests` (les siennes), `POST …/cancel` | `secretaire` ; lecture de **toutes** les demandes : `admin` |
| `POST /stock/adjustment-requests/{id}/approve`, `…/reject` | `admin` seulement (≠ demandeur) |
| `GET /stock/movements` (entrées et sorties : fabrication/réception, avaries, ventes, annulations de vente, ajustements) | `StockController`, `admin`, `Assistant` |

Routeur existant `/pharmacy` : les routes de **lecture** restent ouvertes comme aujourd'hui (la caisse de la secrétaire en dépend) ; les routes d'écriture reçoivent leur propre garde :
- `POST /pharmacy/{id}/renew` et `DELETE /pharmacy/{id}` : `admin` seulement ;
- `PUT /pharmacy/{id}` : `admin` peut tout modifier (ajustement direct, tracé) ; `Assistant` et `ToxicoManager` peuvent modifier les champs non liés à la quantité (nom, prix, seuil, forme, type, dosage) mais **toute modification de `quantity` par un autre rôle que `admin` est refusée (403)** ; `secretaire` : **aucune écriture** (403), elle passe par une demande d'autorisation ;
- `POST /pharmacy/` (création de produit) : `admin`, `Assistant`, `ToxicoManager` ; la quantité initiale est **forcée à 0** pour tout rôle autre que `admin` (l'entrée initiale passe par une réception) ; `secretaire` ne crée pas de produit ;
- `secretaire` : lecture du stock comme aujourd'hui (la caisse en dépend) ; `ToxicoManager` : plus aucun réapprovisionnement ni modification de quantité.

### 4. Rôle « Contrôleur de stock »

- Nouvelle ligne `StockController` dans `application_roles` (migration, idempotente) ; ajouter l'alias canonique dans `api_backend/backend_app/security/role_map.py` (même motif que `ASSISTANT = "assistant"` avec ses alias) ; constante dans `ah2-admin-web/src/router/index.js` (`ROLES`) et libellés i18n du rôle (FR/EN) dans la gestion des utilisateurs (`UserManagement.vue`/`UserModal.vue`, voir comment `Assistant` y figure).
- `users.postgres_role` a une contrainte CHECK sur 5 valeurs : suivre le précédent de `Assistant` et `Psychologist` (tous deux `app_admin`). **Vérifier à l'implémentation** que ce champ n'est pas lu pour une décision d'autorisation du web (`grep postgres_role`), sinon choisir la valeur la plus restrictive existante et le consigner.
- **Vue limitée** : le rôle n'a accès, côté frontend et côté serveur, qu'aux écrans « À contrôler » et « Mouvements » (entrées/sorties) ; menu minimal (jamais patients, caisse, dossiers, labo…). Toutes les routes frontend existantes qui n'ont pas `StockController` dans leurs `roles` lui sont déjà refusées ; vérifier les écrans communs (tableau de bord par défaut après connexion, profil, mot de passe) : le contrôleur doit atterrir sur « À contrôler » et pouvoir changer son profil/mot de passe.

### 5. Frontend

Sous le menu Stock (admin, Assistant) : **Fabrication** (liste et saisie des lots, bouton « Marquer livré »), **Réceptions** (liste ; saisie multi-lignes avec choix de l'origine : lot livré → ligne préremplie, ou fournisseur), **Avaries** (déclaration sur un produit en stock). Pour le contrôleur : **À contrôler** (file des réceptions et avaries `a_controler`, détail, correction des quantités, valider / rejeter avec motif) et **Mouvements** (historique lecture seule des entrées/sorties avec filtres produit/période/type). **Pour la secrétaire** : sur l'écran Stock en lecture (`/secretariat/stock`), un bouton « Demander un réapprovisionnement / une correction » par produit (type, quantité, motif) et une liste « Mes demandes » avec leur statut. **Pour l'admin** : une page « Demandes d'ajustement » (file, détail avec stock actuel, approuver / refuser avec motif). Pastille et popup de notification via le composant existant. Écrans **en ligne seulement**, comme l'écran Stock actuel ; le stock mis à jour descend vers la caisse hors ligne par le flux `pharmacy_stock` déjà existant (lecture seule). Toutes les chaînes en FR et EN.

### 6. Effets sur l'existant

- `Pharmacy.quantity` / `stock_status` : modifiés à la validation (atomique) ; la déduction de caisse reste inchangée.
- `renew`/`update`/`delete`/création : voir §3.
- Alertes de péremption et KPI stock (`/pharmacy/alerts/*`, `/pharmacy/kpi/*`) : inchangés, ils lisent `quantity`/`expiry_date`.
- Journal `stock_movement` : de nouveaux types s'y ajoutent ; vérifier que les consommateurs existants de `movement_type` (écrans, rapports, exports) tolèrent les nouvelles valeurs (aucune CHECK, mais des listes de libellés peuvent exister).

## Gestion d'erreurs

- Bon sans ligne ; ligne dont la somme dépasse `qty_expected` ; quantités négatives ; origine `fabrication` sans lot, ou avec un lot qui n'est pas au statut `livre` (donc `produit`, `recu` ou `annule`) ; lot déjà lié à une réception non rejetée → 422.
- Validation par l'auteur de la saisie, ou par un rôle non autorisé → 403.
- Avarie supérieure au stock à la validation → 409 avec la quantité disponible (le stock ne descend jamais sous 0).
- Opération déjà décidée (`valide`/`rejete`) → 409.
- Rejet ou refus sans motif → 422.
- Demande de la secrétaire : produit inconnu, quantité invalide (≤ 0 pour un réapprovisionnement, < 0 pour une correction), motif vide → 422 ; approbation d'une demande déjà décidée ou annulée → 409 ; approbation par un non-admin ou par le demandeur → 403.
- Tentative de modification directe de `quantity` par un rôle non admin → 403 avec message explicite (« passez par une réception ou une avarie »).

## Tests

Backend (pytest, base de dev avec fixtures transactionnelles ; les tests doivent partir d'un état isolé comme `clean_staff_rules` pour ne pas dépendre de vraies données) :
- validation d'une réception : stock + mouvement(s) corrects, péremption = la plus proche, lot → `recu`, statut, audit, notification ; réception à plusieurs lignes ; livraison partielle ; quantités endommagée/perdue/défectueuse non ajoutées ;
- rejet : aucun changement de stock, motif obligatoire, le lot reste `livre` ;
- correction des quantités par le contrôleur : valeurs finales utilisées, audit old/new ;
- avarie : validation retire la quantité (atomique), refus si > stock, mouvement typé, rejet ;
- règle des deux comptes (auteur ≠ validateur, y compris admin) ;
- droits par route (Assistant, StockController, admin, secrétaire, ToxicoManager, autres) y compris l'écriture directe `/pharmacy` : `renew`/`DELETE` admin seulement, `PUT` quantité refusée hors admin, création avec quantité forcée à 0 ;
- **concurrence** : une validation de réception et une vente de caisse sur le même produit ne perdent aucune mise à jour (test déterministe : deux sessions ou ordre contrôlé) ;
- demande de la secrétaire : création sans effet sur le stock ; approbation réapprovisionnement et correction (mouvements `renew`/`update`, `stock_before/after`, stock correct après des ventes intermédiaires) ; refus ; annulation ; admin ≠ demandeur ; la secrétaire et le ToxicoManager reçoivent 403 sur `PUT quantité`, `renew`, `DELETE`, et la secrétaire sur la création de produit ; notification aux admins ;
- câblage réel : une réception créée par un vrai appel HTTP crée bien les notifications `stock_to_check` (test de bout en bout, pas seulement unitaire) ;
- migration : rôle `StockController` présent, CHECK/uniques, idempotence.
Frontend : build de production vert ; tests `node:test` pour toute fonction pure extraite (ex. règles de somme des lignes de réception).
Non-régression : vente en caisse, annulation de vente, alertes de péremption et KPI stock inchangés.

## Hors périmètre

- Stock par lot avec consommation FIFO (décision 6) ; coût de revient et prix de vente par lot ; gestion de commandes fournisseurs ; avaries « périmé » (la péremption est déjà suivie par les alertes) ; fabrication planifiée avec matières premières/recettes ; fonctionnement hors ligne des nouveaux écrans ; validation conditionnée à un seuil de quantité.

## Hypothèses à confirmer pendant la revue

- Aucune reconfirmation de mot de passe n'est exigée pour approuver (contrairement aux réductions) ; durcissement possible plus tard sur le même motif.
- Une demande de secrétaire porte sur **un** produit à la fois.

- `StockController` reçoit aussi les notifications `stock_to_check` ; l'`admin` aussi (supervision).
- Le contrôleur peut voir `GET /stock/movements` pour **toutes** les ventes (entrées et sorties), pas seulement ses validations — « ce qui entre ou sort ».
- L'`Assistant` voit `GET /stock/movements` (lecture) ; il ne voit pas la file « À contrôler » des autres tant qu'il n'a pas le rôle de validateur (il suit le statut de ses propres saisies dans ses listes).

## Révisions après exécution (2026-10-21)

Écarts et décisions pris pendant l'implémentation ; le plan et le code font foi en cas d'écart avec le texte ci-dessus.

1. **Actions sur un lot** : routes explicites `POST /stock/lots/{id}/deliver` et `POST /stock/lots/{id}/cancel` (au lieu d'un `PUT /stock/lots/{id}`).
2. **Un lot ne nourrit le stock qu'une fois** : à la création, un lot déjà lié à une réception `a_controler` ou `valide` est refusé (un frère `rejete` ne bloque pas) ; à la validation, le lot est verrouillé et doit être `livre`, sinon 409. Corrige un double comptage trouvé en revue (plusieurs réceptions pour un même lot).
3. **Annulation** d'une réception ou d'une avarie : statut final `rejete` avec le motif « annulé par l'auteur » (pas de statut `annule`, réservé aux lots et aux demandes d'ajustement). L'auteur ne peut pas **rejeter** sa propre opération (il l'annule).
4. **Listes de l'Assistant** : côté serveur, ses listes de réceptions et d'avaries sont forcées à « les miennes » ; une réception d'un autre est refusée (403). La secrétaire ne voit que ses demandes ; `admin` et `StockController` voient tout.
5. **Lecture élargie** : `GET /stock/products` (`StockController`, `admin`, `Assistant`) renvoie seulement `{id, name}` (le contrôleur n'a pas accès à `/pharmacy`) ; `current_quantity` est ajouté aux demandes d'ajustement pour l'affichage admin.
6. **Corrections du contrôleur** : une correction de lignes ne peut que **réduire ou redistribuer** (jamais ajouter une ligne ni dépasser le total actuel d'une ligne), pour qu'un seul compte ne puisse pas gonfler une entrée de stock puis la valider.
7. **Verrouillage des écritures de stock existantes** : la vente, l'édition de vente, l'annulation de vente (`caisse_repo`) et `renew_stock`/`update` avec quantité (`pharmacy_repo`) lisent désormais le produit sous `FOR UPDATE` (ordre croissant des identifiants), sinon une validation concurrente pouvait être écrasée silencieusement.
8. **Rôle `StockController` isolé côté serveur** : garde négative `deny_roles` sur `/appointments`, `/users/roles|specialties|doctors|managers` et `GET /labo/exams/{id}/params`.
9. **CI** : le rôle est ajouté à `ci/seed_application_roles.sql` (la CI ne rejoue pas les migrations).
10. **Notifications** : libellés par type, genre et statut (`refuse` pour les demandes d'ajustement, `rejete` pour les réceptions et avaries), repli sûr pour tout statut inconnu.
11. **Correction = écart (2026-10-21)** : `stock_adjustment_requests.stock_at_request` (migration 020) mémorise le stock à la demande ; à l'approbation d'une `correction`, `delta = quantité comptée − stock_at_request` est appliqué au stock **actuel** (409 si < 0) ; demandes sans cette valeur : ancien comportement absolu.
12. **Noms d'auteurs (2026-10-21)** : les dictionnaires portent `created_by_name`, `controlled_by_name`, `requested_by_name`, `decided_by_name` (une requête groupée par liste).
13. **Règle de ligne de stock** : `utils/item_types.py::touches_stock` unique pour la vente, la modification et l'annulation.
