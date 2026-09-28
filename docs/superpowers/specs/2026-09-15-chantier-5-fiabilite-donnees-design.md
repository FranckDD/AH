# Chantier 5 — Fiabiliser les données affichées

**Date** : 2026-09-15
**Origine** : registre `L1` de `SUIVI-AVANCEMENT.md` (audit transversal du 2026-09-15)
**Position** : premier des chantiers de remise à niveau, avant l'identité patient (chantier 6) et la complétion du portage (chantier 7)

## Objectif

Faire en sorte que tout chiffre, tout compteur et toute liste affichés par l'application correspondent à la réalité de la base — ou signalent explicitement leur échec. Aucune fonctionnalité nouvelle.

## Pourquoi ce chantier passe en premier

Les défauts de cette classe ne ressemblent pas à des pannes : l'écran répond, affiche un nombre, et se trompe. Trois conséquences qui justifient l'ordre :

1. **On ne peut pas vérifier nos propres corrections** sur les chantiers suivants tant que les écrans mentent. Un test manuel après le chantier 6 ou 7 serait ininterprétable.
2. **Le risque est financier et immédiat.** Deux exemples déjà mesurés sur la base réelle : une journée à 48 500 F affichée à 0, et 5 retraits affichés comme 0.
3. **Le coût est faible** : causes racines connues, fichiers identifiés, aucune migration de données.

Deux constats de cette classe ont déjà été corrigés le 2026-09-15 hors chantier, en raison de leur gravité (`L0`) : la perte silencieuse de saisie financière, et les 5 routes labo sans garde de rôle. Les trois bugs de bornes de dates (`L1a`, `L1b`, `L1c`) ont également été corrigés dans la foulée, leur cause racine étant commune.

## Périmètre

**Inclus** — le reste du registre `L1` : `L1d`, `L1e`, `L1f`, `L1g`, `L1h`, `L1i`.

**Exclus explicitement** :
- Tout le registre `L2` (identité patient) → chantier 6
- Tout le registre `L3` (portage des actions métier) → chantier 7
- Tout le registre `L4` (cohérence des permissions) → chantier 6, car relevant de la même décision d'accès
- **Le passage hors ligne** : ce chantier ne rend aucune fonction disponible hors ligne. Synchroniser des compteurs faux n'aurait aucun sens ; le hors-ligne est intégré en fin des chantiers 6 et 7, module par module.

## Méthode

**Caractérisation avant modification.** Chaque défaut est d'abord reproduit par un test automatisé qui échoue en décrivant le comportement erroné constaté, puis corrigé, puis re-vérifié. C'est indispensable ici parce que ces bugs sont invisibles à l'œil : sans test, on ne peut pas distinguer « corrigé » de « toujours faux, autrement ».

**Suivre les conventions déjà correctes du dépôt.** Dans presque tous les cas, une version correcte du même mécanisme existe déjà à côté du code fautif. On l'applique plutôt que d'inventer. C'est ce qui a été fait pour `L1a-c` (`func.date()` sur la colonne, repris de la liste des transactions) et ce que la spec retient ci-dessous pour `L1d` (`_list_by_flag`) et `L1g` (`secretariatHomeStore`).

**Pas de changement de contrat d'API gratuit.** Quand un type déclaré est malhonnête mais qu'un appelant existant en dépend, on corrige le sens sans casser l'appelant, et on note la dette.

---

## L1d — Seuls 10 patients sont atteignables dans l'onglet « Tous »

**Constat** : l'onglet affiche le vrai total dans son badge, mais « Page 1 sur 1 » et le bouton Suivant grisé. Au-delà du dixième patient, le dossier est inaccessible par cette voie.

**Cause racine** : `GET /patients/` déclare `response_model=List[PatientResponse]` et renvoie une liste nue (`patients_endpoints.py:66-74`). Le dépôt pagine pourtant bien côté serveur (`patient_repo.py:263`, `offset/limit`), mais ne renvoie jamais le total. Côté client, `patientStore.js:90-99` gère les deux formes : faute d'enveloppe, il retombe sur `total = rawList.length` et `total_pages = 1`.

**Approche retenue** : aligner sur la convention déjà en place dans ce même dépôt. Les trois onglets typés (`/patients/clinical`, `/toxicology`, `/spiritual/list`) passent par `_list_by_flag` (`patient_repo.py:277`), qui calcule le total **avant** pagination et renvoie l'enveloppe `{data, total, page, per_page, total_pages}`. On fait de même pour `list_patients`, et l'endpoint déclare `PatientListResponse` (schéma déjà défini, `patients_schemas.py:168`).

**Le client n'a pas besoin d'être modifié** : `patientStore` sait déjà lire l'enveloppe — c'est la branche qu'il utilise pour les trois autres onglets.

