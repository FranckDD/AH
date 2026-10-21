# Stock du laboratoire — conception (2026-10-21)

## Intention

Aujourd'hui, quand les réactifs du labo vont finir, la technicienne prévient de vive voix le manager et le promoteur ; la direction passe commande ; le livreur arrive avec une fiche papier (n° de facture, fournisseur, tableau : n°, désignation, conditionnement, quantité, prix unitaire, prix total) ; le promoteur ou le contrôleur coche la liste en vérifiant produits et quantités. Rien n'est tracé, et personne ne voit à l'avance ce qui va manquer.

L'application doit permettre : enregistrer facilement les produits du labo, **suivre leur stock**, **signaler** (seuil atteint, péremption proche, signalement de la technicienne), **lister** ce qui est à commander, **notifier** les décideurs, **suivre la commande** jusqu'à la livraison, et **réceptionner** la livraison comme sur la fiche papier. Les montants reçus alimentent un suivi des dépenses du labo.

Succès : la technicienne n'a plus à courir après le manager ; le promoteur voit d'un coup d'œil ce qu'il faut commander et ce qui est déjà en route ; le contrôleur enregistre une livraison en quelques minutes **depuis un téléphone**.

## Décisions de l'utilisateur (ce qu'il a dit)

1. **Stock séparé de la caisse et de la pharmacie.** Ces produits ne passent jamais par la caisse et n'entrent pas dans le stock `pharmacy`. Tables et routes propres, aucune modification de `pharmacy`, `caisse` ni `stock_movements`.
2. **Pas de saisie de consommation à chaque ouverture de flacon** (« trop pour la technicienne »). Le niveau de stock baisse par un **comptage hebdomadaire rapide** : la technicienne tape ce qu'elle voit en rayon.
3. **Réception** : saisie et validation **en une seule fois** par le **contrôleur** (`StockController`) ; le **promoteur** peut le faire à sa place s'il est absent (et l'admin). Le **manager (`ToxicoManager`) ne saisit pas de réception.** Pas de règle des deux comptes ici (la même personne saisit en cochant devant les produits).
4. **Produits préenregistrés** : le contrôleur choisit dans une liste (avec recherche) au lieu de retaper ; il peut créer un produit manquant à la volée.
5. **Responsive** : l'écran de réception (et celui du comptage) doit être confortable sur **téléphone et tablette**, pas seulement sur PC.
6. **Qui crée un produit et fixe son seuil** : la **technicienne** (`laborantin`) et le **contrôleur** ; **le promoteur et le manager n'en créent pas.** L'admin a tous les droits.
7. **Suivi de commande dans l'application** : statut « commandé » + date de livraison attendue, visible de la technicienne.
8. **Signalement** par la technicienne → notification au manager et au promoteur, et l'article rejoint la liste « à commander ».
9. **Alertes** : seuil atteint (listé + notifié), péremption proche.
10. **Produits exonérés de taxes** : aucun champ de taxe.
11. **Suivi des dépenses utile** : montants reçus par mois et par fournisseur, évolution du prix d'un produit.

## Droits

| Rôle | Peut |
|---|---|
| `laborantin` | créer/modifier un produit et son seuil ; faire le comptage ; signaler « bientôt fini / fini » ; voir stocks, liste « à commander » et commandes en cours (lecture) |
| `StockController` | créer/modifier un produit ; saisir **et** valider une réception ; voir stocks, historique, liste « à commander » |
| `promoteur` | saisir et valider une réception ; recevoir les notifications ; voir stocks/dépenses ; marquer « commandé » (date attendue) ; **ne crée pas de produit** |
| `ToxicoManager` | recevoir les notifications ; voir stocks/dépenses ; marquer « commandé » ; **ni réception ni création de produit** |
| `admin` | tout (choix par défaut) |
| autres rôles | aucun accès (choix par défaut) |

Le rôle `StockController` est aujourd'hui limité à 2 entrées de menu (« À contrôler », « Mouvements ») et muselé côté serveur par `deny_roles` : il faut lui ouvrir les écrans du stock labo seulement, sans lui rendre l'accès aux autres routes.

