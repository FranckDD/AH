# Chantier 7b — Caisse & Retrait : design

**Registre couvert :** `L3b` (Caisse limitée à une recette à montant unique) et `L3e` (Retrait de caisse sans écran dédié), `docs/superpowers/SUIVI-AVANCEMENT.md`. Bugs backend corrigés en même temps : registre `F` (F1-F6), même document.

**Ordre du chantier 7 confirmé par l'utilisateur (2026-09-21) :** `7c` (fait) → `7b` (ce document) → `L4b-e` (nettoyage des gardes de rôle) → `7d`.

## 1. Constat

Le back-end porte déjà tout le moteur métier de la caisse et du retrait :
facture multi-lignes liée au stock (`Pharmacy`) ou à une consultation
spirituelle (`ConsultationSpirituel`), avance/versements échelonnés,
solde, annulation, export PDF, et pour le retrait : création avec
justification/catégorie/mode de paiement, annulation avec justification,
recherche paginée. **Aucune de ces capacités n'est appelée depuis le web** :
`ah2-admin-web/src/components/finance/FinanceModal.vue` ne crée qu'une
transaction à un seul montant (`FinanceGateway.createIncome`/`createExpense`,
`ah2-admin-web/src/services/FinanceGateway.js:60-72,101-111`), sans lien
patient réel, sans lignes, sans avance, sans possibilité d'annuler une
saisie erronée. Aucun écran de retrait n'existe (aucune route `/retrait`
dans `ah2-admin-web/src/router/index.js`).

En creusant le code que cette UI va appeler, un registre de bugs déjà
documenté (`SUIVI-AVANCEMENT.md`, section F, découverts au chantier 2d-4,
jamais corrigés) touche exactement ces endpoints :

| # | Bug | Gravité |
|---|---|---|
| F1 | `normalize_caisse_data()` (`api_backend/backend_app/routes/caisse/mapping.py:38-39`) calcule `amount_due = amount + advance_amount` et `amount_paid = amount` — inversés. Avec `amount=100, advance_amount=30` : `amount_due` vaut 130 (attendu 70), `amount_paid` vaut 100 (attendu 30). | Élevée |
| F2 | `DELETE /caisse/{id}` sur un id inexistant renvoie 204 au lieu de 404 (`caisse_endpoints.py::delete_transaction` ne vérifie jamais le retour de `delete_transaction()`, qui échoue silencieusement). | Faible |
| F3 | `POST /caisse/{id}/payment` ne déclare pas de `response_model` — renvoie `{}` (l'objet ORM `PaiementEchelonne` n'est pas sérialisable sans schéma), alors que `PaymentEchelonneOut` existe déjà dans `caisse_schemas.py:91-102`, juste jamais branché. | Faible |
| F4 | `get_total_remaining_due()` (`repositories/caisse_repo.py:774`) filtre implicitement `status='active'` même sans paramètre explicite, contrairement à `get_total_transactions()`/`get_total_payments()`. | Moyenne |
| F5 | Annuler une transaction Caisse déjà annulée réussit silencieusement (200), alors qu'annuler un Retrait déjà annulé est explicitement refusé (400). | Faible |
| F6 | `update_transaction()` (`repositories/caisse_repo.py:341-424`) supprime **inconditionnellement** toutes les lignes existantes avant même de vérifier si le payload contient `"items"`, puis ne réinsère que `data.get("items", [])`. Un `PUT` partiel qui omet `items` (ex. `{"note": "..."}`) supprime donc définitivement toutes les lignes de facture, et pour les lignes médicament/carnet, restaure le stock sans jamais le redéduire (inflation de stock fantôme). | **La plus élevée du registre F** |

Construire un écran "reste à payer" et des actions d'édition sur des
calculs et un comportement d'update faux serait trompeur dès le premier
jour. F1-F6 sont donc corrigés dans ce même sous-projet (décision
utilisateur, 2026-09-21).

## 2. Périmètre

**Dans le périmètre :**
1. Corrections F1-F6.
2. Annulation Caisse avec justification obligatoire (migration + colonnes,
   miroir de `caisse_retrait`).
