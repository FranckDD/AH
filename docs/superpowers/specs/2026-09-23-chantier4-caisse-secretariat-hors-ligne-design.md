# Chantier 4, sous-projet 3 — Caisse/secrétariat hors-ligne

**Statut** : approuvé par l'utilisateur le 2026-09-23, prêt pour le plan d'implémentation.

## Contexte

Sous-projets 1 (Rendez-vous) et 2 (dossier patient, medecin/nurse) sont clos, chacun en 2
chantiers séparés (infra PowerSync d'abord, câblage UI ensuite) — le second a été nécessaire
parce que le premier laissait l'infrastructure inutilisée par tout écran, découvert seulement
par un test navigateur réel. **Leçon appliquée ici : un seul chantier, infra ET câblage UI
ensemble.**

Périmètre confirmé par l'utilisateur : rôle `secretaire` uniquement. Actions hors ligne :
encaissement (transaction + lignes), retrait de caisse, annulation (transaction et retrait),
paiement échelonné (versement + solde), et lecture (liste, total du jour, KPIs). Annuler/ajouter
un versement sur un enregistrement créé hors ligne mais pas encore synchronisé (pas de
`transaction_id`/`retrait_id` serveur réel) : impossible, bouton désactivé — même motif déjà
validé pour le lien prescription→consultation du sous-projet 2.

## Différence structurelle majeure avec les sous-projets précédents

**Aucune des 4 tables concernées (`caisse`, `caisse_item`, `caisse_retrait`,
`paiement_echelonne`) n'a de colonne `uuid`** — contrairement à `appointments`/`patients`/
`medical_records`/`prescriptions`, qui l'avaient déjà avant même le premier chantier PowerSync.
Ce sous-projet doit donc, en plus de tout le reste, **créer cette colonne par migration Alembic**
sur les 4 tables (même motif que `appointments.uuid`, migration `004_appointments_uuid_unique` :
`DEFAULT gen_random_uuid() NOT NULL` + index unique). **Application réelle contre la base de dev
nécessite l'accord explicite de l'utilisateur**, comme chaque migration précédente de ce projet.

`caisse_item` est un enfant de `caisse` (FK `transaction_id`, cascade) — une transaction créée
hors ligne avec ses lignes doit écrire la transaction ET ses lignes dans la même transaction
SQLite locale, la ligne référençant l'uuid local de la transaction parente (résolu au vrai
`transaction_id` serveur par le connecteur au moment de l'upload, même motif que
`prescriptions.medical_record_id`).

## Architecture

Réutilisation stricte du pattern déjà deux fois validé (RDV, dossier patient) :
- **Écriture** : toujours locale pour `secretaire` (`db.execute()`, en ligne comme hors ligne),
  jamais un chemin séparé "si en ligne alors HTTP sinon local" — PowerSync gère la
  synchronisation en arrière-plan de façon transparente.
- **Lecture** : HTTP par défaut (listes, KPIs, dashboard caisse), secours local en lecture seule
  uniquement sur échec réseau réel (`!err.response`, jamais sur une erreur applicative).
- **Connecteur** : extension de `DossierConnector.js` existant (décision utilisateur explicite,
  pas un nouveau connecteur séparé) — un seul `db.connect()`/une seule file CRUD pour toute
  l'application, cohérent avec le choix déjà fait pour RDV+dossier patient. Nouveaux cases
  `caisse:PUT`, `caisse_item:PUT` (traité comme partie de la même transaction locale que
  `caisse:PUT`, pas un upload séparé), `caisse_retrait:PUT`, `paiement_echelonne:PUT`. Pas de
  `PATCH`/`DELETE` pour aucune de ces tables (annulation = `POST /cancel` dédié via le gateway
  existant, pas une modification de ligne locale arbitraire).
- **Annulation** (transaction ou retrait) : reste un appel dédié (`CaisseGateway.cancelTransaction`/
  `cancelRetrait`), jamais une écriture locale PowerSync — nécessite toujours un vrai id serveur
  (cf. "Annuler avant sync : impossible" ci-dessus), donc jamais concerné par le mode hors ligne
  à proprement parler ; le bouton se désactive simplement tant que l'id local n'a pas de
  `server_id` confirmé.

## Décision spécifique à ce sous-projet — vente de médicaments/carnets hors ligne

**Découverte en cours de cadrage, absente du périmètre initial** : `CaisseRepository.create_transaction`
ne se limite pas à insérer une transaction — pour les lignes de type médicament/carnet, elle
vérifie le stock réel (`Pharmacy.quantity`) et lève `ValueError("Stock insuffisant")` si
insuffisant, puis déduit le stock et trace un `StockMovement`. Une écriture locale pure ne peut
pas reproduire cette vérification sans connaître le stock réel au moment de la vente.

