# Notifications + validation des réductions caisse — design

Date : 2026-09-25 · Statut : validé en brainstorming par l'utilisateur

## Contexte

Le centre de santé, humanitaire, autorise parfois une réduction ou une prise en
charge gratuite selon la situation financière du patient. Le circuit actuel
est entièrement manuel et papier : la secrétaire se déplace vers un
manager/`promoteur`, qui écrit « Okey » à la main sur la facture papier pour
valider, puis la secrétaire porte cette facture aux laborantins en affirmant
que la réduction est validée. **Un audit a révélé que beaucoup de ces « Okey »
manuscrits sont en réalité falsifiés** — c'est une faille de vol actif, pas un
simple confort à améliorer.

Ce chantier introduit :
1. Un **système de notifications** interne à l'application (générique,
   réutilisable au-delà de ce seul cas).
2. Un **workflow de validation des réductions** qui rend la falsification
   structurellement impossible : la décision n'est plus un papier, c'est une
   action d'un compte réel, horodatée, tracée dans l'audit existant.

Hors périmètre de ce chantier (chantier suivant, qui consommera ce résultat) :
le format exact du ticket 80mm/50mm imprimé à la caisse (imprimante
thermique POS) — ce chantier-ci garantit seulement que la donnée produite
(réduction validée, %, échéance, qui a décidé) est structurée pour être
reprise proprement sur ce ticket plus tard.

## Décisions utilisateur (2026-09-25)

1. La demande de réduction n'est possible que sur une **facture entièrement
   remplie** (patient + tous les articles + montant total calculé) — jamais
   sur un panier vide ou incomplet. Le montant est figé au moment de la
   demande.
2. **Option A retenue** pour le cycle de vie : la facture (transaction
   caisse) est créée immédiatement en base dans un état « en attente de
   validation », paiement/impression/modification bloqués — pas une facture
   fantôme qui n'existerait qu'après décision.
3. Le paiement échelonné (option "payer progressivement jusqu'à une date
   précisée") **peut être combiné** avec un pourcentage de réduction — pas
   mutuellement exclusif.
4. Si le manager choisi ne répond pas, la secrétaire peut **annuler et
   réassigner** la demande à un autre manager/`promoteur` — sans perdre
   l'historique de la tentative précédente.
5. Notification manager : **pastille sur l'icône notification mise à jour
   toutes les 30 secondes, plus un popup** dès qu'une nouvelle demande
   arrive, même sur un autre écran de l'application.
6. Retour secrétaire : une notification de type `discount_decided` est
   envoyée à la secrétaire dès que le manager tranche, pour qu'elle sache
   reprendre le patient au guichet sans avoir à revérifier en boucle.
7. **Reconfirmation par mot de passe** au moment où le manager valide sa
   décision (accepter, refuser, ou combiner % + échéance) — garde-fou contre
   quelqu'un qui validerait depuis un poste laissé ouvert par le manager.

## Architecture

### 1. Modèle de données

**Nouvelle table `notifications`** (générique, pas limitée aux réductions —
premier consommateur de ce système, pas le seul prévu) :

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `recipient_user_id` | FK `users.user_id` | qui doit voir cette notification |
| `type` | String(50) | `'discount_request'`, `'discount_decided'`, … (extensible) |
| `payload` | JSONB | contenu utile à l'affichage sans requête supplémentaire (ex : nom patient, montant, lien vers la facture) |
| `status` | String(20) | `'unread'` / `'read'`, défaut `'unread'` |
| `created_at` | DateTime | |
| `read_at` | DateTime nullable | |

**Nouvelle table `discount_requests`** :

| Colonne | Type | Note |
|---|---|---|
| `id` | Integer PK | |
| `transaction_id` | FK `caisse.transaction_id` | |
| `requested_by` | FK `users.user_id` | la secrétaire |
| `requested_to` | FK `users.user_id` | le manager/`promoteur` choisi |
| `original_amount` | Numeric(10,2) | montant figé au moment de la demande |
| `status` | String(20) | `'pending'` / `'approved'` / `'refused'` / `'cancelled'` |
| `decision_percent` | Integer nullable | 0/10/20/50/100 — `NULL` tant que pas décidé |
| `decision_echelonne_deadline` | Date nullable | combinable avec `decision_percent` (décision n°3) |
| `decided_by` | FK `users.user_id` nullable | |
| `decided_at` | DateTime nullable | |
| `created_at` | DateTime | |

Une seule ligne `status = 'pending'` autorisée par `transaction_id` à la
fois — le flux « annuler et réassigner » marque l'ancienne ligne
`'cancelled'` puis en crée une nouvelle, jamais de mutation destructive de
l'historique.

**`caisse.status`** gagne une nouvelle valeur : `'pending_approval'` — posée
à la création de la demande, retirée (repasse à `'active'`) à la décision.
Tant que ce statut est actif :
- Les endpoints existants de modification/annulation de la facture
  (`update_transaction`, `cancel_transaction`, etc. dans
  `caisse_controller.py`/`caisse_repo.py`) doivent **refuser toute action**
  (422 ou 409) — c'est le garde-fou qui rend la faille structurellement
  impossible, pas juste dissuadée. Sans ça, quelqu'un pourrait éditer la
  facture par un autre écran pendant l'attente.
- L'encaissement (`add_installment_payment`, l'écran "Encaisser") est
  également bloqué.

