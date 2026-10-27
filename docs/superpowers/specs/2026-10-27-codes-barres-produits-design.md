# Codes-barres produits, zone photo et fenetre agrandissable a la caisse (conception)

Date : 2026-10-27. Statut : decrite et validee en discussion par l'utilisateur ; relecture par un constructeur independant a faire ; en attente d'approbation.

## Pourquoi

Le promoteur veut faciliter l'identification d'un produit a la caisse. Aujourd'hui, dans « New invoice », la secretaire tape le nom du produit ; la liste de resultats n'affiche que le nom et le stock (`CaisseInvoiceModal.vue`, appel `CaisseGateway.searchProducts`, `GET /pharmacy/`). La table `pharmacy` n'a ni code-barres, ni photo. Des produits de meme nom avec un dosage ou une forme differents se distinguent mal.

Le centre va acheter un lecteur de codes-barres (type « clavier » : il saisit le code puis Entree). Le centre colle ses propres etiquettes sur tous ses produits.

## Regle d'or (decidee par l'utilisateur)

On ne change rien de ce qui existe : on **ajoute une option**. La recherche par nom, le prix verrouille, la saisie de la quantite, les avertissements de stock et tous les autres ecrans restent tels quels.

## Ce qui est decide (par l'utilisateur)

- **Code-barres** : chaque produit recoit un code unique genere automatiquement, y compris les produits deja existants. Le centre colle ses propres etiquettes.
- **Scan dans New invoice** : scanner un flacon remplit automatiquement une ligne Pharmacie avec ce produit (prix verrouille comme aujourd'hui). La secretaire regle ensuite la quantite comme d'habitude. Un second scan du meme produit **augmente la quantite de la ligne existante** (2, puis 3...) au lieu de creer une nouvelle ligne ; elle peut corriger a la main.
- **Zone photo dediee** dans la fenetre New invoice (pas une photo dans la ligne). Elle montre le produit concerne : nom, forme, dosage, prix, et la photo. Elle reagit au scan, au choix d'un produit par la recherche par nom, et au clic sur une ligne deja ajoutee. La photo est **facultative** (rien n'est exige a la creation d'un produit) ; sans photo, une image neutre est affichee avec les memes informations.
- **Fenetre agrandissable** : un bouton « agrandir / restaurer » sur la fenetre New invoice (taille actuelle <-> plein ecran). Version simple uniquement : pas de redimensionnement libre par glisser.
- **Impression des etiquettes** depuis la fiche des produits : choix des produits et du nombre d'etiquettes par produit (voir « Imprimante d'etiquettes » plus bas).
- **Imprimante d'etiquettes (info du promoteur 2026-10-27)** : le centre va acheter une imprimante d'etiquettes ; modele et taille de rouleau **pas encore connus**. Donc : impression etiquette par etiquette (une petite page par etiquette : code-barres, chiffres lisibles dessous, nom du produit), via la boite d'impression du navigateur (tout pilote Windows convient) ; **la taille de l'etiquette est un reglage** modifiable par l'admin, avec une valeur par defaut de 50 x 30 mm (appel de l'assistant). La planche A4 avec traits de coupe reste en solution de secours tant que l'imprimante n'est pas achetee (appel de l'assistant, l'utilisateur peut la retirer).
- **Qui gere** : les photos et les etiquettes se gerent dans l'ecran actuel de gestion des produits (`ProductModal.vue`), par les roles qui peuvent deja creer et modifier un produit. La secretaire ne fait que scanner.

## Ce qui est suppose (appels de l'assistant, a faire relire)