**Décision utilisateur** : le centre fonctionne avec un seul poste secrétariat, les 2 secrétaires
se relaient (jamais simultanément) — pas de risque réel de concurrence sur le stock. En
conséquence :
- La vente de médicaments/carnets **reste autorisée hors ligne** (pas de restriction de type de
  ligne).
- **Le stock (`Pharmacy`) est synchronisé en lecture seule** (nouvelle table locale
  `pharmacy_stock`, nouveau stream `secretariat_pharmacy_stock`) — permet à l'écran de vente
  d'afficher le stock disponible et de bloquer côté client une vente qui dépasserait le stock
  *localement connu* (avertissement, pas un blocage serveur réel — le serveur reste la seule
  source de vérité et peut toujours refuser à la synchronisation si le stock a bougé entre-temps
  par un autre canal, par ex. un ajustement d'inventaire).
- **La déduction réelle du stock reste exclusivement côté serveur**, au moment de l'upload par
  `DossierConnector.js` (via l'endpoint `POST /caisse/` existant, inchangé) — jamais reproduite
  côté client.
- **Garde-fou obligatoire contre la perte silencieuse d'une vente** : le connecteur traite
  aujourd'hui toute erreur 400/404/409/422 comme définitivement "fatale" — l'opération est
  retirée de la file sans autre trace qu'un `console.error`. Pour `caisse:PUT` spécifiquement,
  ce comportement est **inacceptable** (une vente réellement effectuée au guichet ne doit jamais
  disparaître silencieusement si le stock a manqué entre-temps) : en cas d'échec fatal sur
  l'upload d'une transaction caisse, le connecteur doit persister un signal visible (nouvelle
  colonne locale `upload_error` sur la table `caisse`, affichée dans l'écran caisse comme un
  badge "échec de synchronisation — action requise") plutôt que de l'abandonner en silence.

## Composants côté écran (câblage UI, la partie manquante au sous-projet 2)

- `caisseStore.js::createInvoice` — écrit localement (transaction + lignes) pour `secretaire`,
  rafraîchit `transactions.value` depuis la table locale après écriture (même correctif que le
  registre Important I1 du sous-projet 2 — appliqué dès la conception cette fois, pas après
  coup).
- `caisseStore.js::addPayment`/`settleTransaction` — écriture locale pour `secretaire` (résout
  le `server_id` de la transaction visée, bouton désactivé si absent).
- `retraitStore.js::createRetrait` — écriture locale pour `secretaire`, même motif de
  rafraîchissement local après écriture.
- `CaisseList.vue`/`RetraitModal.vue`/écrans dashboard caisse (`daily_total`, KPIs) — secours de
  lecture locale sur échec réseau réel, même motif que `patientDossierStore.fetchDossierComplete`
  du sous-projet 2. Les agrégats calculés côté serveur (KPIs, distribution de paiements) ne sont
  **jamais recalculés côté client** — décision cohérente avec le sous-projet 2 (résumé clinique
  jamais recalculé) : en secours hors ligne, ces agrégats restent à leur dernière valeur connue
  ou vides, jamais une approximation client.

## Tests

Pas de suite automatisée frontend (comme les 2 sous-projets précédents) — vérification par build
production à chaque tâche, et un protocole de test navigateur réel à la charge de l'utilisateur
en fin de chantier, avec une **vraie coupure réseau** (pas seulement le toggle DevTools — leçon
tirée du registre N du sous-projet 2). Côté backend, tests automatisés pour le round-trip `uuid`
sur les 4 tables (même motif que `tests/test_medical_records_uuid.py`/
`tests/test_prescriptions_uuid.py`).

## Risques déjà identifiés

- 4 migrations au lieu d'1 (contre 1 seule pour le sous-projet 2, `medical_records` seul avait
  besoin d'une procédure stockée) — plus de surface de changement réel en base, à séquencer
  prudemment, une table à la fois, avec confirmation utilisateur à chaque application réelle.
- `caisse_item` en écriture locale multi-lignes dans la même transaction que `caisse` — le point
  le plus délicat de ce sous-projet, sans équivalent exact dans les 2 précédents (le lien
  prescription→consultation est un seul enfant, pas une liste).
- Paiement échelonné sur une transaction pas encore synchronisée : cas limite rare en pratique
  (un versement intervient généralement bien après la création, le temps que la sync ait eu
  lieu), mais le garde-fou "bouton désactivé sans server_id" doit être appliqué avec la même
  rigueur que pour la prescription liée à une consultation hors ligne.
- Stock affiché hors ligne = dernière valeur synchronisée, potentiellement périmée de quelques
  heures si le poste reste déconnecté longtemps — accepté (pas de concurrence réelle entre
  secrétaires), mais à rappeler à l'utilisateur si le protocole de test réel révèle un écart
  gênant en pratique.
