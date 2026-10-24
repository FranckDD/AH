# Chantier 8 : deploiement en production (VPS OVH, Docker) : conception

Date : 2026-10-24. Statut : propositions techniques validees par l'utilisateur le 2026-10-24 ; reste le plan d'execution, a faire quand on aborde le chantier.

## Pourquoi

Le systeme (API FastAPI, interface Vue, PowerSync pour le travail hors ligne, Postgres, Redis, Celery) ne tourne aujourd'hui que sur le poste de developpement Windows. Le centre de sante doit pouvoir l'utiliser en vrai, les donnees doivent etre protegees, et le systeme doit rester exploitable meme si la personne qui l'a mis en place s'en va. L'utilisateur est debutant en deploiement et sera accompagne pas a pas.

## Ce qui est decide (par l'utilisateur)

- **Hebergement** : un VPS OVHcloud deja achete, Londres, Ubuntu 26.04 LTS, 4 vCore, 8 Go de RAM, 75 Go NVMe, trafic illimite, option "Daily backup" (instantane du disque une fois par jour). Pas de PaaS gere, pas de Supabase : tout en conteneurs Docker.
- **Adresse** : un sous-domaine du site existant (hebergé chez Hostinger) : `app.ahandtohumanity-ngo.org` (nom exact a confirmer le moment venu). Le site Hostinger reste inchange. Seule une entree DNS A, chez Hostinger, dirige le sous-domaine vers l'IP du VPS.
- **Premier usage** : l'admin ouvre l'application depuis son PC, cree les comptes, definit les prix (produits et examens), initialise la caisse (solde de depart, une seule fois). Ce qui doit marcher hors ligne est deja defini par les chantiers precedents (dossier patient, rendez-vous, caisse, formulaires, labo via PowerSync ; la cloture de caisse est en ligne seulement).
- **Mises a jour** : quand le code est pousse sur GitHub (branche de production), la mise a jour doit aussi arriver sur le serveur, automatiquement.
- **Montee en charge / replication** : prevoir la possibilite, ne pas la construire maintenant (voir "Ma recommandation").
- **Sauvegardes** : perdre au maximum quelques heures de donnees en cas de perte du serveur. Aucun stockage hors VPS n'existait : l'hebergement Hostinger (50 Go, 6 % utilises, SSH disponible mais inactif a activer) servira de copie hors serveur, plus une copie occasionnelle (hebdomadaire) sur le PC de l'admin (validee par l'utilisateur).
- **Alertes** : par e-mail au promoteur, a l'admin et au technicien responsable. La liste des destinataires doit etre facile a modifier, car le systeme doit rester maintenu meme si un employe part.
- **Courriels** : le domaine a une boite `recovery@ahandtohumanity-ngo.org` chez Hostinger ; le compte Hostinger lui-meme est cree avec une adresse personnelle (voir "Risques").

## Objectifs

1. Un docker-compose de production qui demarre tout le systeme : proxy HTTPS, interface, API, worker Celery, planificateur, Postgres applicatif, Redis, PowerSync et son stockage.
2. Un deploiement automatique et reversible depuis GitHub.
3. Des sauvegardes testees, chiffrees, dont une copie hors du VPS, avec restauration a l'heure pres (objectif : perdre au maximum les dernieres heures).
4. Des alertes e-mail et une surveillance externe.
5. Un manuel d'exploitation court pour une personne qui n'a pas construit le systeme.

## Non-buts et anti-buts

- Pas de cluster, pas de Kubernetes, pas de replication Postgres sur un second serveur maintenant.
- Pas d'environnement d'essai separe (staging) sur le meme VPS pour l'instant (memoire et complexite) ; les tests automatiques et la sauvegarde avant deploiement en tiennent lieu.
- Le pont d'impression des tickets ne va PAS sur le VPS : l'imprimante est physiquement au centre, le pont reste sur le PC de la secretaire.
- Anti-but : un deploiement qui marche une fois mais que personne d'autre ne sait relancer, restaurer ou reparer ; des secrets uniquement dans la tete ou le poste d'une personne ; une sauvegarde jamais restauree en essai.

## Contraintes techniques (faits relevés dans le code)