- Le code est propre au centre, court et lisible sous le dessin du code-barres, et **ne change jamais** pour un produit donne. Il est stocke sur la ligne de `pharmacy` (nouvelle colonne unique), genere a la creation du produit ; une migration Alembic remplit les produits existants.
- Un code inconnu affiche un message clair en francais et en anglais et n'ajoute rien a la facture.
- Un produit en rupture reste selectionnable ; l'avertissement de stock actuel s'affiche comme aujourd'hui.
- Hors ligne : le scan doit marcher comme la recherche par nom (meme secours sur la table locale synchronisee, secretaire uniquement, affichage informatif du stock). La photo est reduite (environ 50 Ko) et gardee en cache ; sans reseau et sans cache, c'est l'image neutre.
- Le lecteur « clavier » est reconnu a sa vitesse de frappe et a son Entree finale ; un champ de scan est toujours pret a recevoir le code quand la fenetre New invoice est ouverte (la secretaire n'a rien a cliquer).
- La photo est stockee comme le fichier de consentement toxicologie : dossier du serveur, nom UUID, lecture authentifiee (pas de fichier public).
- Le type de code-barres et son rendu (Code 128 recommande) sont laisses au constructeur.
- **Code en chiffres uniquement** (appel de l'assistant) : un lecteur « clavier » sur clavier AZERTY peut deformer lettres et prefixes. Le code est genere cote serveur (sequence ou valeur unique), jamais cote client, et n'est jamais reutilise, meme si un produit est supprime ou desactive (contrainte d'unicite permanente).
- **Creation de produit uniquement en ligne** (appel de l'assistant, a verifier dans le code) : les produits sont crees par le serveur ; la secretaire n'en cree pas. Le code arrive donc dans la table locale `pharmacy` par la synchro ; un produit tout juste cree est scannable hors ligne apres sa premiere synchro. Un scan hors ligne d'un code pas encore synchronise donne le message « code inconnu ».
- **Photo, cache** (appel de l'assistant) : lecture par une URL qui change quand la photo est remplacee (identifiant ou version dans l'URL) et cache du navigateur. Pas de systeme de pieces jointes PowerSync.
- **Scan repete** (appel de l'assistant) : un scan ajoute toujours 1 a la premiere ligne Pharmacie de ce produit, meme si la quantite a ete tapee a la main. L'avertissement de stock et le circuit de reduction restent ceux de la saisie manuelle : le scan ne fait que remplir la ligne et sa quantite, il ne contourne aucune regle.
- **Roles de gestion** : on reutilise les gardes de route existantes des produits, sans nouveau role ni nouvelle regle.

## Buts

- Scanner un flacon remplit la bonne ligne en une seconde, sans taper.
- La secretaire voit une photo et les details du produit pour confirmer son choix.
- Aucune regression : sans lecteur, sans photo, sans agrandir, l'ecran se comporte comme avant.

## Non-buts et anti-buts

- Pas de code par lot ni par date de peremption : un code par produit.
- Pas de lecture de codes-barres de fabricants.
- Pas de camera ou de lecteur integre au navigateur : seulement le lecteur « clavier ».
- Pas de redimensionnement libre de la fenetre.
- Pas de photo exigee, pas de gestion de photos par la secretaire.
- Ne pas toucher aux autres roles, aux autres lignes (Consultation, Examen, Service) ni a la logique de prix, de reduction ou de stock.

## Contraintes du projet

- Roles verifies cote serveur ; table des routes comparee dans les tests de roles.
- UI : jetons seulement, textes >= 13 px, cibles >= 44 px, FR/EN a cles identiques, ponctuation ASCII (pas de tiret long, de fleche ou de point median), dates jj/mm/aaaa, `authStore.hasRole()`.
- Migration Alembic (tete actuelle `032_psy_scope_transfers`), appliquee a la base de developpement, miroir dans `ci/schema_only.sql`.
- PowerSync : toute nouvelle colonne de `pharmacy` lue hors ligne doit etre enfilee dans les couches du schema local et des flux de synchronisation (voir les notes du chantier 4) ; verifier les regles de synchro de `pharmacy` pour la secretaire.
- Impression : la planche A4 suit le motif d'export PDF existant (WeasyPrint, en-tete dynamique).
- Les guides utilisateur concernes (secretaire, stock/produits) sont a mettre a jour apres livraison.

## A la charge du constructeur

Nom et forme de la colonne du code, algorithme de generation, symbologie, endpoints (recherche par code, envoi et lecture de la photo, planche d'etiquettes), format et dimensions de la planche (nombre d'etiquettes par page), traitement de l'image (redimensionnement), emplacement du bouton d'agrandissement, detection du lecteur, libelles FR/EN, tests, mise a jour des guides.
