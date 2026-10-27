# Notes du conseiller spirituel (conception)

Date : 2026-10-28. Statut : decrite et validee en discussion par l'utilisateur ; relecture par un constructeur independant a faire ; en attente d'approbation.

## Pourquoi

Le conseiller spirituel du centre n'a aujourd'hui que deux ecrans de lecture de la toxicologie (`SpiritualCounsellor`, voir le guide spiritual-1). Ses rencontres et ses notes sont sur papier. Le centre veut qu'il puisse les saisir dans l'application, sans alourdir son travail.

## Comment il travaille (rapporte par l'utilisateur apres discussion avec lui)

Il parle a un patient **quand il se sent inspire de le faire** : pas de planning, pas de rendez-vous. Une rencontre suit en general ces etapes, sans qu'elles soient toutes presentes : conseil general, priere, lecture d'un verset de la Bible, discussion sur ce verset, texte remis au patient a lire, questions et reponses en fin de seance. Parfois les personnes ne veulent pas parler ; c'est normal et doit pouvoir s'enregistrer sans que cela ressemble a un echec.

## Ce qui est decide (par l'utilisateur)

- **Une seule liste de notes du conseiller, sans lien avec un patient.** Aucune table existante n'est touchee (dossiers, patients, toxicologie, caisse). Une note par patient pourra venir plus tard comme un chantier a part.
- **Facultatif** : le conseiller n'est jamais oblige d'ecrire une note. Aucun rappel, aucun compteur, aucun indicateur « sans note ».
- **Qui lit** : le conseiller (qui ecrit, relit et corrige ses notes), le **promoteur** et l'**admin** en lecture seule. Personne d'autre (ni le psychologue, ni le medecin, ni le responsable de toxicologie).
- **Contenu d'une note** : date automatique ; cases facultatives de ce qui s'est passe (conseil general, priere, verset lu avec sa reference, discussion, texte remis, questions et reponses) ; une mention facultative « les personnes suivies n'ont pas voulu parler » ; un champ libre.
- Ecran simple et rapide ; la derniere note est la premiere affichee ; aucune suite n'est imposee et aucun « a faire » n'est montre.

## Ce qui est suppose (appels de l'assistant, a faire relire)

- Nouvelle table `spiritual_notes` : identifiant, auteur (`users.user_id`), date de la rencontre (date locale de Douala, modifiable par le conseiller pour une note saisie plus tard), cases booleennes (conseil, priere, verset lu, discussion, texte remis, questions et reponses), reference du verset (texte court, facultatif), mention « n'a pas voulu parler » (booleen), texte libre (facultatif), dates de creation et de modification. Une note peut etre vide sauf la date (rencontre sans rien d'autre a dire).
- Role d'ecriture : `SpiritualCounsellor` seulement, sur **ses propres** notes (modifier et supprimer sont reserves a l'auteur). Lecture : `SpiritualCounsellor` (ses notes), `promoteur` et `admin` (toutes les notes, avec le nom de l'auteur). Les ecritures de l'admin et du promoteur sont refusees cote serveur.
- **Plusieurs comptes conseiller (appel de l'assistant, ecarte la lecture « ses seules notes »)** : tout compte `SpiritualCounsellor` lit **toutes** les notes du role (un successeur retrouve l'historique) ; seul l'**auteur** modifie ou supprime sa note. Promoteur et admin lisent tout, avec le nom de l'auteur.
- **Suppression** : definitive (suppression en dur) par l'auteur seulement ; l'entree d'audit garde l'identifiant de la note, sa date et son auteur, **pas son texte** (confidentialite).
- **Pas de journal des lectures** par le promoteur ou l'admin (non demande).
- **Liste** : la meme liste pour les trois roles (colonne auteur), triee par date de rencontre decroissante puis par creation, sans filtre ni recherche ; le promoteur et l'admin n'ont aucun bouton d'ecriture.
- **Date de rencontre** : par defaut aujourd'hui (Douala), modifiable, jamais dans le futur, au plus 365 jours dans le passe.
- Pas de suppression definitive par les autres roles ; la suppression par l'auteur est autorisee (c'est son carnet) et tracee dans le journal d'audit existant.
- Ecran web : une entree de menu « Notes spirituelles » pour le conseiller (a cote des deux entrees actuelles de toxicologie) et une entree en lecture seule pour le promoteur et l'admin ; liste (la plus recente en premier), formulaire de creation et de modification. Le menu de toxicologie du conseiller et ses droits de lecture actuels ne changent pas.
- Hors ligne : les notes sont saisies en ligne uniquement (pas de PowerSync pour ce chantier) ; un message clair FR/EN s'affiche si le reseau manque et le brouillon n'est pas perdu tant que la fenetre reste ouverte.
- Confidentialite : les notes ne sont jamais incluses dans les exports de dossier ni dans les statistiques existantes. Le guide du conseiller rappelle que les notes sont lues par le promoteur et l'admin.
- Pagination serveur de la liste (comme les autres listes du projet).

## Buts

- Le conseiller saisit une rencontre en moins d'une minute.
- Les notes restent confidentielles : lecture limitee a trois roles, aucune fuite vers les autres ecrans.
- Aucun changement visible pour les autres roles ni pour les ecrans existants.

## Non-buts et anti-buts

- Pas de note par patient, pas de lien avec les dossiers de toxicologie, pas de planning, pas de rappel, pas de statistique de performance du conseiller.
- Pas de PowerSync, pas d'export, pas de partage avec le psychologue ou le medecin.
- Ne pas toucher aux consultations spirituelles facturees ni au carnet vendu a la caisse.

## Contraintes du projet

- Roles verifies cote serveur ; table des routes comparee dans les tests de roles.
- UI : jetons seulement, textes >= 13 px, cibles >= 44 px, FR/EN a cles identiques, ponctuation ASCII, dates jj/mm/aaaa, `authStore.hasRole()`.
- Migration Alembic (tete actuelle `034_product_photo_label_size`), appliquee a la base de developpement, miroir dans `ci/schema_only.sql`.
- Fuseau Douala (`utils/business_time.py`) pour la date par defaut.
- Guides : refaire le guide du conseiller (spiritual-1) et ajuster ceux du promoteur et de l'admin concernes.

## A la charge du constructeur

Noms exacts de table, de colonnes et d'endpoints, forme du formulaire (cases et champ libre), libelles FR/EN, tri et pagination, journal d'audit, tests, mise a jour des guides.
