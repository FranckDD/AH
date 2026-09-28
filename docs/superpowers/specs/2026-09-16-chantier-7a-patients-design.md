# Chantier 7a — Formulaire patient (création / modification / suppression)

**Date** : 2026-09-16
**Origine** : registre `L3a` de `SUIVI-AVANCEMENT.md`, sous-projet 1 du chantier 7 (« terminer le portage web »)
**Position** : premier sous-projet du chantier 7, après la clôture du chantier 6 (identité patient + dossier consolidé). Le nettoyage `L4b-e` des gardes de rôle et les autres points parqués par le chantier 6 sont explicitement reportés après le chantier 7 (décision utilisateur, 2026-09-16).

## Objectif

Donner à l'application web un formulaire de création, modification et suppression de patient — aujourd'hui totalement absent. Le seul chemin de création de patient dans toute l'application web est un effet de bord de l'admission toxicologique (`ToxicoController.admission_patient`, sur laquelle le rattachement à un patient existant a été ajouté au chantier 6). Aucun écran ne permet de modifier ou supprimer un patient.

## Pourquoi maintenant

Le backend expose déjà `POST/PUT/DELETE /patients/{id}` (routeur `patients_endpoints.py`), ouverts à 6 rôles. `patientStore.js` contient déjà des ébauches `addPatient`/`deletePatient` non branchées à aucun bouton, et `addPatient` n'envoie que 3 des 10 champs métier modifiables (avec une date de naissance de repli codée en dur, `"2000-01-01"`, quand le champ est absent). C'est le manque le plus large identifié par l'audit du 2026-09-15 (registre `L3a`) et un prérequis naturel pour exploiter correctement le dossier consolidé livré au chantier 6 : sans formulaire de création/modification, la seule façon d'enrichir la fiche d'un patient reste de passer par le détour de l'admission toxicologique.

## Périmètre

**Inclus** :
- Création d'un patient (formulaire complet, 10 champs métier)
- Modification d'un patient existant (même formulaire, pré-rempli)
- Suppression (soft-delete, déjà implémentée côté backend — juste câblée à un bouton avec confirmation)
- Correction du bug de protection des drapeaux de domaine dans `PatientController.update_patient`, exercé pour la première fois de façon réelle par ce formulaire d'édition

