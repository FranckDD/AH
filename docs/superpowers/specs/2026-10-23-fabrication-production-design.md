# Fabrication : de l'achat des intrants à l'expédition au centre

Date : 2026-10-23 · Statut : cadré en brainstorming avec l'utilisateur, en attente de relecture et d'approbation.
Projet précédent à lire : `2026-10-20-fabrication-reception-avaries-design.md` (réception, lots, avaries, contrôle du stock). Ce document le **prolonge en amont** et ne le remplace pas.

## Intention et pourquoi

Le centre fabrique un produit que l'utilisateur appelle « MIEL » (ce n'est pas du miel : des liquides mis en bouteilles). Aujourd'hui rien n'enregistre ce qui est acheté pour le fabriquer, ce qui est consommé, ce qui est perdu en route de production, ni ce que cela coûte. Le stock ne connaît le produit qu'à sa **réception** au centre. Le promoteur n'a que des registres et la parole des responsables, et un audit comptable a déjà révélé des manques financiers et de produits ; la faille des réductions est fermée, il reste à **le rassurer** par un suivi réel du parcours des produits.

Le responsable de production (qui n'existe pas encore comme rôle) doit pouvoir enregistrer les achats d'intrants et chaque lot de fabrication, et le promoteur **suit** sans rien saisir. Le procédé exact de fabrication n'est pas connu de l'utilisateur ; la conception s'inspire donc des pratiques usuelles de traçabilité et de bilan de production (ISO 22000 / 22005, bilan de rendement), sans viser de certification.

Succès : un lot de MIEL qui arrive au centre peut être remonté jusqu'aux achats d'intrants qui l'ont produit ; un manque non expliqué (bouteilles qui ne se retrouvent ni bonnes, ni cassées, ni rejetées) ne passe plus inaperçu ; le coût de revient par bouteille est connu.

## Ce qui est décidé

1. **Deux projets indépendants** : cette Fabrication d'abord, les **Rapports** ensuite (le promoteur et l'admin comparent ce qui entre et ce qui sort, par produit). Les Rapports s'appuient sur les données de la Fabrication (coûts, pertes) : c'est pourquoi la Fabrication passe en premier.
2. **Nouveau rôle « responsable de production »** : il saisit tout (intrants, lots, consommations, résultats). Le **promoteur** et l'**admin** voient tout, en lecture seule. Aucun autre rôle n'a accès.
3. **Parcours** : achat d'intrants → lot en production (consommations saisies) → bilan du lot → expédition au centre, puis le circuit existant (lot « produit » → « livré » par l'Assistant à l'arrivée → réception → contrôle par le contrôleur de stock) **sans aucun changement**.
4. **Volume** : environ 2 lots par semaine, au moins 100 bouteilles chacun. Des formulaires simples suffisent, pas de saisie en série.
5. **Coûts** : visibles du **responsable de production, du promoteur et de l'admin seulement**. Les montants de coût sont retirés des réponses du serveur pour tous les autres rôles.
6. **Aucun nom de produit ou d'intrant dans le code** : tout vient de ce qui est enregistré (la base sera nettoyée en fin de projet et les vrais noms seront créés en production).
7. **Aucun écran existant n'est modifié.** La Fabrication s'ajoute à côté. Seules exceptions inévitables : ajouter une entrée de menu pour les rôles concernés et déclarer le nouveau rôle.
8. **Lot hors tolérance** (décidé par l'utilisateur) : il **peut être expédié**, mais le responsable de production doit **écrire une justification** ; la justification est conservée avec le bilan et le lot entre comme anomalie dans le contrôle quotidien. L'expédition n'est pas bloquée.
9. **Les anomalies ne déclenchent pas d'alerte immédiate** : elles sont regroupées par un **contrôle quotidien** qui appartient au projet Rapports. La Fabrication se contente de rendre ses anomalies **interrogeables** (voir plus bas).

## Les écrans (maquette validée le 2026-10-23)

- **Intrants** : liste des achats d'intrants (fournisseur, quantité, unité, coût unitaire, date) et stock restant par intrant, avec seuil d'alerte.
- **Lots de fabrication** : liste avec statut, et fiche d'un lot : produit fini, date, responsable ; tableau de ce qui est consommé avec **la provenance (l'achat d'où ça vient)** et le coût ; résultat (bonnes, cassées, rejetées, liquide perdu) ; **bilan** (attendu, retrouvé, manque non expliqué en nombre et en %, tolérance, badge hors tolérance) ; **coût de revient** (total des intrants et par bouteille bonne). Boutons : enregistrer en brouillon, **valider le bilan et expédier au centre**.
- **Suivi du promoteur** : les mêmes écrans en lecture seule, plus un résumé des lots récents et des anomalies de fabrication.

Dans le style des refontes récentes (bibliothèque `ui/`, jetons de couleur, FR et EN, contrastes AA, accessibilité), en tableau responsive sur téléphone.

## Règles métier

- **Intrant** : catalogue d'intrants propre à la Fabrication (distinct des produits vendus, jamais vendable en caisse), avec unité et un indicateur « contenant » (la bouteille) qui définit le nombre de pièces attendues. Un achat d'intrant augmente son stock ; une consommation le diminue.
- **Consommation** : saisie par lot, **rattachée à un achat précis** (provenance). On ne peut pas consommer plus que le restant de l'achat.
- **Bilan** : `attendu` = nombre de contenants mis en production ; `retrouvé` = bonnes + cassées + rejetées ; `manque non expliqué` = attendu − retrouvé, aussi en % de l'attendu. Hors tolérance si ce % dépasse la **tolérance** (2 % au départ, modifiable par l'admin). Un lot hors tolérance exige une **justification** avant l'expédition (voir la décision 8). Le liquide perdu est enregistré à titre d'information (le bilan en litres n'est pas dans ce projet).
- **Coût** : coût du lot = somme des (quantité consommée × coût unitaire de l'achat d'origine) ; coût par bouteille bonne = coût du lot / bouteilles bonnes.
- **Statuts d'un lot** : `brouillon` → `en_production` → `termine` (bilan à valider) → `expedie` ; `annule` possible tant qu'il n'est pas `expedie`, avec un motif. Un lot `expedie` n'est plus modifiable.
- **Expédition** : valider le bilan crée, dans le circuit existant, **un lot de production à l'état « produit »** (quantité = bouteilles bonnes, produit fini, date de péremption éventuelle) et le relie au lot de Fabrication. Tout ce qui suit est le flux actuel, inchangé.
- **Traçabilité** : de n'importe quel lot du circuit existant on remonte à son lot de Fabrication, puis aux achats d'intrants consommés ; et dans l'autre sens.

## Pour les Rapports (ce que la Fabrication doit rendre disponible)

Sans construire le contrôle quotidien : fournir des **requêtes d'anomalies de fabrication** interrogeables par le futur contrôle : lots hors tolérance, intrants sous leur seuil, lots restés trop longtemps « en production ou terminés non expédiés », écart entre quantité expédiée et quantité reçue (via la réception existante). Et exposer le **coût de revient par produit fini**, qui manquait pour calculer les marges.

## Hors périmètre

- Le contrôle quotidien, les alertes aux promoteur et admin, les écrans de Rapports (projet suivant).
- Le fonctionnement hors ligne (la saisie se fait en ligne).
- Une recette type imposée (la saisie porte sur ce qui est réellement consommé ; une recette pourra s'ajouter plus tard).
- Le bilan en litres du liquide, les inventaires d'intrants avec comptage contrôlé, les achats avec bons de commande.
- Toute modification des écrans existants (stock admin, caisse, réception, contrôle), de leurs droits ou de leurs règles.
- La certification ISO.

## Ce qui ferait échouer le projet même s'il « marche »

- Un nom de produit ou d'intrant écrit dans le code.
- Des montants de coût visibles d'un rôle non autorisé.
- Un lot expédié dont on ne retrouve pas les achats d'intrants.
- Une modification, même discrète, du comportement du circuit existant de réception et de contrôle.

## Laissé au constructeur

Le nom exact du rôle (proposition : `ProductionManager`, dans le style de `StockController`), les noms des tables et colonnes, la migration, la génération des numéros (`FAB-AAAA-NNNN` proposé), l'organisation des écrans à l'intérieur de la mise en page, l'ordre de construction, la façon de retirer les coûts des réponses du serveur, les tests.

## Choix faits par l'assistant, non confirmés par l'utilisateur

- Tolérance par défaut 2 % et modifiable par l'admin.
- Un lot de Fabrication correspond à une expédition.
- Le stock d'intrants est suivi, avec seuil d'alerte réglé par l'admin.
- Le lot de production du circuit existant naît à l'**expédition** (état « produit »), et non à la fin de la production : le « livré » reste le geste de l'Assistant à l'arrivée.
- Le coût de revient, écarté dans la conception du 2026-10-20, est **réintroduit** sur demande de l'utilisateur du 2026-10-23.
- Les lots saisis directement dans l'écran actuel des lots (sans passer par la Fabrication) restent possibles et n'ont simplement pas de bilan ni de coût.

## Précisions après relecture (choix de l'assistant, à vérifier par l'utilisateur)

Un relecteur indépendant a posé des questions ; celles-ci sont tranchées ainsi, sans changer ce qui est construit.

- **Contenant et « attendu »** : un lot a **exactement une** consommation marquée contenant ; l'attendu est la quantité consommée de ce contenant. Un lot sans consommation de contenant ne peut pas passer en production.
- **Types de nombres** : quantités d'intrants en décimal (3 décimales, pour les litres), bouteilles en entier, coûts en décimal à 2 décimales, dans la monnaie de l'application (la même que la caisse).
- **Stock d'intrants** : la consommation est réservée au passage du lot en `en_production` (le stock de l'achat diminue à ce moment, sous verrou pour éviter deux lots sur le même achat). L'annulation d'un lot **rend** les quantités à leurs achats d'origine.
- **Transitions** : `brouillon` (tout est modifiable) → `en_production` (le responsable de production déclenche ; consommations figées) → `termine` (le responsable déclenche ; exige les résultats saisis) → `expedie` (valide le bilan). Retour `termine` → `en_production` possible avant l'expédition, pour corriger. Le responsable de production déclenche chaque transition.
- **Achats d'intrants** : modifiables tant qu'aucune consommation ne s'y rattache ; annulables avec motif tant qu'ils ne sont pas consommés ; après la première consommation, verrouillés (une erreur se corrige par une correction motivée et tracée dans le journal d'audit).
- **Paramètres** : la **tolérance** est globale ; le **seuil d'alerte** est **par intrant** ; le **délai « trop longtemps »** vaut 7 jours par défaut, réglé par l'admin. La tolérance appliquée est **figée dans le lot** au moment de la validation, pour que l'historique ne bouge pas si on la change.
- **Produit fini** : un produit de la table des produits existante (comme les lots actuels). À l'expédition : date de livraison prévue et péremption éventuelle saisies, responsable repris du compte qui expédie.
- **Visibilité** : seuls le responsable de production, le promoteur et l'admin voient les écrans de Fabrication. L'Assistant et le contrôleur de stock ne voient **rien** de nouveau (les écrans existants ne changent pas) ; la traçabilité vers les intrants n'est donc consultable que par ces trois rôles.
