# Psychologues : vue limitee par l'admin et transfert d'un patient (conception)

Date : 2026-10-27. Statut : decrite et validee en discussion par l'utilisateur ; relue par un constructeur independant ; APPROUVE par l utilisateur le 2026-10-27.

## Pourquoi

Aujourd'hui un seul psychologue suit tous les patients de toxicologie. Le centre va grandir : plusieurs psychologues arriveront. Il faut que le logiciel soit pret : pouvoir limiter ce que voit chaque psychologue, et pouvoir faire passer un patient d'un psychologue a un autre sans perdre la trace de ce que le premier a fait.

## Ce qui est decide (par l'utilisateur)

- **Limiter la vue** : l'admin peut regler, pour chaque psychologue, « ne voit que ses propres patients ». Version simple uniquement : pas de liste de patients ou de psychologues autorises. Par defaut le reglage est desactive : le psychologue voit tous les patients de toxicologie, comme aujourd'hui.
- **Transferer** : un patient de toxicologie peut passer d'un psychologue a un autre. Seuls l'**admin** et le **responsable de toxicologie** (ToxicoManager) decident un transfert. Le psychologue qui cede son patient ne peut pas le decider.
- **Tracabilite** : ce que le premier psychologue a fait reste visible et garde son nom.

## Ce qui est suppose (appels de l'assistant, a faire relire)