**Exclus explicitement** (décisions utilisateur du 2026-09-16) :
- Exports (CSV liste, PDF dossier) — aucun pattern de liste n'existe dans le code aujourd'hui (seuls des exports PDF d'enregistrement unique existent, facture caisse et résultat labo) ; traité comme un sous-projet séparé si besoin plus tard
- Accès hors ligne — chaque sous-projet du chantier 7 statue sur son passage hors-ligne séparément, une fois le sous-projet fonctionnel en ligne, pas avant
- Le nettoyage plus large des gardes de rôle (`L4b-e`) et les autres points parqués par le chantier 6 (accès large du rôle `assistant` sur `/patients/*`, badges de domaine obsolètes dans `patientStore.js`, etc.) — reportés après le chantier 7 (décision explicite du 2026-09-16)
- Toute modification de la politique d'accès : les 6 rôles déjà autorisés côté backend (`medecin, nurse, secretaire, admin, manager, assistant`) sont conservés tels quels côté UI — pas de restriction ni d'élargissement

## Modèle de données — aucun changement

Aucune migration. Toutes les colonnes existent déjà sur `patients` : `first_name`, `last_name`, `birth_date` (obligatoires), `gender`, `national_id`, `contact_phone`, `assurance`, `residence`, `father_name`, `mother_name` (optionnels) — 10 champs métier modifiables au total. `is_clinical`/`is_toxicology`/`is_spiritual` existent aussi mais **ne sont jamais envoyés par ce formulaire** : depuis le chantier 6, ces colonnes ne sont plus la source de vérité (`PatientRepository.compute_domain_flags`, calcul à la lecture) — les exposer dans un formulaire d'édition réintroduirait la confusion que le chantier 6 a justement réglée.

## Section 1 — `PatientModal.vue` (nouveau composant)

**Décision (approuvée par l'utilisateur)** : un seul composant réutilisé pour création et modification, sur le patron déjà établi par `UserModal.vue` — pas deux composants séparés, pas d'édition en ligne dans le tableau.

- **Props** : `patientToEdit: Object | null`. `isEditing = computed(() => !!props.patientToEdit)`, détermine le titre de l'en-tête (« Nouveau patient » / « Modifier le patient ») et pré-remplit le formulaire réactif quand présent (même patron que `UserModal.vue` : `reactive(form)` initialisé dans `onMounted` à partir de `props.patientToEdit`).
- **Champs** (grille 2 colonnes, patron `UserModal.vue`) : prénom*, nom*, date de naissance*, genre (normalisé aujourd'hui côté backend via un validateur Pydantic — le formulaire envoie la valeur choisie telle quelle, la normalisation reste backend), numéro national d'identité, téléphone (normalisé aussi backend, aucune validation stricte côté formulaire au-delà du type), assurance, résidence, nom du père, nom de la mère. (*) = obligatoire, correspond exactement à `PatientCreate` (`first_name`/`last_name`/`birth_date` requis, le reste optionnel).
- **Soumission** : la modale ne fait AUCUN appel réseau elle-même — `emit('save', payload)` avec le formulaire courant, le parent (`PatientList.vue`) appelle le store. C'est le patron `UserModal.vue`, délibérément différent de `ToxicoAdmissionModal.vue` (qui appelle le store directement) — suivi ici car `PatientList.vue` a besoin de réagir après coup (rafraîchir la liste, fermer la modale) de la même façon pour create et update, ce que centraliser dans le parent simplifie.
- **Gestion des erreurs — correction d'un écart trouvé en vérifiant `UserModal.vue`/`UserManagement.vue` en détail** : ce patron existant n'a en réalité **aucun retour visible en cas d'échec** — `userStore.addUser`/`updateUser` ne font qu'un `console.error` puis relancent l'erreur, et `UserManagement.vue::handleSaveUser` l'avale silencieusement (le commentaire « Erreur déjà gérée dans le store » est trompeur : rien n'est montré à l'utilisateur, la modale se contente de ne pas se fermer). Ce n'est pas un patron à reproduire. `PatientModal.vue` ajoute donc un canal que `UserModal.vue` n'a pas : une prop `errorMessage: String | null`, que le parent renseigne depuis son bloc `catch` et que la modale affiche en bannière inline (patron visuel de `ToxicoAdmissionModal.vue`, mappage des statuts HTTP courants — 422 validation, 400 requête invalide, 401 session expirée — vers un message lisible, même logique que `ToxicoAdmissionModal.vue::handleSubmit`'s bloc `catch`, réutilisée côté parent). La modale efface l'erreur affichée dès qu'une nouvelle soumission démarre. Bouton de soumission avec spinner pendant l'appel (état `isSaving`, passé en prop par le parent, même mécanique que l'erreur).
- **Validation minimale côté client** : les 3 champs obligatoires non vides et une date de naissance non future — pas de duplication de la logique de normalisation `gender`/`contact_phone`, qui reste une responsabilité backend (le formulaire envoie la saisie brute, le backend normalise déjà via ses `field_validator`).

## Section 2 — `PatientList.vue`

- **Bouton « Ajouter un patient »** dans la barre d'outils (absent aujourd'hui — actuellement seulement recherche, onglets, pagination), visible pour les 6 rôles déjà autorisés côté backend sur ce routeur. Ouvre `PatientModal` sans `patientToEdit`.
- **Icônes crayon/poubelle par ligne**, patron identique à `UserManagement.vue` (`PencilSquareIcon`/`TrashIcon`, mêmes classes Tailwind). Le crayon ouvre `PatientModal` avec `patientToEdit` défini sur la ligne cliquée. La poubelle appelle une fonction `confirmDelete(patient)` qui utilise `window.confirm(...)` avant d'appeler le store — même patron exact que `UserManagement.vue::confirmDelete`, pas de nouveau composant de confirmation à construire.
- **Après un `save` ou une suppression réussie** : rafraîchir la liste et les compteurs globaux (patron déjà utilisé par `deletePatient` existant dans le store), fermer la modale.

## Section 3 — `patientStore.js`

- **`addPatient(patientData)`** : corrigé pour envoyer les 10 champs métier (au lieu de 3 aujourd'hui) ; suppression du repli codé en dur `"2000-01-01"` sur `birth_date` (un champ obligatoire du formulaire, jamais absent en pratique une fois le formulaire construit — le repli était un contournement pour l'ancien appelant incomplet, plus nécessaire).
- **`updatePatient(patientId, patientData)`** (nouveau — n'existe pas aujourd'hui) : `PUT /patients/{id}` avec les champs modifiés. Suit le même patron d'erreur que les autres actions du store (pas de `alert()` — l'erreur remonte à l'appelant, qui la passe à la bannière de la modale).
- **`deletePatient(id)`** : logique inchangée (déjà correcte — appelle `DELETE /patients/{id}`, filtre l'id localement, rafraîchit les compteurs), seulement rendue atteignable par un vrai bouton.

## Section 4 — Simplification backend : `PatientController.update_patient`

**Correction apportée à cette section après vérification plus poussée (pendant l'écriture du plan, avant tout code) : ce n'est PAS un bug de perte de données.** La version précédente de cette section affirmait qu'un appelant envoyant `is_X: null` effaçait silencieusement le drapeau en base. Faux — vérifié en lisant la procédure stockée réelle `public.update_patient` (`ci/schema_only.sql:901-921`) : `SET is_clinical = COALESCE(p_is_clinical, is_clinical), ...` — un `NULL` reçu par la procédure **préserve** la valeur existante, il ne l'efface jamais. La base protège déjà contre ce cas, indépendamment de ce que fait le code Python en amont.

**Ce qui reste vrai** : le bloc de `PatientController.update_patient` (lignes 118-131) qui recalcule `data['is_clinical']`/`is_spiritual`/`is_toxicology` avant l'appel au dépôt est **redondant et trompeur**, pas dangereux. Il duplique en Python — de façon partielle et confuse (mélange de rôles `app_*` jamais vus ailleurs dans le code actuel comme `app_toxico_web`, alias qui ne correspondent à aucun rôle réel du système depuis le chantier 6) — une protection que la procédure stockée assure déjà correctement et simplement via `COALESCE`. Depuis le chantier 6, ces 3 colonnes ne sont de toute façon plus une source de vérité (`compute_domain_flags`, calcul à la lecture par `EXISTS`) : aucun code ne devrait plus jamais avoir besoin de les écrire après la création initiale.

**Simplification (décision utilisateur confirmée après cette correction)** : retirer les lignes 118-131 de `update_patient` — ne plus construire `data['is_clinical']`/`is_spiritual`/`is_toxicology` du tout côté Python. Le dépôt (`repositories/patient_repo.py::update_patient`, lignes 162-164) continue de faire `data.get('is_X')` → `None` si absent → la procédure stockée les laisse alors inchangés via `COALESCE`, exactement le comportement souhaité, obtenu plus simplement. Le formulaire de 7a n'envoie jamais ces 3 champs (Section 1), donc `data` ne les contiendra jamais en pratique sur ce chemin — cette simplification retire du code mort/confus, elle ne change aucun comportement observable aujourd'hui.

## Définition du « terminé »

- Un patient peut être créé depuis `PatientList.vue` avec les 10 champs métier, vérifié en base (pas de date de naissance codée en dur, tous les champs saisis effectivement persistés).
- Un patient existant peut être modifié via le formulaire, sans jamais envoyer les 3 drapeaux de domaine. Un test confirme que `PatientController.update_patient` ne construit plus ces 3 clés (code mort retiré) et que la mise à jour d'un patient laisse ses drapeaux réels (calculés) inchangés.
- Un patient peut être supprimé (soft-delete) avec confirmation ; il disparaît de la liste (déjà filtrée sur `is_deleted`) sans que ses dossiers médicaux/prescriptions/etc. associés ne soient affectés (déjà garanti par le mécanisme de soft-delete existant, aucun changement requis ici — simplement vérifié).
- Le bouton « Ajouter un patient » et les icônes crayon/poubelle sont visibles exactement pour les 6 rôles déjà autorisés côté backend, ni plus ni moins.
- Aucun export, aucun changement de politique d'accès, aucun travail hors ligne dans ce sous-projet.
- Suite de tests existante non régressée ; nouveaux tests pour chaque point ci-dessus.