À la décision (approuvée) : `caisse.amount` est mis à jour au montant
effectif (`original_amount × (1 - decision_percent/100)`) — la machinerie
existante de paiement/PDF/affichage continue de lire `caisse.amount`
directement, aucun autre consommateur de ce champ n'a besoin de connaître le
concept de réduction. `discount_requests.original_amount` reste la source
de vérité pour l'audit et le futur ticket (afficher "Prix normal / Réduction
validée par X / Montant dû").

Si `decision_echelonne_deadline` est posée, elle est la seule source de
vérité pour l'échéance — la table `paiement_echelonne` existante
(historique des versements réellement effectués) n'est pas modifiée dans sa
structure, juste consultée aux côtés de cette échéance pour calculer le
solde restant face à la date limite.

**`audit_user_actions`** (table déjà existante, déjà utilisée ailleurs dans
le projet) reçoit une entrée à chaque décision (qui, quand, quel
pourcentage/échéance, sur quelle facture) — c'est le point le plus important
de cette conception : une réduction validée n'est plus falsifiable, elle
existe dans le même système d'audit qui a révélé la faille initiale.

### 2. Backend — endpoints

- `POST /discount-requests` (rôle `secretaire`) : crée la demande sur une
  facture `active` et entièrement remplie, pose `caisse.status =
  'pending_approval'`, crée la notification vers `requested_to`.
- `POST /discount-requests/{id}/cancel` (rôle `secretaire`, doit être
  l'auteur) : marque `'cancelled'`, n'affecte pas `caisse.status`.
- `POST /discount-requests/{id}/decide` (rôle `admin`/`promoteur`, doit être
  le `requested_to`) : payload `{decision_percent, decision_echelonne_deadline,
  refuse: bool, password}`. `refuse: true` est exclusif — si posé,
  `decision_percent`/`decision_echelonne_deadline` doivent être absents ou
  nuls (422 sinon, pour éviter toute ambiguïté "refusé mais avec une
  réduction quand même"). `status` final : `'refused'` uniquement si
  `refuse: true` ; `'approved'` dès qu'au moins un des deux (`decision_percent
  > 0` et/ou `decision_echelonne_deadline` posée) est accordé — un
  échéancier seul, sans pourcentage, compte comme approuvé. Rejoue
  `auth_ctrl.authenticate(current_user.username, password)` (primitive déjà
  existante, utilisée au login) avant tout — échec → 403, rien n'est
  enregistré. Succès → met à jour `discount_requests`, recalcule
  `caisse.amount` si un pourcentage a été accordé (inchangé si échéancier
  seul), repasse `caisse.status = 'active'` dans tous les cas (approuvé ou
  refusé), écrit dans `audit_user_actions`, notifie `requested_by`.
- `GET /notifications?status=unread` (tout rôle authentifié) : liste des
  notifications de l'utilisateur courant — interrogé par le poller frontend.
- `POST /notifications/{id}/read` : marque comme lue.

### 3. Frontend

- `notificationStore.js` (nouveau, Pinia) : interroge `GET
  /notifications?status=unread` toutes les 30 secondes tant qu'un utilisateur
  `admin`/`promoteur`/`secretaire` est connecté. Déclenche un popup une seule
  fois par notification jamais vue (pas à chaque poll). Pastille sur l'icône
  notification dans le layout partagé (`MainLayout.vue` ou équivalent).
- `CaisseInvoiceModal.vue` (existant) : nouveau bouton « Demander une
  réduction », actif sous les mêmes conditions que le bouton "Encaisser"
  actuel. Affiche l'état "En attente de validation par {nom}" quand
  `caisse.status === 'pending_approval'`, avec bouton "Annuler et
  réassigner".
- Nouvel écran côté manager (`admin`/`promoteur`) : liste des demandes en
  attente (patient, montant original, articles, demandeur), formulaire de
  décision (pourcentage, date d'échéance, case "Refuser"), champ mot de
  passe de reconfirmation avant validation.

## Gestion d'erreurs

- Décision avec mot de passe incorrect : 403, aucune modification, message
  clair côté manager.
- Tentative de modifier/annuler/encaisser une facture `pending_approval` par
  un autre écran que le flux de décision : 409, message explicite.
- Tentative de créer une deuxième demande `pending` sur la même facture :
  409 (le flux "annuler et réassigner" gère ça correctement en annulant
  d'abord).
- Décision par un utilisateur qui n'est pas le `requested_to` de la demande :
  403.
- Annulation par quelqu'un d'autre que `requested_by` : 403.

## Tests

Backend (pytest) :
- Création de demande verrouille bien la facture (modification/annulation/
  encaissement refusés pendant `pending_approval`).
- Décision avec mot de passe correct vs incorrect.
- Annulation + réassignation : ancienne ligne `cancelled`, nouvelle `pending`,
  jamais deux `pending` actives simultanément.
- Refus explicite (`refuse: true`) libère la facture sans changer
  `caisse.amount`.
- Combinaison pourcentage + échéance sur une même décision.
- Entrée correcte dans `audit_user_actions` à chaque décision.
- `GET /notifications` ne renvoie que les notifications du destinataire
  courant.

Frontend : build production vert, `notificationStore.js` ne déclenche le
popup qu'une fois par notification (pas à chaque poll de 30s).

Non-régression : toute facture qui ne passe jamais par "Demander une
réduction" garde exactement le comportement actuel — aucune route/table
caisse existante n'a son comportement par défaut modifié.