**Le filtrage par rôle est conservé en l'état, sans être activé — décision du 2026-09-15.**

`list_patients` (`patient_controller.py:317`) contient un filtrage par rôle **mort** : il lit `getattr(self.user, 'role_name', '')`, attribut inexistant sur le modèle `User` (registre `B6`), donc toujours vide, donc jamais appliqué.

Son intention correspond exactement au fonctionnement réel du centre, tel que décrit par le propriétaire : « un patient peut être suivi cliniquement, spirituellement ou toxicologiquement, ou passer par 2 ou les 3 ; c'est la secrétaire qui enregistre les patients spirituels, donc elle n'a pas besoin de voir ceux qui sont uniquement cliniques ; de même le médecin n'a pas besoin de voir ceux qui sont uniquement spirituels ». Le code va dans ce sens : pour la secrétaire il pose `WHERE is_spiritual = true` (`patient_repo.py:241-247`), ce qui **inclut** les patients suivis à la fois spirituellement et cliniquement, et n'exclut que ceux qui sont *exclusivement* cliniques. **Ce filtre ne doit donc pas être supprimé.**

Mais il ne peut pas être activé dans ce chantier : il s'appuie sur les drapeaux `is_clinical`/`is_spiritual`/`is_toxicology`, dont l'audit a établi qu'ils ne sont jamais dérivés des données réelles (registre `L2b` — créer une consultation spirituelle ne pose jamais `is_spiritual`). L'activer aujourd'hui ferait **disparaître de la liste de la secrétaire** des patients réellement suivis spirituellement mais dont le drapeau n'a jamais été posé : on passerait d'un écran trop permissif à un écran qui cache des patients, ce qui est pire.

**Décision** : ce chantier ne corrige que la pagination et laisse le filtre inerte. Son activation devient un livrable du **chantier 6**, une fois les drapeaux fiabilisés — et la règle devra alors se fonder sur l'existence réelle d'un dossier dans chaque domaine, pas sur un drapeau déclaratif.

Ce filtrage n'entre pas en contradiction avec la politique d'ouverture large décidée le 2026-09-15 : celle-ci porte sur ce qui est visible **à l'intérieur** d'un dossier ouvert ; il s'agit ici seulement de réduire le bruit dans une liste de travail.

## L1e — La pagination du module Finance mélange deux sources

**Constat** : tri par date faux d'une page à l'autre, dernières pages vides, filtre « Catégorie » qui ne ramène presque rien, compteur « N transactions trouvées » incohérent.

**Cause racine** : `financialStore.js:36-114` charge la page N des recettes (`/caisse/`) **et** la page N des dépenses (`/retrait/search`) indépendamment, fusionne les deux, puis ne trie que la page courante et calcule `total = countIn + countOut`. Le filtre catégorie est appliqué côté client **après** la pagination serveur, donc sur une quarantaine de lignes seulement (`FinancialList.vue:102`).

C'est le seul défaut de ce chantier qui ne se corrige pas par un simple alignement : deux sources paginées séparément ne peuvent pas être fusionnées en un classement correct côté client, quelle que soit l'astuce. Trois approches possibles.

**Option A — Journal unifié côté serveur (recommandée).** Un endpoint qui renvoie recettes et dépenses comme un seul flux de mouvements, trié, filtré et paginé en base (`UNION ALL` sur les deux tables avec un champ `sens` recette/dépense). Le client ne fait plus que l'afficher.
*Pour* : c'est la seule option qui rend le tri, la pagination, le total et le filtre catégorie tous corrects en même temps ; c'est aussi ce dont aura besoin l'état de caisse imprimable prévu au chantier 7.
*Contre* : nouvelle requête SQL à écrire et à tester ; les deux tables n'ont pas les mêmes colonnes, il faut définir la projection commune.

**Option B — Séparer l'affichage en deux listes.** Un onglet Recettes, un onglet Dépenses, chacun paginé par sa propre source.
*Pour* : correction immédiate, presque sans code backend.
*Contre* : change l'interface que l'utilisateur connaît, et supprime la vue chronologique mélangée — or c'est précisément ce qu'on regarde pour comprendre une journée de caisse.

**Option C — Tout charger puis paginer côté client.**
*Pour* : peu de code.
*Contre* : ne tient pas à la volumétrie d'un centre de santé sur plusieurs années, et déplace le problème au lieu de le résoudre. Écartée.

**Option retenue (décision du 2026-09-15) : A — journal unifié côté serveur**, en définissant la projection commune de façon à servir aussi l'état de caisse imprimable prévu au chantier 7. Le filtre catégorie et le tri passent côté serveur ; `financialStore` cesse de fusionner et de trier, et ne fait plus qu'afficher la page reçue.

## L1f + L1h (utilisateurs) — « Utilisateurs inscrits » toujours 0, pagination bloquée