- **Fuseau** : tout tourne en `Africa/Douala` : `TZ=Africa/Douala` sur chaque conteneur applicatif (avec `tzdata`), Postgres lance avec `-c timezone=Africa/Douala -c log_timezone=Africa/Douala`. Horloge de l'hote en UTC avec NTP : sans importance. Raison : environ 45 appels `date.today()`/`datetime.now()` et des colonnes `timestamp` sans fuseau supposent l'heure de Douala (audit du 2026-10-24, resume dans `docs/superpowers/SUIVI-AVANCEMENT.md`). Base de production **neuve** : schema par `ci/schema_only.sql` puis `alembic stamp head` (le baseline ne peut pas s'appliquer sur une base vide), plus donnees de reference et roles (`ci/seed_application_roles.sql`) ; les donnees de test actuelles ne migrent pas.
- **Planificateur de cloture de caisse** : `scripts/cash_closure_catchup.py` (idempotent, code de sortie 0 si rien a faire ou si un verrou est pris, non nul si erreur). A lancer toutes les heures a la minute 5 (`5 * * * *`, fuseau Douala) par un conteneur `scheduler` (meme image que l'API, boucle cron) ; la cloture automatique de 23 h est ainsi rattrapee meme apres une panne.
- **PowerSync** : necessite que Postgres tourne avec `wal_level=logical` et une publication ; un petit Postgres de stockage separe (`pg-storage`) pour son etat interne, deja decrit dans `powersync/docker-compose.yaml` (images `journeyapps/powersync-service`, `postgres:18`) ; la configuration de synchronisation est dans `powersync/sync-config.yaml` et `service.yaml`. En developpement PowerSync se connecte au Postgres Windows via `host.docker.internal` ; en production il se connecte au conteneur Postgres applicatif par le reseau Docker interne.
- **Celery/Redis** : Celery est configure `timezone="Africa/Douala"`, sans planification (`beat`) ; l'API et le worker utilisent `REDIS_URL`. Postgres, Redis et PowerSync ne sont pas exposes sur internet.
- **Fichiers deposes** : le dossier `static/uploads/toxico_consents` (consentements scannes) doit etre un volume Docker persistant, sauvegarde avec la base. Le code contient encore un client de stockage Supabase (`api_backend/backend_app/utils/file_storage.py`) : la production n'en utilise pas (decision du 2026-09-29), le stockage local doit etre le chemin par defaut.
- **Redis sur la machine de developpement** : le port 6379 est reserve par Windows ; sans effet en production (conteneurs Linux), mais le developpement continue d'utiliser un Redis de secours sur 16379 tant que le PC n'est pas redemarre.
- **Taille des donnees** : tres petite (base de developpement : 17 Mo pour 106 patients) ; seuls les fichiers deposes peuvent peser.

## Decisions de conception (propositions de l'assistant, a valider ou refuser)

- **Porte d'entree** : Caddy en conteneur, certificat HTTPS obtenu et renouvele automatiquement. Il sert l'interface (fichiers compiles par `vite build`), relaye l'API et le service PowerSync (WebSocket compris) derriere le meme nom de domaine. Seuls les ports 80, 443 et SSH sont ouverts sur le pare-feu.
- **Images** : construites par GitHub Actions et publiees sur le registre de conteneurs de GitHub (GHCR) avec une etiquette de version ; le serveur les telecharge. Pas de compilation sur le VPS.
- **CI/CD** : sur poussee vers la branche de production : tests (serveur et interface), construction des images, puis connexion SSH au VPS : sauvegarde, telechargement des images, migrations Alembic (`upgrade head`), redemarrage des conteneurs un par un, controle de sante. Echec d'un test ou d'un controle : rien n'est deploye ou retour automatique a l'image precedente. Retour manuel en une commande. Les secrets du deploiement sont des secrets GitHub, non commités.
- **Sauvegardes** : copie complete de la base chaque nuit + archivage continu des journaux (restauration a l'heure pres (objectif : perdre au maximum les dernieres heures)), dossier de fichiers deposes, outil chiffrant cote client (restic) ; envoi par SFTP vers Hostinger plusieurs fois par jour, retention a regler ; copie hebdomadaire sur le PC de l'admin ; essai de restauration documente et fait avant la mise en production, puis periodique. L'option OVH "Daily backup" est une protection supplementaire, pas la sauvegarde de reference.
- **Alertes** : surveillance externe de l'adresse publique toutes les 5 minutes (service gratuit de type UptimeRobot) vers la liste d'e-mails ; alertes internes (echec de sauvegarde, disque a plus de 80 %, conteneur qui redemarre en boucle, certificat proche de l'expiration) envoyees par e-mail ; destinataires dans un seul fichier de reglages sur le serveur.
- **E-mails** : l'application n'envoie aucun e-mail aujourd'hui (pas de configuration SMTP). Les alertes passent par un petit expediteur sur le serveur utilisant le SMTP du domaine chez Hostinger (reglages a confirmer dans hPanel ; le mot de passe de la boite va dans le fichier de secrets du serveur, jamais dans une conversation ni dans git).
- **Exploitation** : un manuel court dans le depot (`docs/exploitation/`) : demarrer, arreter, mettre a jour, revenir en arriere, restaurer, changer un destinataire d'alerte, ajouter ou retirer un acces technicien, renouveler un secret. Un seul dossier de configuration sur le serveur, un seul fichier de secrets, sauvegardes de ce fichier chiffre.
- **Montee en charge** : l'API est sans etat et configuree par variables d'environnement, donc plusieurs copies derriere Caddy sont possibles plus tard ; la replication Postgres sur un second serveur n'est pas construite, elle sera etudiee si l'usage ou les exigences de disponibilite le justifient.

## Risques et points d'attention

- Le depot GitHub est `FranckDD/AH` (compte personnel) et le compte Hostinger a ete cree avec une adresse personnelle (gmail). Si ces personnes partent, le centre perd la main. Recommandation : transferer le depot dans une organisation GitHub du centre et rattacher les comptes (GitHub, OVH, Hostinger, domaine) a une adresse de l'organisation, avec au moins deux administrateurs.
- Conditions d'usage de l'hebergement Hostinger pour stocker des sauvegardes : a verifier ; sinon un stockage objet de sauvegarde dedie.
- L'option "Daily backup" d'OVH ne remplace pas la sauvegarde de la base.
- Premiere mise en ligne = base neuve : toutes les donnees de test sont abandonnees ; l'admin doit definir les prix avant la premiere vente (un produit ou examen a 0 est invendable par la secretaire).

## A trancher par le constructeur

- Nom exact du sous-domaine et de la branche de production ; versions precises des images (Postgres, Redis, PowerSync) ; politique de retention des sauvegardes ; fenetre horaire des sauvegardes ; choix de l'outil de cron du conteneur planificateur ; format du manuel ; durcissement du serveur (utilisateur non root, pare-feu, mises a jour de securite automatiques).

## Precisions apres relecture (appels de l'assistant, a verifier)

- **Objectif de perte de donnees** : au maximum les dernieres heures (parole de l'utilisateur). Moyen retenu : sauvegarde complete nocturne + export chiffre de la base **toutes les heures** envoye hors du VPS (Hostinger). Pas d'archivage continu des journaux Postgres (WAL) : il ne survit pas a la perte du serveur sans envoi continu, c'est de la complexite inutile ici. La base est petite, un export horaire est quasi instantane.
- **Echec d'un deploiement apres migration** : regle de migration "ajout seulement" (une migration ne supprime ni ne renomme rien d'utilise par l'ancienne version) ; un retour en arriere remet l'image precedente sans defaire la migration. Si une migration est reellement destructive, le deploiement est fait hors des heures d'ouverture, apres une sauvegarde faite juste avant, et un retour passe par la restauration de cette sauvegarde (on accepte de perdre ce qui a ete saisi entre-temps, d'ou le creneau creux).
- **Premier compte admin** : un script a usage unique (`scripts/create_first_admin.py`) lit l'identifiant et le mot de passe depuis des variables d'environnement ou une saisie au clavier, cree l'admin dans la base neuve et exige un changement de mot de passe a la premiere connexion si l'application le permet (sinon le dire dans le manuel). Les roles viennent de `ci/seed_application_roles.sql`. Le catalogue (produits, examens) est saisi par l'admin dans l'application (il definit deja les prix) : on ne seme pas de catalogue de test.
- **Pont d'impression en HTTPS** : la page servie en `https://app...` appellera le pont local en `http://127.0.0.1:9123`. Les navigateurs recents tolerent le contenu mixte vers `127.0.0.1` mais exigent que le pont reponde aux requetes CORS pour la nouvelle origine, avec l'en-tete de reseau prive (`Access-Control-Allow-Private-Network: true`) pour Chrome. Travail inclus dans ce chantier : liste d'origines autorisees configurable dans le pont, en-tetes, et verification sur le PC de la secretaire avec le navigateur reel. Safari n'est pas garanti.
- **Secrets maitres** : cle de chiffrement des sauvegardes, fichier de secrets du serveur, secrets de deploiement GitHub. Ils sont conserves dans un gestionnaire de mots de passe partage entre au moins deux responsables (organisation Bitwarden gratuite, par exemple), pas sur un seul poste. Sans la cle de chiffrement, toutes les sauvegardes sont inutilisables : une copie scellee de cette cle est aussi remise a l'organisation.
- **Depot GitHub** : si le depot passe dans une organisation du centre, il doit y passer avant la mise en place du deploiement automatique (noms d'images, secrets et cles de deploiement en dependent).

## Reponses de l'utilisateur (2026-10-24)

- Les decisions de conception ci-dessus sont **validees** (Caddy, images GHCR, deploiement SSH automatique, restic, surveillance externe).
- Si Hostinger refuse les sauvegardes : option payante de secours, **a faire valider par le promoteur** avant achat.
- **Depot** : au moment du chantier, il sera deplace dans une organisation du centre **et nettoye** de tous les fichiers inutilises (version desktop PyQt/CustomTkinter, fichiers des tout debuts du developpement, scripts et sauvegardes obsoletes). Nettoyage a inventorier et faire valider avant suppression. Les deux responsables des secrets restent a designer.