## Modèle de données (nouvelles tables, préfixe `lab_stock_`)

- **`lab_stock_products`** : nom, conditionnement (texte : « boîte de 100 tests »), `alert_threshold` (entier, en unités de conditionnement), fournisseur habituel (texte, optionnel), `quantity` (entier ≥ 0, stock courant), `last_counted_at`, `is_active`, créé par/le. Le nom est unique parmi les actifs (insensible à la casse).
- **`lab_stock_receipts`** : n° de facture, fournisseur, date de livraison, total, statut (`valide`, `annule`), saisi/validé par (même personne), motif d'annulation. Une réception est créée directement validée.
- **`lab_stock_receipt_lines`** : réception, produit, quantité commandée (optionnelle), quantité reçue (> 0), prix unitaire, total de ligne, **n° de lot** et **date de péremption** (obligatoires : suivi par lot comme dans les pratiques européennes — proposition du concepteur, acceptée pendant la discussion), remarque.
- **`lab_stock_counts`** + **`lab_stock_count_lines`** : un comptage (qui, quand) et pour chaque produit compté : quantité avant, quantité comptée. Le comptage **fixe** le stock à la valeur comptée (en rayon, pas de ventes concurrentes ; verrou de ligne tout de même).
- **`lab_stock_movements`** : produit, variation, type (`reception`, `comptage`, `annulation_reception`), référence, utilisateur, quantité après, date.
- **`lab_stock_requests`** (signalement / commande) : produit, origine (`signalement`, `seuil`, `peremption`), niveau (`bientot_fini`, `fini`), statut (`a_commander`, `commande`, `recu`, `annule`), demandé par, commandé par, date de livraison attendue, dates. **Une seule demande ouverte** (`a_commander` ou `commande`) par produit (index unique partiel). Elle passe à `recu` automatiquement quand une réception validée contient le produit.

Les contraintes CHECK de valeurs fermées vont dans la migration **et** dans `ci/schema_only.sql` (la CI ne rejoue pas les migrations ; vérifier les CHECK du schéma avant de décrire un champ comme libre). Dernière révision Alembic actuelle : `020_adjustment_stock_at_request`.

## Comportements

- **Réception** : en-tête (n° de facture, fournisseur, date), puis lignes choisies dans la liste des produits (recherche, ou création d'un produit manquant si le rôle y a droit), qté reçue, lot, péremption, prix. À la validation, dans **une transaction** : `quantity += reçu` (verrou de ligne, ordre d'identifiant croissant), mouvements `reception`, demandes ouvertes des produits concernés → `recu`, notification à la technicienne (créatrice des signalements) et audit. Une facture déjà enregistrée avec le même couple (fournisseur, n° de facture) est refusée (409). Annulation d'une réception : **admin seulement**, avec motif ; elle retire les quantités si le stock est suffisant (409 sinon).
- **Comptage hebdomadaire** : écran mobile avec la liste des produits actifs et un champ numérique par produit ; la technicienne ne saisit que ce qui a changé ou tout. À l'envoi : stock fixé, mouvement `comptage` (écart tracé), et pour chaque produit passé **à ou sous le seuil** : création de la demande `seuil` si aucune n'est ouverte + notification au promoteur et au manager. Un **rappel** est affiché (bandeau + notification dédupliquée à la technicienne) si le dernier comptage a plus de 7 jours.
- **Signalement** : bouton « bientôt fini / fini » par produit (technicienne) → demande `signalement` (si aucune ouverte, sinon on met le niveau à jour) + notification au promoteur et au manager.
- **Liste « à commander »** : toutes les demandes ouvertes avec produit, stock, seuil, origine, statut ; **marquer commandé** (promoteur, manager, admin) avec date de livraison attendue (modifiable) ; **annuler** une demande (mêmes rôles, motif). La technicienne voit le statut et la date.
- **Péremption** : un lot reçu dont la date est à **60 jours ou moins** (réglable en constante) alors que le produit a du stock est signalé dans la liste d'alertes et par notification (dédupliquée par lot). Calculé à la consultation et au comptage : il n'y a aucun planificateur dans le projet (pas de Celery beat), on n'en ajoute pas. Limite assumée : le comptage étant par produit, on ne sait pas si un lot précis est déjà consommé.
- **Dépenses** : montants reçus par mois, par fournisseur et total ; historique du prix unitaire d'un produit (par réception). Lecture pour promoteur, manager, admin.
- **Notifications** : réutiliser le système existant (types `lab_stock_signal`, `lab_stock_low`, `lab_stock_expiry`, `lab_stock_received`, `lab_stock_count_reminder`), libellés FR + EN avec repli sûr pour tout statut inconnu.