**Constat** : le tableau de bord admin affiche toujours 0 utilisateur ; la liste des utilisateurs reste bloquée sur une page au-delà de 50 comptes ; avec une recherche, `page` et `per_page` sont ignorés côté serveur.

**Cause racine** : `GET /users/` renvoie une liste nue (`users_endpoint.py:71-85`) alors que `dashboardStore.js:68,90` lit `usersRes.data.total`. Et le chemin « avec recherche » du contrôleur ignore la pagination (`users_endpoint.py:79-84`).

**Approche retenue** : même correction que `L1d`, même convention — `GET /users/` renvoie l'enveloppe paginée, avec le total calculé avant pagination, et le chemin de recherche honore `page`/`per_page` comme le chemin sans recherche. Les deux consommateurs (`dashboardStore`, `userStore`) lisent alors le même contrat.

## L1g — Un seul appel en échec vide tout le tableau de bord

**Constat** : si une requête échoue, tous les indicateurs tombent à 0 et les activités récentes disparaissent, sans aucun message. L'écran devient indiscernable d'une journée sans activité.

**Cause racine** : `dashboardStore.js:56-134` charge tout via `Promise.all` — une seule rejection vide l'ensemble.

**Approche retenue** : `Promise.allSettled`, chaque bloc rendu indépendamment, et un indicateur visible pour les blocs en échec (« indisponible », pas « 0 »). Le modèle correct existe déjà dans le projet : `secretariatHomeStore` procède ainsi. La règle à retenir : **un chiffre absent ne doit jamais s'afficher comme un zéro.**

## L1h (reste) — Compteurs et recherches tronqués en silence

- **Compteur « Consultations » plafonné à 200** : `secretariatHomeStore.js:41,51` lit la longueur d'une liste dont `per_page` est borné à 200 (`cs_endpoint.py:99`). Correction : lire un total renvoyé par le serveur plutôt que la longueur d'une page.
- **Recherche en caisse trop étroite** : `caisse_repo.py:107-114` ne cherche que dans `transaction_type` et `created_by_name` — ni la description (`note`, pourtant affichée en colonne) ni le patient. Correction : étendre la recherche à ces deux champs.
- **Badges toxico jamais déclenchés** : « +X cette semaine » et l'alerte « évaluation en retard » dépendent de dates absentes du schéma de liste (`toxico_schema.py:36-45`) ; elles n'existent que sur le détail. Correction : exposer la date d'admission dans le schéma de liste.

## L1i — Erreurs avalées rendant un bug indiscernable d'un cas vide

- `configStore.fetchStructureInfo` (`configStore.js:41-51`) avale toute erreur en `console.warn` et conserve le nom par défaut « AH2 DASHBOARD » : « établissement non configuré » et « endpoint cassé » deviennent identiques à l'écran. Correction : distinguer les deux états et rendre l'échec visible.
- `labStore.fetchHistory` (`labStore.js:159-181`) appelle `LabGateway.getAllResults()`, **qui n'existe pas** : le `TypeError` est avalé par le `catch` et produit une liste vide. Aucune vue n'appelle cette fonction aujourd'hui — c'est du code mort, mais c'est un piège armé pour la première vue qui l'utilisera. Correction : supprimer la fonction morte (après vérification qu'aucun appelant n'existe), plutôt que d'implémenter une méthode dont personne n'a défini le besoin.

---

## Décisions prises (2026-09-15) — plus aucune question ouverte

1. **Filtrage par rôle de la liste patients (`B6`)** — conservé, non activé, reporté au chantier 6 où il sera fondé sur l'existence réelle des dossiers. Motivation détaillée dans la section `L1d`.
2. **Approche `L1e`** — option A, journal unifié côté serveur.
3. **`labStore.fetchHistory`** — supprimée. Vérifié le 2026-09-15 : `getAllResults` est appelée à `labStore.js:168` mais n'est **définie nulle part** dans `src/`, et `fetchHistory` n'est appelée par aucune vue. Code mort intégral, dont le seul effet possible serait une `TypeError` avalée par un `catch`.

## Définition du « terminé »

- Chaque défaut du périmètre est couvert par un test qui échouait avant la correction et passe après.
- Les compteurs et totaux affichés sont vérifiés contre une requête SQL directe sur la base réelle, comme cela a été fait pour `L1a-c` (48 500 F attendus, 48 500 F affichés).
- Aucun écran n'affiche `0` là où la donnée est indisponible : l'indisponibilité est visible en tant que telle.
- La suite de tests existante ne régresse pas (les 9 échecs pré-existants documentés restent les seuls).
- `SUIVI-AVANCEMENT.md` mis à jour : entrées `L1d` à `L1i` marquées résolues, avec la preuve chiffrée.