- Le psychologue « referent » d'un patient est `toxico_dossiers.psychologist_id` (aussi `toxico_stays.psychologist_id` par sejour). Le transfert change le referent du dossier **et celui du sejour ouvert** ; les sejours deja clos gardent leur psychologue.
- Le transfert est enregistre dans une nouvelle table (de qui, vers qui, date et heure, qui a decide, motif). Le **motif est obligatoire**. Les transferts s'affichent dans l'historique du dossier.
- Les evaluations existantes gardent leur auteur (`toxico_evaluations.created_by`) : rien a changer ; le nouveau psychologue voit tout l'historique du dossier.
- Le nouveau psychologue recoit une notification (type dedie, FR et EN) avec un lien vers le dossier ; l'ancien n'est pas notifie (le motif est dans l'historique).
- **Evaluer (decide par l'utilisateur)** : seul le psychologue referent du dossier peut ajouter une evaluation, **toujours**, y compris quand aucun psychologue n'est limite. Changement voulu par rapport a aujourd'hui (ou n'importe quel psychologue pouvait evaluer n'importe quel patient). Si le referent est vide ou n'est pas un psychologue, aucun psychologue ne peut evaluer tant que l'admin ou le responsable n'a pas assigne un psychologue. L'admin et le responsable de toxicologie n'evaluent pas (inchange).
- **Apres un transfert (decide par l'utilisateur)** : l'ancien psychologue, s'il est limite, ne voit plus le patient dans ses listes, ses compteurs et ses exports. Il garde un acces **en lecture seule** a l'historique des patients qu'il a suivis (voir ci-dessous). Ses evaluations restent visibles au nouveau psychologue et a l'admin, avec son nom.
- **Lecture seule de l'historique (decide, forme = appel de l'assistant)** : un onglet distinct, « Patients suivis auparavant », liste les patients dont il a ete referent ou dont il a ecrit une evaluation (un transfert, un sejour ou une evaluation a son nom). Ouvrir un dossier depuis cet onglet montre l'historique complet **sans** les boutons d'action (pas d'evaluation, pas de sortie) ; le serveur refuse toute ecriture. Un psychologue non limite voit tout en lecture/ecriture comme aujourd'hui, avec la seule restriction d'evaluer (ci-dessus).
- Pour un psychologue limite : les listes (patients actifs et sortis), les compteurs et statistiques du tableau de bord toxicologie, la recherche, le detail d'un dossier, le dossier complet et les exports PDF/Excel ne montrent que ses patients actuels (referent du dossier). Les statistiques ne montrent que ses propres chiffres : la repartition par psychologue et la ligne « Non assigne » sont masquees. Un patient sans referent n'est visible que de l'admin et du responsable de toxicologie. Un acces direct a un dossier hors perimetre est refuse (403/404), pas seulement cache dans la liste, sauf l'acces en lecture seule decrit plus haut.
- **Cible et regles du transfert (appels de l'assistant)** : la cible est un compte actif de role Psychologist uniquement ; un patient sans referent (ou dont le referent n'est pas un psychologue) peut recevoir un premier referent par le meme ecran ; un transfert vers le referent actuel est refuse ; un transfert est possible pour un patient sorti (seul le referent du dossier change, pas de sejour ouvert) ; le transfert, le changement de referent du dossier et du sejour ouvert, et la notification forment une seule transaction ; une readmission propose le referent actuel ; si l utilisateur choisit un autre psychologue, un transfert automatique avec le motif « Readmission » est enregistre dans la meme transaction (aucune notification pour ce transfert automatique). Note : `flags.is_toxicology` du dossier patient consolide reste visible pour un patient hors perimetre du psychologue limite (decision en attente du proprietaire) ; seul le bloc toxicologie est retire.
- **Autres roles (appel de l'assistant)** : la limite ne s'applique qu'aux comptes de role Psychologist ; le reglage est ignore pour les autres roles (comme `is_head_nurse` hors infirmier). Pour le dossier patient consolide (`/patients/{id}/dossier`), la limite ne porte que sur le bloc toxicologie ; elle ne rend pas tout le patient inaccessible.
- **Hors ligne / lecture (appel de l'assistant)** : l'historique des transferts est lu par les endpoints toxicologie serveur (pas de table PowerSync).
- Le reglage est un booleen sur le compte (`users`), modifie par l'admin dans la fiche du compte d'un psychologue, sur le modele de `is_head_nurse` (drapeau de privilege dans un role existant, pas un nouveau role). Les parties du circuit utilisateur a ne pas oublier sont celles que ce modele a deja pieges : creation (POST), modification (PUT), lecture de la liste, forme de l'utilisateur dans `auth.js` / `authStore.user`, `UserModal.vue`, `userStore.js`.

## Buts

- Un psychologue limite ne voit jamais un patient qui n'est pas le sien (liste, detail, exports, stats).
- Un transfert est trace de bout en bout et visible dans le dossier.
- Aucun changement visible tant qu'il n'y a qu'un seul psychologue et que le reglage est desactive.

## Non-buts et anti-buts

- Pas de liste personnalisee de patients autorises, pas de groupes de psychologues, pas de transfert propose ou demande par le psychologue lui-meme.
- Pas de perte d'historique : jamais de reassignation silencieuse des evaluations, jamais de suppression.
- Ne pas toucher aux autres roles de toxicologie (conseiller spirituel, assistant) : leur perimetre reste inchange.

## Contraintes du projet

- Roles verifies cote serveur, table des routes comparee dans les tests de roles.
- UI : jetons seulement, textes >= 13 px, cibles >= 44 px, FR/EN a cles identiques, ponctuation ASCII, dates locales (jj/mm/aaaa), `authStore.hasRole()`.
- Fuseau Douala (`utils/business_time.py`) pour la date du transfert.
- Migration Alembic (la tete est `031_lab_param_order`) ; appliquee a la base de developpement, miroir dans `ci/schema_only.sql`.
- Les listes toxicologie passent par `ToxicoRepository` (get_psychologists, listes, stats, exports) : le filtre de perimetre doit etre applique a un seul endroit reutilise par tous ces chemins.
- Le dossier du patient (`/patients/{id}/dossier`, onglet Toxico) et les exports du dossier complet lisent aussi les donnees toxicologie : verifier qu'ils respectent la limite.
- Hors ligne : les ecrans de toxicologie appellent le serveur (pas de PowerSync) ; le filtrage est donc cote serveur.

## A la charge du constructeur

Forme exacte de la table des transferts et des endpoints, emplacement du bouton « Transferer » dans l'ecran de suivi toxicologie (visible seulement pour l'admin et le responsable), libelles, maniere de montrer les transferts dans l'historique du dossier, tests, guides utilisateur a mettre a jour (toxicologie 1 et 2, psychologue, admin 1) une fois livre.
