# Cloture de caisse : compter l'argent reel, chaque jour

Date : 2026-10-23 · Statut : cadre en brainstorming avec l'utilisateur, en attente de relecture et d'approbation.
Premier des quatre morceaux decides pour les Rapports (ordre : 1 cloture de caisse, 3 sorties declarees de la production, 2 comptage physique du stock, 4 Rapports et controle quotidien). Les trois autres ont leur propre document.

## Intention et pourquoi

Le promoteur n'a plus confiance : un audit comptable a revele des manques d'argent et de produits. La faille des reductions est deja fermee (permission obligatoire). Mais aujourd'hui le systeme ne connait que ce qui a ete **enregistre** : le filtre par date de la caisse montre des totaux, pas l'argent **reellement compte**. Rien ne permet de savoir si le tiroir contient ce qu'il devrait contenir.

Ce document ajoute la **cloture de caisse** : chaque jour, l'argent est compte, compare a ce que le systeme attend, et l'ecart est conserve et signale. C'est aussi la source que les Rapports liront plus tard (ecarts par jour, par secretaire, dans le temps).

Succes : pour n'importe quel jour, le promoteur sait combien etait dans la caisse a l'ouverture, combien est rentre, combien a ete retire, combien devrait rester, combien a ete compte, et l'ecart ; et une journee jamais cloturee ne passe pas inapercue.

## Ce qui est decide (par l'utilisateur)

1. **Une seule caisse, un seul tiroir** partage par les secretaires. La cloture se fait **par caisse et par jour**, pas par secretaire. (Deux secretaires travaillent ensemble cinq jours sur six ; une seconde alternera plus tard par semaines, sans regle sur le nombre de semaines. Chacune encaisse avec son propre compte.)
2. **Comptage a l'aveugle, puis affichage.** La secretaire saisit d'abord ce qu'elle a compte **par mode de paiement**, sans voir le total attendu. Elle valide. Ensuite seulement, le systeme affiche, pour chaque mode, le total recu, le compte et l'ecart. Le comptage ne peut plus etre modifie apres cet affichage. Un ecart non nul exige un commentaire. (Pendant la saisie, elle peut consulter la liste de ses propres ventes, comme aujourd'hui.)
3. **Calcul par mode** : attendu = solde d'ouverture + entrees - retraits. Le solde d'ouverture est le compte de la cloture precedente. Les retraits de caisse actifs comptent ; les retraits annules ne comptent pas. Ainsi on sait exactement combien il y a dans la caisse, combien est rentre et combien a ete retire au total.
4. **Cloture automatique a 23 h** : toute journee non cloturee a 23 h est cloturee par le systeme (oubli, pas de connexion). Elle est marquee « non declaree » (attendu seulement, pas de compte), verrouillee, et signalee comme anomalie au promoteur et a l'admin. Le centre est ouvert tous les jours : il y a donc une cloture **chaque jour**, meme sans aucun mouvement, avec sa notification.
4b. **Modes mobiles** : seul l'argent liquide est compte physiquement. Pour Orange Money, MTN Money et Autre mobile, la secretaire saisit, toujours a l'aveugle et avant l'affichage, le total que **l'operateur** lui indique pour la journee (releve). Ce releve est compare au flux attendu du jour de ce mode (entrees - retraits), sans solde d'ouverture reporte. Le solde d'ouverture ne concerne que les especes. (Lecture de l'utilisateur a verifier : « elle va relever de l'operateur ».)
5. **Notifications** : a chaque cloture, le promoteur et l'admin recoivent une notification avec le total attendu, le total compte et l'ecart (la notification dit si la cloture est automatique). Le controle quotidien des Rapports, lui, ne previent qu'en cas d'anomalie. La notification de cloture sert de preuve que la journee a tourne.
6. **Mode de paiement obligatoire sur les nouveaux retraits** (15 retraits sur 17 existants n'ont pas de mode). C'est la seule modification d'un ecran existant (le formulaire de retrait et son endpoint) ; elle est annoncee comme telle. Les anciens retraits sans mode sont comptes en **Especes**.
7. **Liste officielle des modes** : Especes (« Cash » est regroupe dans Especes), Orange Money, MTN Money, Autre mobile (pour « Mobile Money » ou un nouvel operateur). Modifiable par l'admin. Les textes libres existants sont normalises vers cette liste.
8. **Une cloture validee n'est jamais modifiee.** Une correction passe par une demande approuvee par le promoteur (ou l'admin), comme pour les reductions, et laisse une trace.
9. **Ecrans existants modifies, limites a deux points (valides par l'utilisateur)** : (a) le formulaire de retrait exige le mode ; (b) les formulaires de facture et de paiement echelonne offrent la **liste officielle des modes** a la place de leurs choix actuels (Especes, Mobile Money, Virement, Cheque). Aucun autre ecran existant ne change. La cloture est un nouvel ecran du menu de la secretaire ; la lecture des clotures par le promoteur et l'admin est un ecran nouveau a cote.
10. **Vente annulee = sortie d'argent** : l'annulation d'une vente enregistre une sortie du montant paye, a la date de l'annulation, avec le motif « vente annulee » et la justification deja obligatoire. Si le client reprend le produit, une nouvelle facture enregistre une nouvelle entree : les deux se compensent et l'attendu reste exact, que l'argent soit rendu ou reste dans le tiroir. La cloture affiche chaque annulation de la journee (auteur, montant, justification) ; le projet Rapports en fera un indicateur surveille par secretaire, car une annulation peut masquer un vol.
11. **Consultations spirituelles** : l'argent qu'elles encaissent hors caisse entre dans le meme tiroir et compte dans les entrees (le constructeur trouve la table et le champ exacts).

## Ce que j'ai choisi, a verifier

- **Qui peut cloturer** : n'importe quel compte secretaire. La cloture est celle de la caisse, avec le nom de la personne qui l'a faite.
- **Periodes chainees** : une cloture couvre tout ce qui s'est passe depuis la cloture precedente jusqu'au moment de sa validation, sans trou ni chevauchement. Ce qui est encaisse apres 23 h appartient a la periode suivante.
- **Premiere cloture** : le solde d'ouverture est saisi une seule fois (par l'admin), faute de cloture precedente.
- **Apres une cloture automatique** : le solde d'ouverture du lendemain reprend l'attendu (pas de compte), avec un marqueur visible dans les Rapports.
- **Periodes et heures** : l'heure de chaque operation est celle de **reception sur le serveur**, via une nouvelle colonne remplie par la base sur les paiements echelonnes et les retraits (les heures actuelles melangent trois fuseaux, par exemple les retraits sont en retard d'une heure sur les ventes). Une operation hors ligne synchronisee apres une cloture tombe donc d'elle-meme dans la periode suivante et ne change jamais une cloture figee. Il n'y a pas de marqueur « tardif ».
- **Cloture manuelle bloquee tant que des operations du poste ne sont pas synchronisees** : sinon une vente faite hors ligne avant le comptage serait dans le tiroir mais pas dans l'attendu, puis comptee une seconde fois le lendemain.
- **Cloture en ligne seulement** : elle a besoin du calcul du serveur. Hors ligne, la secretaire ne peut pas cloturer ; la cloture automatique de 23 h prend le relais.
- **Entrees** : les **paiements echelonnes** (avances, versements, soldes) groupes par mode, sur la periode, moins les ventes annulees ou en attente d'approbation. Une avance est ecrite deux fois dans le code (paiement et montant avance de la vente) : ne jamais additionner les deux, et ne pas reutiliser les KPI existants de la caisse (ils placent les versements ulterieurs sur la mauvaise journee et le mauvais mode). Les chemins qui changent le montant paye sans ecrire de paiement (la route de reglement et la modification d'une vente) doivent etre verifies ; s'ils sont atteignables depuis l'ecran actuel, ils sont corriges pour ecrire un paiement et l'annoncer.
- **Planification** : il n'existe aucun planificateur. La cloture automatique de 23 h est rattrapee a la premiere lecture ou connexion qui suit, et un script lance par cron sur le serveur la declenche aussi. Chaque journee garde sa limite de 23 h, meme fermee plus tard.
- **Anciennes operations en attente avec un mode ancien** (Mobile Money, Virement, Cheque) : le serveur les rapproche de la liste officielle au lieu de les rejeter, pour ne pas bloquer la file de synchronisation.