## Frontend

Écrans en ligne seulement (pas de hors-ligne, comme le stock existant), FR + EN, **mobile d'abord** pour la réception et le comptage : cartes empilées au lieu de tableaux larges, grands champs numériques, boutons tactiles. Menu : une entrée « Stock labo » par rôle concerné avec les sous-écrans qu'il a le droit d'utiliser. Maquettes validées par l'utilisateur : entête de fiche → choix du produit → pointage ligne par ligne (qté commandée/reçue, lot, péremption, total) ; liste « à commander » avec colonnes produit, stock, seuil, origine, statut « commandé · livraison prévue ».

## Hors périmètre

- Consommation par examen ou par ouverture de flacon ; décrément automatique selon les analyses.
- Température/conditions de stockage, stabilité après ouverture, certificats.
- Passation automatique de commande ou envoi au fournisseur ; export PDF de bon de commande.
- Hors ligne (PowerSync).
- Toute liaison avec `pharmacy`, la caisse ou les mouvements de stock existants.
- Planificateur de tâches.

## Anti-objectifs

Échec même si « ça marche » : un écran de réception inutilisable sur téléphone ; devoir retaper les produits à chaque livraison ; un stock labo qui modifierait ou apparaîtrait dans la pharmacie ou la caisse ; un `StockController`/`ToxicoManager` qui obtient des droits au-delà de ceux listés.

## Contraintes

Tout accès concurrent à `quantity` : verrou `FOR UPDATE` en ordre croissant, jamais < 0 (409). Montants dans la devise de l'application (FCFA). Contrôle d'accès **côté serveur**, tests sur la matrice rôles × routes (au plus 4 connexions par test). Migration SQL brute idempotente + mise à jour de `ci/schema_only.sql`. Audit des écritures.

## Choix du concepteur (à contester)

- Seuil unique par produit (« atteint » = quantité ≤ seuil) ; pas de second niveau « critique ».
- Comptage = valeur absolue en rayon.
- Annulation de réception réservée à l'admin.
- Refus d'un doublon (fournisseur, n° de facture).
- Péremption à 60 jours, rappel de comptage à 7 jours.
- Admin a tous les droits ; autres rôles sans accès.
- Pas de planificateur : alertes calculées à la consultation et à l'envoi d'un comptage.
- **Livraison partielle** : toute réception validée contenant le produit clôt la demande ouverte (`recu`) ; si, après la réception, le stock est encore **≤ seuil**, une nouvelle demande `seuil` est créée aussitôt (le promoteur voit toujours ce qui manque). La « quantité commandée » d'une ligne est informative (écart affiché), elle ne pilote aucune règle.
- **Annulation d'une réception** : la demande clôturée par cette réception (on mémorise `closed_by_receipt_id`) repasse à `a_commander` ; si le stock retombe ≤ seuil sans demande ouverte, une demande `seuil` est créée.
- **Comptage et réception simultanés** : le comptage envoie la quantité « avant » qu'il a chargée pour chaque produit ; si le stock a changé entre-temps, la ligne est refusée (409 avec la liste des produits concernés), rien n'est écrit pour ces lignes, et la technicienne recompte ces produits.
- **Comptage qui remonte au-dessus du seuil** : une demande `seuil` ouverte et **non encore commandée** est clôturée automatiquement (`annule`, motif « stock remonté ») ; une demande `signalement` ou déjà `commande` n'est jamais clôturée par un comptage.