3. Écran Caisse opérationnel (`/secretariat/caisse`, remplace l'actuel) :
   liste des transactions Caisse avec reste à payer, actions (versement,
   solde, annulation, téléchargement facture), création d'une facture
   multi-lignes (patient recherché ou nom libre ; lignes Pharmacie /
   Consultation spirituelle / Service libre ; avance initiale optionnelle).
4. Écran Retrait (`/secretariat/retrait`, nouveau) : liste avec filtres,
   création (montant, justification, catégorie, mode de paiement),
   annulation avec justification.
5. Entrée de menu "Retrait" dans `SecretaireLayout.vue`.

**Hors périmètre (décision utilisateur, 2026-09-21) :**
- `/dashboard/finance` (admin) : inchangé, reste le journal unifié en
  lecture du chantier 5 (`FinancialList.vue` + `FinanceModal.vue` tels
  quels). Aucun écran opérationnel n'est branché côté admin dans ce
  chantier.
- Export PDF/CSV en masse (`L3d`) — sous-projet séparé, non traité ici.
  Le téléchargement de facture *individuelle* (`GET
  /caisse/{id}/invoice/download`) est dans le périmètre : c'est un simple
  bouton sur une route déjà fonctionnelle, pas un nouveau sous-système
  d'export.
- Le nettoyage du dead-code procédure stockée à 19 paramètres (parqué au
  chantier `L4b-e`) et toute autre dette déjà parquée par 6/7a/7c ne sont
  pas repris ici.

## 3. Corrections backend (registre F)

- **F1** — `mapping.py::normalize_caisse_data` :
  `"amount_due": lambda r: parse_decimal(get_field(r, "amount") - get_field(r, "advance_amount"))`,
  `"amount_paid": lambda r: parse_decimal(get_field(r, "advance_amount"))`.
- **F6** — `caisse_repo.py::update_transaction` : le rétablissement de
  stock + suppression des lignes existantes, et la réinsertion, ne
  s'exécutent que si `"items" in data`. Absent de `data` = lignes et
  stock inchangés (même sémantique que `COALESCE` déjà utilisée ailleurs
  dans le projet — absent veut dire "ne pas toucher", `[]` explicite veut
  dire "vider").
- **F5** — `caisse_repo.py::cancel_transaction` lève `ValueError("Cette
  transaction est déjà annulée.")` si `tx.status == 'cancelled'`, comme
  `caisse_retrait_repo.py::cancel_with_justification`. L'endpoint
  `caisse_endpoints.py::cancel_transaction` traduit déjà tout `ValueError`
  en 400 — aucun changement requis côté route pour ce point.
- **F2** — `caisse_endpoints.py::delete_transaction` : si
  `caisse_ctrl.delete_transaction(transaction_id)` renvoie `None` (id
  inexistant), lever `HTTPException(404)` avant de renvoyer `None`.
- **F3** — `caisse_endpoints.py::add_payment` : ajouter
  `response_model=PaymentEchelonneOut` (déjà importé dans
  `caisse_schemas.py`) au décorateur `@router.post("/{transaction_id}/payment", ...)`.
- **F4** — `caisse_repo.py::get_total_remaining_due` :
  `query.filter(Caisse.status == status)` seulement `if status:`, comme
  `get_total_transactions`/`get_total_payments`. Sans filtre explicite, la
  somme porte sur toutes les transactions (actives + annulées) — décision
  cohérente avec les deux méthodes voisines, prise ici sans repasser par
  l'utilisateur (c'est exactement l'écart que F4 documente).

## 4. Annulation Caisse avec justification

Nouvelle migration Alembic, miroir exact des colonnes déjà présentes sur
`caisse_retrait` :

```sql
ALTER TABLE public.caisse
    ADD COLUMN IF NOT EXISTS cancelled_by integer REFERENCES public.users(user_id),
    ADD COLUMN IF NOT EXISTS cancelled_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS cancel_justification text;
```

`models/caisse.py::Caisse` gagne les 3 colonnes correspondantes (types
identiques à `models/retrait.py::CaisseRetrait`).

`repositories/caisse_repo.py::cancel_transaction(transaction_id,
current_user, justification: str)` : signature étendue avec un paramètre
`justification` obligatoire, enregistre `cancelled_by`, `cancelled_at`,
`cancel_justification` en plus du changement de statut et de la restauration
de stock déjà en place. `controller/caisse_controller.py::cancel_transaction`
répercute le nouveau paramètre. `caisse_endpoints.py::cancel_transaction`
reçoit `cancel_justification: str = Body(..., embed=True)`, exactement
comme `retrait_endpoints.py::cancel_retrait` (même contrat API entre les
deux modules — referme aussi une partie de l'incohérence F5).

`normalize_caisse_data` gagne les 3 champs en sortie (`cancelled_by`,
`cancelled_at`, `cancel_justification`), miroir de
`normalize_retrait_data`.

Cette migration touche une table de production réelle : comme pour les
migrations des chantiers précédents, elle est appliquée à la base locale
AH2 seulement après confirmation explicite de l'utilisateur au moment de
l'exécution.

## 5. Écran Caisse (`/secretariat/caisse`)

### 5.1 Liste

Nouvelle vue `ah2-admin-web/src/views/modules/finance/CaisseList.vue`
(remplace `FinancialList.vue` sur cette route ; `FinancialList.vue`
lui-même n'est pas modifié, il reste utilisé tel quel par
`/dashboard/finance`). Alimentée par `GET /caisse/` (déjà paginé,
filtrable par `term`/`payment_method`/`status`/dates — aucun changement
d'API nécessaire côté liste).

Colonnes : date, patient (nom réel via `patient_name` ou `patient_label`),
type de transaction, montant total, payé (`amount_paid`, corrigé F1),
reste dû (`amount_due`, corrigé F1), statut (badge actif/annulé), actions.

Actions par ligne (visibilité conditionnelle) :
- **Voir le détail** — panneau/modal listant les lignes de facture
  (`items`) et l'historique des versements. Utilise les données déjà
  renvoyées par `GET /caisse/{id}` (`items`) ; l'historique des versements
  (table `PaiementEchelonne`) n'a aujourd'hui aucun endpoint de lecture
  dédié — hors périmètre, le détail affiche les lignes de facture et le
  couple payé/dû, pas le détail des versements individuels.
- **Ajouter un versement** — visible si `status === 'active'` et
  `amount_due > 0`. Petit formulaire (montant, mode de paiement, note
  optionnelle) → `POST /caisse/{id}/payment`.
- **Solder** — visible dans les mêmes conditions. Confirmation puis
  `POST /caisse/{id}/settle`.
- **Annuler** — visible si `status === 'active'`. Modal avec justification
  obligatoire → `POST /caisse/{id}/cancel` (nouveau contrat, section 4).
- **Télécharger la facture** — toujours visible. `GET
  /caisse/{id}/invoice/download`, ouverture directe du PDF renvoyé (déjà
  fonctionnel côté back-end, juste jamais appelé depuis le web).

KPI en tête d'écran : reprend les trois cartes déjà utilisées par
`FinancialList.vue` (encaissé, reste dû, nombre de transactions) via
`GET /caisse/dashboard/caisse/kpis` (`FinancialKpiSchema`, déjà exposé,
déjà correct — indépendant du bug F1 qui ne touche que le mapping par
transaction).

### 5.2 Création d'une facture

Nouveau composant `ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue`,
remplace l'usage de `FinanceModal.vue` sur cette route (`FinanceModal.vue`
n'est pas supprimé, il reste utilisé par `/dashboard/finance`).

**Patient** : recherche par nom (réutilise le pattern déjà établi par
`ToxicoGateway.searchPatients` — `GET /patients/?search=...&per_page=8`)
avec sélection d'un patient existant (`patient_id`), ou repli sur un champ
texte libre (`patient_label`) si la personne n'a pas de dossier. Les deux
champs existent déjà côté schéma et repository (`Caisse.patient_id`
nullable, `Caisse.patient_label`).

**Lignes de facture** (au moins une ligne requise, ou une avance > 0 —
règle déjà appliquée par `CaisseController.create_transaction`), trois
types sélectionnables par ligne :
- **Pharmacie** (médicament ou carnet) — recherche produit (`GET
  /pharmacy/?term=...`, déjà utilisé par `stockStore.js`), quantité,
  prix unitaire pré-rempli depuis `product.price` (modifiable), stock
  disponible affiché. `item_type` envoyé : `"Médicament"`. La déduction de
  stock est gérée par le back-end (`caisse_repo.py::create_transaction`),
  aucune double logique côté frontend.
- **Consultation spirituelle** — recherche consultation (`GET
  /cs/?search=...`, déjà utilisé par `ConsultationGateway.fetchConsultations`),
  quantité fixée à 1, prix unitaire libre (pré-rempli avec
  `fr_amount_paid` de la consultation si renseigné). `item_type` envoyé :
  `"Consultation"` — le back-end vérifie déjà l'existence de la
  consultation référencée.
- **Service libre** — libellé + prix unitaire + quantité, sans recherche
  ni vérification de référence. `item_type` envoyé : `"Service"`,
  `item_ref_id` : `0` (aucune contrainte NOT NULL sur autre chose qu'un
  entier ; `0` n'est jamais un id réel de `Pharmacy`/`ConsultationSpirituel`
  et le repo ne fait aucune vérification pour ce type de ligne — miroir
  exact du fixture déjà utilisé par `tests/test_caisse.py`, qui envoie
  `item_type: "Service", item_ref_id: 1`).

Le total (`amount`) est calculé côté client comme la somme des
`line_total` et affiché en lecture seule (le back-end revalide déjà cette
somme et rejette toute incohérence — `CaisseController.create_transaction`,
"Incohérence montant").

**Avance initiale** (`advance_amount`, optionnelle, ≤ `amount`) et
**mode de paiement** (réutilise les mêmes options que `FinanceModal.vue` :
Espèces/Mobile Money/Virement/Chèque).

**Catégorie** (`transaction_type`, header de facture) : réutilise la
liste `INCOME` déjà définie dans `FinanceModal.vue`
(`CONSULTATION`/`PHARMACY`/`HOSPITALIZATION`/`LAB`/`DETOX`/`OTHER`).

Soumission → `POST /caisse/` avec le payload complet
(`patient_id`/`patient_label`, `amount`, `advance_amount`,
`payment_method`, `transaction_type`, `note`, `items[]`) — c'est
exactement le contrat déjà accepté par `CaisseController.create_transaction`,
aucun changement d'API nécessaire pour la création.

## 6. Écran Retrait (`/secretariat/retrait`)

Nouvelle vue `ah2-admin-web/src/views/modules/finance/RetraitList.vue` et
nouvelle route dans `router/index.js` (bloc `/secretariat`, même pattern
que les routes voisines, `roles: [ROLES.SECRETAIRE]`).

**Liste** : `GET /retrait/search` (déjà paginé, filtrable par
`term`/`status`/dates — `FinanceGateway.fetchExpenses` l'appelle déjà pour
le journal unifié, aucun changement d'API). Colonnes : date, montant,
justification, catégorie, mode de paiement, statut, actions.

**Action Annuler** (visible si `status === 'active'`) : modal avec
justification obligatoire → `POST /retrait/{id}/cancel` (contrat déjà en
place, `cancel_justification` en body).

**Création** : nouveau composant
`ah2-admin-web/src/components/caisse/RetraitModal.vue` — montant,
justification (obligatoire), catégorie, mode de paiement → `POST
/retrait/` (contrat déjà en place).

**Nav** : nouvelle entrée `secretariat.nav.retrait` dans
`SecretaireLayout.vue::menuItems`, après l'entrée Caisse existante.

## 7. Fichiers touchés (résumé)

**Backend :**
- `api_backend/backend_app/routes/caisse/mapping.py` (F1)
- `repositories/caisse_repo.py` (F4, F5, F6, `cancel_transaction` étendu)
- `api_backend/backend_app/routes/caisse/caisse_endpoints.py` (F2, F3,
  `cancel_transaction` accepte `cancel_justification`)
- `controller/caisse_controller.py` (`cancel_transaction` répercute
  `justification`)
- `models/caisse.py` (3 nouvelles colonnes)
- `alembic/versions/006_caisse_cancel_justification.py` (nouvelle
  migration)
- `ci/schema_only.sql` (régénéré après application de la migration)

**Frontend :**
- `ah2-admin-web/src/views/modules/finance/CaisseList.vue` (nouveau)
- `ah2-admin-web/src/views/modules/finance/RetraitList.vue` (nouveau)
- `ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue` (nouveau)
- `ah2-admin-web/src/components/caisse/CaisseCancelModal.vue` (nouveau,
  petit — réutilisé pour Caisse ET Retrait, un seul champ justification)
- `ah2-admin-web/src/components/caisse/RetraitModal.vue` (nouveau)
- `ah2-admin-web/src/services/CaisseGateway.js` (nouveau — recherche
  patient/produit/consultation, création facture, versement, solde,
  annulation, téléchargement facture, création/annulation retrait ;
  `FinanceGateway.js` n'est pas modifié, il reste dédié au journal unifié
  de `/dashboard/finance`)
- `ah2-admin-web/src/stores/caisseStore.js` (nouveau)
- `ah2-admin-web/src/stores/retraitStore.js` (nouveau)
- `ah2-admin-web/src/router/index.js` (route `/secretariat/caisse`
  repointée vers `CaisseList.vue`, nouvelle route `/secretariat/retrait`)
- `ah2-admin-web/src/components/layout/SecretaireLayout.vue` (nouvelle
  entrée de menu)
- `ah2-admin-web/src/i18n.js` (nouvelles clés `caisse.*`, `retrait.*`,
  fr + en)

**Tests :**
- `tests/test_caisse.py` — mise à jour des tests F1/F6 déjà présents
  (aujourd'hui ils *documentent* le bug, ils doivent désormais vérifier le
  comportement corrigé) ; nouveaux tests pour F2/F3/F4/F5 et pour
  `cancel_transaction` avec justification.
- `tests/test_retrait.py` — inchangé sauf si un couplage émerge à
  l'exécution.

## 8. Rôles et accès

Aucun changement de garde de rôle : `/caisse/*` et `/retrait/*` restent
`role_required("secretaire", "admin")` côté back-end (inchangé) ; les
nouvelles routes web `/secretariat/caisse` et `/secretariat/retrait`
restent `roles: [ROLES.SECRETAIRE]` (même garde que l'existant sur cette
fenêtre). L'audit et les gardes de rôle divergentes entre interface et
serveur sont le sujet du prochain sous-projet (`L4b-e`), pas de celui-ci.

## 9. Erreurs et cas limites

- Stock insuffisant sur une ligne Pharmacie : le back-end rejette déjà
  (400, "Stock insuffisant pour ...") — le formulaire affiche l'erreur
  telle quelle, pas de vérification dupliquée côté client au-delà d'un
  affichage informatif du stock disponible.
  Incohérence montant (somme des lignes ≠ total) : déjà rejetée par le
  back-end (400) — même traitement.
- Avance supérieure au total : validée côté client avant soumission
  (`advance_amount <= amount`), en plus de toute validation back-end
  existante.
- Versement dépassant le reste dû : déjà rejeté par le back-end (400,
  "Montant trop élevé...") — affiché tel quel.
- Annulation d'une transaction déjà annulée : après F5, rejetée (400) —
  le bouton Annuler est de toute façon masqué pour `status !== 'active'`,
  donc ce cas ne devrait survenir qu'en cas de double-clic/onglet
  concurrent ; l'erreur 400 est affichée telle quelle, pas de traitement
  spécial.

## 10. Auto-review

- **Placeholders** : aucun "TBD" — chaque item du plan référence un
  fichier et un comportement réels, vérifiés dans le code actuel avant
  rédaction (contrats API, noms de colonnes, gateways existantes).
- **Cohérence interne** : la section 3 (corrections F) précède les
  sections 5-6 qui en dépendent (`amount_due`/`amount_paid` corrects,
  `cancel_transaction` avec justification) — ordre respecté dans le plan
  d'implémentation à venir.
- **Portée** : un seul sous-projet cohérent (Caisse + Retrait,
  explicitement groupés par l'utilisateur dans l'ordre confirmé) ; pas de
  décomposition supplémentaire nécessaire.
- **Ambiguïté** : le choix `item_ref_id: 0` pour les lignes "Service
  libre" est documenté explicitement (section 5.2) pour éviter toute
  hésitation à l'implémentation — c'est le même choix que le fixture de
  test déjà présent sur `HEAD`, pas une invention de ce spec.