- **Modes inconnus** : un mode qui ne rentre pas dans la liste officielle va dans un compartiment « non classe » visible et signale, jamais compte en especes. Pour les nouveaux encaissements, le mode vient de la liste.
- **Solde d'ouverture des especes** : toujours le montant compte de la cloture precedente ; apres une cloture automatique, l'attendu, avec un marqueur.
- **Comptage en cours** : pas conserve cote serveur ; un rechargement avant la validation recommence sans rien reveler. Une fois validee, la cloture est definitive. Si le travail de 23 h tombe pendant un comptage non valide, la cloture automatique l'emporte.
- **Double cloture** : impossible (une seule cloture par periode, avec verrou).
- **Serveur en panne a 23 h** : une reprise ferme chaque jour manque, un par un, a son heure de 23 h. L'heure est celle du centre, fuseau fixe.
- **Corrections** : un enregistrement de regularisation s'ajoute, la cloture d'origine n'est jamais modifiee ; le solde d'ouverture du lendemain reste fige ; la regularisation se compense dans la periode suivante. Une cloture automatique peut etre completee par cette voie.
- **Notifications** : une seule par destinataire et par cloture (promoteur et chaque admin) ; l'anomalie est un marqueur sur cette notification, pas une seconde.
- **Modes de paiement** : l'admin desactive un mode, il ne le supprime jamais (les clotures stockent des montants par mode).
- **Operations tardives** : reperees par l'heure de reception sur le serveur ; si cette heure n'existe pas deja sur les tables concernees, le plan ajoute une colonne.

## Hors perimetre

- Les Rapports eux-memes (vues comparatives, tendances, comparaison des secretaires, controle quotidien et son anomalie « journee non declaree ») : projet 4.
- Les sorties declarees de la production (projet 3) et le comptage physique du stock (projet 2).
- Tout changement de la caisse, des reductions ou des factures existantes, hors l'obligation du mode sur les retraits.
- Les devises autres que celle de l'application ; les depots en banque.

## Ce qui ferait echouer le projet meme s'il « marche »

- La secretaire voit le total attendu avant d'avoir valide son comptage, ou peut modifier son comptage apres l'avoir vu.
- Une journee reste sans cloture (ni manuelle, ni automatique).
- Un encaissement ou un retrait est compte deux fois, ou pas du tout, dans l'attendu d'un mode.
- Une cloture figee peut etre modifiee, ou une operation tardive change un chiffre deja fige.
- Un retrait sans mode est possible apres la mise en service.

## Laisse au constructeur

Les noms de tables et de routes, la migration, la facon de normaliser les textes libres existants, l'implementation de la tache de 23 h (planificateur deja present ou autre), le format exact des notifications (le systeme de notifications existant), l'organisation des ecrans, le traitement des paiements echelonnes, les tests.
