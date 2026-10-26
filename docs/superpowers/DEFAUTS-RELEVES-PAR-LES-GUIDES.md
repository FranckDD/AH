# Défauts et questions relevés pendant la rédaction des 21 guides (2026-10-26)

Liste unique, classée par priorité, à éclaircir avec l'utilisateur puis à corriger. Hors liste, déjà décidés : les boutons PDF marchent (IDM les intercepte dans le Chrome de test) ; l'infirmier peut enregistrer une ordonnance ; l'admin ne compte pas le stock ; examens à 0 FCFA et nom du menu latéral ne sont pas des défauts.

## A. Graves (données de santé, argent, perte de données)

1. **Notification d'aggravation jamais enregistrée** (`HospitalizationController._notify_team_of_aggravation` : `NotificationRepository.create` ne fait qu'un flush, aucun commit). L'équipe infirmière n'est jamais alertée. Confirmé 3 fois (médecin 2, infirmier 1 et 2).
2. **Fichiers de consentement de toxicologie servis sans connexion** (`/static/uploads/toxico_consents/...`, GET non authentifié = 200), nommés `None_None_<horodatage>.pdf`. Données de santé exposées.
3. **Évaluation toxicologique enregistrée deux fois** (`ToxicoEvaluationModal` puis `ToxicoList.handleSaveEvaluation`) : doublons dans l'historique et le PDF, rechutes doublées, taux de rechute gonflé (23 % puis 31 %).
4. **Patient enregistré hors ligne par l'infirmier : formulaire de mesures sans code patient.** Enregistrer ne fait rien, les mesures sont perdues sans échec de synchro listé (reproduit 3 fois).
5. **Laboratoire : un examen terminé peut être rouvert et revalidé**, ce qui remplace en silence des valeurs déjà lues par le médecin.
6. **Laboratoire : patient facturé à la caisse sans ordonnance** ne peut pas être reçu comme dossier existant et la facture n'atteint pas le labo ; **un ordre déjà exécuté est encore proposé** (réception en double possible).
7. **Fuseaux horaires mélangés** : séjours (`admitted_at` local, `discharged_at` UTC, durées « 0 jour(s) », sortie avant admission) ; écran Mouvements en UTC contre comptage en local.
8. **Sortie de toxicologie d'un patient hospitalisé** sans avertissement, séjour hospitalier laissé ouvert.
9. **Fiche labo imprimée** : sexe « X » pour une femme, valeurs de référence « - », drapeau manuel Haut imprimé « * * », plage des érythrocytes non adaptée au sexe.
10. **Produit de catégorie « Other » : catégorie affichée vide** dans la fenêtre de modification (l'enregistrement peut changer la catégorie).

## B. Fonctionnels à corriger

- **Médecin** : après « Take in charge » ou « Start consultation » depuis un rendez-vous, le formulaire ne s'ouvre pas (liens `?record=` et `?appointmentId=` sans effet, rendez-vous reste En attente) ; auteur « Inconnu » et signes vitaux « - » jusqu'au rechargement ; Reject d'un rendez-vous sans confirmation ; onglet Traitements : « undefined » et « DEMANDE D'EXAMEN N/A » ; colonne Type = NEW pour des patients ayant des consultations ; nouveaux patients pas en tête de liste.
- **Hospitalisation** : motif d'admission jamais affiché ; export du dossier sans séjours ni notes de sortie ; compteur « Current stays » en cache 300 s ; lettre de sortie et export du dossier entièrement en français, page 2 presque vide.
- **Admin** : colonne Rôle de la liste des utilisateurs affiche le groupe de sécurité (`application_role` contre `role_name`) ; identifiant modifiable à l'écran mais ignoré ; doublon d'identifiant sans message ; compte inactif = même message que mauvais mot de passe ; création de produit sans péremption échoue (« [object Object] ») ; dosage non enregistré ; aucun écran pour ajouter ou modifier les paramètres d'un examen ; catalogue labo sans prix ni modification ; clé brute `config.delete_confirmation`.
- **Configuration système** : sauvegarde factice (attente 3 s puis « terminée »), interrupteur de maintenance local à l'écran ; historique des connexions arrêté au 3 déc. 2025 ; colonne Détails de l'audit presque toujours « - ».
- **Caisse** : liste des retraits avec codes bruts SUPPLIES, BILLS, OTHER ; dialogue d'annulation d'un retrait « Cancel Transaction » ; « total reçu aujourd'hui » alors que la période court depuis la dernière clôture ; aucun contrôle bloquant un retrait supérieur à la caisse (lu dans le code) ; liste des clôtures sans l'heure ; ajustements de caisse sans notification (ni promoteur ou admin, ni retour à la secrétaire) et absents du contrôle quotidien ; grand livre « +0 FCFA » pour des factures libérées et « New Transaction » qui crée de vrais retraits.
- **Réductions et promoteur** : refus avec pourcentage choisi accepté et pourcentage ignoré (à harmoniser) ; sous-titre « Read only. » des clôtures alors que le promoteur y décide ; sous-titre du comptage de stock inadapté au promoteur ; page d'accueil du promoteur : « Indisponible » (403) et actions rapides d'admin.
- **Labo** : menu sans « Lab history » (route ouverte) ; alertes labo sans entrée de menu (contrôleur) ; ordre des paramètres modifié après brouillon ; aucun message après Save ou Validate ; pastilles « In progress » périmées ; filtre Pending incomplet ; noms patients incohérents ; formulaire de réception labo : cases « Checked » facultatives ; chaque produit compté à la même valeur crée un mouvement nul ; liste des péremptions garde un lot tant qu'il reste du stock ; origine « Expiry » jamais créée ; produit créé à 0 « Low » sans demande.
- **Stock** : clic sur la notification d'ajustement envoie le contrôleur vers /forbidden ; historique du comptage sans l'issue ; pas de liste des demandes du contrôleur ; portée « sélection » identique à « tous » ; erreur de ligne qui persiste ; auteur = identifiant de connexion.
- **Toxicologie** : tuile « Admissions (Month) » à 0 ; sexe toujours « M » pour un patient créé par le formulaire d'admission ; liste du psychologue référent = tout le personnel ; réadmission : substance remise à Alcool et champs du tuteur vides ; pas de statut de sortie dans l'onglet de suivi ; date de sortie non antidatable ; aucune confirmation après admission ; tuiles du suivi qui suivent la boîte de recherche ; menu « Users » avec boutons d'écriture pour le responsable ; nom de la mère « Not provided ».
- **Production** : pas de cloche ni de notification de seuil d'intrant, et le contrôle quotidien ignore `intrant_sous_seuil` (`reports_controller.py:623`) ; achat annulé garde sa quantité dans « Remaining » ; modification d'un achat sans écran ; lot rouvert garde le drapeau hors tolérance ; coût par bouteille arrondi à 188 (API 188,24) ; sous-titres « 1 batches » et lots annulés comptés ; bouton Annuler montré à l'assistant sur un lot d'autrui.
- **Infirmier et planning** : aucun contrôle de conflit de garde ; vue mensuelle coupe les noms ; planning hors ligne « No nurse assigned. » ; toast « Measurements saved. » en jaune d'alerte.

## C. Transverses (à traiter une seule fois)

- **Hors ligne trompeur** : indicateur « Offline (your entries are saved) » affiché en ligne pour admin, promoteur, psychologue, spirituel, toxico, assistant, contrôleur, production (cause commune probable, à diagnostiquer) ; écrans hors ligne qui montrent « 0 » ou « No ... found » comme si c'était vide (tableaux de bord, listes, onglets, labo).
- **Textes français dans l'interface anglaise** : page Accès Interdit, messages serveur, bandeaux, libellés d'anomalies du contrôle quotidien, cloche, motifs générés, alertes navigateur, PDF.
- **Caractères interdits** : tiret long dans « Patient already followed — readmission », flèche dans le PDF du dossier toxico, caractères « · » sur l'écran des demandes de stock.
- **Formats de date mêlés** (jj/mm/aaaa dans les champs, mm/jj/aaaa dans les listes) ; date ISO brute dans la notification du contrôle quotidien.
- Pluriels « (1 requests) », « 1 batches », « Sample output of 1 bottles » ; clé brute `appointments.calendar.weekdays_short` dans le calendrier.

## D. Décisions à prendre

1. Écran de suivi spirituel (décidé, à concevoir) : notes saisies par le conseiller spirituel ; refaire ensuite son guide.
2. Le psychologue voit tous les patients de toxicologie et peut évaluer n'importe lequel : voulu ?
3. Fichiers de consentement : stockage protégé (nom, accès authentifié).
4. DECIDE (revirement 2026-10-26) : le responsable de production aura une cloche et des alertes de seuil d intrant.

## E. À nettoyer avant la mise en production

Comptes `doc_*` ; patients de démonstration ; 5 clôtures manuelles et leurs ajustements ; lots, achats, intrants et réceptions de démonstration ; comptages de stock (dates `counted_at` antidatées : comptages 96, 118, 369, 370 et deux `last_counted_at`) ; fichiers de `static/uploads/toxico_consents/` ; notifications et journaux d'audit de test ; `users.postgres_role` de `doc_laborantin` (la contrainte `chk_technician_role` exige `app_laborantin` pour les vrais comptes laborantin) ; tables à NE PAS vider : examens enregistrés et leurs paramètres (liste complète à établir avec l'utilisateur).

## F. Guides à corriger ensuite

Passages disant que les PDF échouent (promoteur 1, médecin 1 et 2, laborantin 1, infirmier 2) ; guide du conseiller spirituel à refaire après l'écran ; régénérer les guides touchés par les corrections de la section B.
