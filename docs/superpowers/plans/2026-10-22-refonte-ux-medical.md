# Refonte UX de l'espace médical — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Moderniser l'apparence et l'ergonomie de l'espace médical (rôles `medecin` et `nurse`) et de la page de connexion, **sans changer aucun comportement métier**, avec un système de design réutilisable (jetons + composants `ui/`).

**Architecture:** Jetons de design **ajoutés** dans `@theme` (`src/style.css`) sous de nouveaux noms (`brand-*`, `nav-*`, `tone-*`), police locale, nouvelle bibliothèque `src/components/ui/`, puis migration écran par écran de l'espace médical. Les composants partagés existants et les autres espaces ne changent pas.

**Tech Stack:** Vue 3.5, Tailwind 4 (CSS `@theme`), vue-i18n 11, Heroicons, PowerSync (état de connexion), tests `node --test`, `vite build`.

**Spec:** `docs/superpowers/specs/2026-10-22-refonte-ux-medical-design.md` (autorité ; sa section « Hypothèses du concepteur » fixe la portée, la file de tâches, le formulaire de consultation en panneau, les points de contrôle). Références visuelles : `Image_propos_test_ui/` (style seulement, jamais le contenu).

## Global Constraints

- **Aucun changement de comportement** : dans les vues et composants existants, la partie `<script>` ne change que pour importer/utiliser les nouveaux composants `ui/` ; chaque autre modification de logique doit être listée et justifiée dans le rapport de la tâche et sera contestée en revue. Droits, routes, hors ligne (PowerSync), règle de lecture seule des consultations passées, notifications, impressions et exports restent identiques. `router/index.js` n'est modifié que s'une tâche le dit.
- **Portée** : seuls `MedicalLayout.vue`, les écrans médicaux listés, `LoginView.vue` et les nouveaux fichiers changent. Interdits : `MainLayout.vue`, `SecretaireLayout.vue`, les écrans labo/toxico/stock/caisse/admin, `components/common/Modal.vue`, `Pagination.vue`, `ToastContainer.vue`, `components/dashboard/StatCard.vue`, `NotificationBell.vue` (partagés : ils gardent leur apparence). Un composant partagé peut être **dupliqué** en version `ui/` mais pas modifié.
- **Jetons** : tous les jetons dans `src/style.css` (`@theme`), noms nouveaux uniquement (`--color-brand-*`, `--color-nav-*`, `--color-tone-*`, `--radius-card`, `--radius-control`, `--shadow-card`, `--text-*` si besoin) ; aucun hexadécimal ni couleur Tailwind brute pour la marque ou les états dans les nouvelles vues ; couleurs d'état : rouge = urgent/erreur, orange = attention, vert = fait/validé, bleu = information ; **une seule couleur d'action principale** (teal de marque). Palette de marque : bleu nuit (menu) et vert-teal (action), proches du logo ; valeurs exactes à fixer par l'implémenteur de la Tâche 1 et **validées AA par un test automatique** (texte normal ≥ 4,5:1, grand texte et composants ≥ 3:1).
- **Typographie** : police sans empattement lisible embarquée **localement** (paquet `@fontsource-variable/inter` ou équivalent, aucun CDN ; application installable/hors ligne), texte de base **15 à 16 px**, petit texte jamais < 13 px, interlignage généreux.
- **Ergonomie** : zones tactiles ≥ 44 px sous `lg`, libellés au-dessus des champs, astérisque sur les champs obligatoires, **icônes seulement** dans le menu, sur les boutons d'action et pour les états (pas dans chaque champ ni sur chaque titre), états jamais portés par la seule couleur, focus visible, `aria-describedby` pour aide/erreur, menu **avec libellés toujours visibles** (tiroir sous `md`), messages d'erreur en langage clair, confirmation avant action irréversible (existante : ne pas supprimer).
- **Adaptabilité** : téléphone 360 px (cartes empilées, pas de défilement horizontal de la page), tablette 768 px (`md:` deux colonnes), PC 1280 px (`lg:` vrais tableaux) ; style mobile par défaut puis `md:` / `lg:`.
- **i18n** : tout texte visible en FR **et** EN, clés ajoutées sous des préfixes propres (`ui.*`, `medicalShell.*`, etc.), clés existantes conservées quand le sens ne change pas ; le test `tests/i18nMessagesCompile.test.mjs` (parité FR/EN + compilation) doit rester vert ; un test de clés par tâche si de nouvelles clés sont utilisées dans des composants.
- **Contenu réel uniquement** : aucune donnée, statistique, bloc ou fonctionnalité inventés ; **pas de recherche de patient globale** (refusée) ; la photo de la page de connexion est facultative (variante sans photo d'abord).
- Vérification à chaque tâche : `node --test ah2-admin-web/tests/*.test.mjs` puis `cd ah2-admin-web && npx vite build` **en dernier** (aucun avertissement nouveau). Les agents n'ont pas de navigateur : le rendu réel est vérifié par l'utilisateur ; chaque tâche **liste les classes/points visuels à regarder** pour sa checklist. Pas de commit (l'utilisateur décide). Disque C: presque plein : aucune copie du dépôt ; ne pas ajouter d'images lourdes (> 100 Ko) ni de polices inutiles.
- Rapport de chaque tâche : `.superpowers/sdd/<workspace>/task-N-report.md` avec la liste des fichiers, la liste des changements de logique (idéalement « aucun »), les breakpoints par écran, et la checklist visuelle pour l'utilisateur.

## Review Focus

- Un écran médical qui perd une fonction, un bouton ou un droit (régression silencieuse en changeant le gabarit) : comparer avant/après élément par élément. Test : revue de diff par tâche (liste des actions/boutons avant et après dans le rapport).
- Les consultations passées en lecture seule, le hors-ligne et la synchronisation continuent de fonctionner (boutons masqués, messages, quarantaine) après la migration des écrans Dossier médical, Prescriptions et Fiche patient. Test : les tests node existants (`consultationLock`, `consultationReadonlyI18nKeys`, stores) restent verts et la revue vérifie que les props/événements des composants restyle n'ont pas changé.
- Contraste insuffisant ou texte trop petit sur tablette (gris clair sur blanc, placeholders) et zones tactiles < 44 px. Test : test automatique des paires de jetons (Tâche 1) + revue des classes.
- Un autre rôle (secrétaire, labo, toxico, admin) voit son interface changer par effet de bord (CSS global, jetons qui écrasent des couleurs, composant partagé modifié). Test : revue de `style.css` (ajouts seulement), `git diff` limité aux fichiers autorisés.
- La page de connexion : redirection par rôle (`getPostLoginPath`), erreurs de connexion, limitation de débit et « mot de passe oublié » inchangés ; chargement rapide sur 7 Mbps. Test : les tests `postLoginRoute` restent verts, revue de `LoginView.vue` (script inchangé), poids du bundle/asset.

## Phases et points de contrôle

Phase 1 = Tâches 1-4 (fondations, cadre, connexion). Phase 2 = Tâches 5-7 (tableau de bord, rendez-vous, hospitalisations, rotations). **Point de contrôle utilisateur + test d'utilisation avec 2-3 membres du personnel après la Tâche 7** (protocole produit à la Tâche 7). Phase 3 = Tâches 8-11. Tâche 12 = recette finale.

---

### Task 1: Jetons de design, police locale et test de contraste

**Files:**
- Modify: `ah2-admin-web/src/style.css` (ajouts seulement dans/à côté de `@theme`, sans toucher aux règles existantes), `ah2-admin-web/package.json` (+ `package-lock.json`), `ah2-admin-web/src/main.js` (import de la police)
- Create: `ah2-admin-web/src/design/tones.js`, `ah2-admin-web/tests/designTokens.test.mjs`, `ah2-admin-web/tests/tones.test.mjs`

**Interfaces:**
- Produces (CSS) : jetons `--color-brand-{50,100,500,600,700,800}`, `--color-nav-{800,900}` + `--color-nav-text`, `--color-tone-{danger,warning,success,info,neutral}-{bg,text,border}`, `--radius-card` (12px), `--radius-control` (8px), `--shadow-card`, `--font-sans` (police locale puis repli système), tailles de texte de base.
- Produces (JS) : `src/design/tones.js` exporte `TONES = ['danger','warning','success','info','neutral']`, `toneClasses(tone)` → chaîne de classes Tailwind utilisant les jetons (`bg-tone-success-bg text-tone-success-text border-tone-success-border`…), repli sur `neutral` pour une valeur inconnue (jamais d'exception), et `isTone(value)`.

- [ ] **Step 1: Tests (écrits d'abord, vus en échec)** : `tests/designTokens.test.mjs` lit `src/style.css`, en extrait les jetons de couleur par expression régulière et calcule le rapport de contraste WCAG de chaque paire déclarée : texte de menu sur `nav-800/900`, `tone-*-text` sur `tone-*-bg`, blanc sur `brand-600/700` (bouton principal), `brand-700` sur blanc (liens), gris de texte secondaire sur blanc et sur le fond de page ; seuils 4,5 et 3 ; le test échoue si un jeton attendu est absent. `tests/tones.test.mjs` : classes par tonalité, repli, `isTone`.
- [ ] **Step 2: Lancer** `node --test ah2-admin-web/tests/designTokens.test.mjs ah2-admin-web/tests/tones.test.mjs` — attendu : échec.
- [ ] **Step 3: Implémenter** jetons, `tones.js`, police locale (`npm install @fontsource-variable/inter`, import dans `main.js`, uniquement les sous-ensembles latin nécessaires), texte de base 15–16 px posé sur `body` **sans changer la mise en page des autres espaces** (si une taille de base globale risque de les décaler, la poser seulement sur un conteneur `.app-refonte` ajouté à `MedicalLayout` et à la page de connexion dans les tâches suivantes).
- [ ] **Step 4: Vérifier** `node --test ah2-admin-web/tests/*.test.mjs` puis `cd ah2-admin-web && npx vite build` (dernier) ; contrôler que `git diff` de `style.css` ne contient que des ajouts.

---

### Task 2: Bibliothèque de composants `ui/`

**Files:**
- Create: `ah2-admin-web/src/components/ui/{AppButton,AppCard,PageHeader,StatusBadge,EmptyState,FormField,FormSection,ActionBar,ResponsiveTable}.vue`, `ah2-admin-web/src/components/ui/index.js` (réexports), `ah2-admin-web/src/views/dev/StyleGuideView.vue`, `ah2-admin-web/tests/uiComponents.test.mjs`
- Modify: `ah2-admin-web/src/router/index.js` (une seule route `/dev/styleguide`, ajoutée **uniquement si `import.meta.env.DEV`**), `ah2-admin-web/src/i18n.js` (clés `ui.*` FR+EN : « Aucun résultat », « Fermer », « Réessayer », libellés d'aide par défaut…)

**Interfaces:**
- Consumes (Task 1) : jetons, `toneClasses`.
- Produces (props/slots exacts) :
  - `AppButton` : props `variant` ('primary'|'secondary'|'danger'|'ghost', défaut 'primary'), `size` ('md'|'lg'), `loading` (bool), `disabled`, `type` (défaut 'button'), `icon` (composant Heroicons optionnel) ; slot par défaut ; hauteur min 44 px sous `lg` ; pas de double soumission (désactivé pendant `loading`) ; émet `click` natif.
  - `AppCard` : props `title`, `subtitle` ; slots `default`, `actions`, `footer`.
  - `PageHeader` : props `title`, `subtitle` ; slot `actions` (boutons à droite sous `md` : empilés).
  - `StatusBadge` : props `tone` (TONES), `label` ; affiche un petit point + texte (état jamais par la couleur seule).
  - `EmptyState` : props `title`, `message`, `icon` ; slot `action`.
  - `FormField` : props `id`, `label`, `required` (bool), `help`, `error` ; slot `default` (le contrôle) avec `aria-describedby` géré via une valeur fournie au slot (`slot props: { describedBy }`).
  - `FormSection` : props `title`, `subtitle`, `collapsible` (défaut false), `defaultOpen` (défaut true) ; bouton d'entête accessible (`aria-expanded`).
  - `ActionBar` : barre collante en bas (`sticky bottom-0`) avec slots `secondary` (gauche) et `default` (droite) ; sous `md` les boutons passent en pleine largeur.
  - `ResponsiveTable` : props `columns` (`[{key,label,align?,class?}]`), `rows` (tableau), `rowKey` (chaîne), `loading`, `emptyTitle`, `emptyMessage` ; slots `cell-<key>` (props `{row}`), `card` (props `{row}`, rendu carte sous `lg`), `actions` (props `{row}`) ; tableau avec en-tête collant à partir de `lg`, cartes empilées dessous ; affiche `EmptyState` si `rows` vide.
- Le guide de style (`StyleGuideView.vue`) montre chaque composant dans chaque état avec **des données factices clairement étiquetées « exemple »** ; il n'est joignable qu'en développement.

- [ ] **Step 1: Tests node** (`uiComponents.test.mjs`) des parties logiques extraites en utilitaires purs si besoin (ex. calcul de `aria-describedby`, choix des classes de variante/taille, normalisation des colonnes de `ResponsiveTable`) — les écrire d'abord et les voir échouer ; test de parité de clés `ui.*` (ou extension de `i18nMessagesCompile.test.mjs`).
- [ ] **Step 2: Lancer** `node --test ah2-admin-web/tests/uiComponents.test.mjs` — attendu : échec.
- [ ] **Step 3: Implémenter** les composants (accessibilité : libellé associé, focus visible, `aria-*`), le guide de style et la route de développement.
- [ ] **Step 4: Vérifier** `node --test ah2-admin-web/tests/*.test.mjs` puis `cd ah2-admin-web && npx vite build` (dernier) ; vérifier que la route de style n'apparaît pas dans le build de production (recherche dans `dist/` du libellé de la vue).

---

### Task 3: Cadre `MedicalLayout` — menu, barre du haut, indicateur de connexion

**Files:**
- Modify: `ah2-admin-web/src/components/layout/MedicalLayout.vue`
- Create: `ah2-admin-web/src/components/ui/ConnectionStatus.vue`, `ah2-admin-web/src/composables/useConnectionStatus.js`, `ah2-admin-web/src/utils/connectionStatus.js`, `ah2-admin-web/tests/connectionStatus.test.mjs`
- Modify: `ah2-admin-web/src/i18n.js` (clés `medicalShell.*` FR+EN : sections de menu, états de connexion)

**Interfaces:**
- Consumes (Tasks 1-2) : jetons, composants `ui/`, `NotificationBell`, `AccountModal`, `useSyncQuarantineCount`, `db` de `@/powersync-client/client` (PowerSync : `db.currentStatus` avec `connected`, `connecting`, `hasSynced`, `dataFlowStatus.{uploading,downloading}` ; écoute via `db.registerListener({ statusChanged })` ; opérations en attente via `db.getUploadQueueStats()` — **vérifier les noms exacts dans la version installée de `@powersync/web` avant de coder et les consigner dans le rapport**).
- Produces : `utils/connectionStatus.js` exporte `resolveConnectionState({ connected, connecting, hasSynced, uploading, pending, hasError })` → `{ state: 'online'|'syncing'|'pending'|'offline'|'error', pending }` (pure, testée) ; `useConnectionStatus()` retourne `{ state, pending }` réactifs (écouteur retiré au démontage, jamais d'exception si `db` indisponible → état 'offline') ; `ConnectionStatus.vue` affiche « Connecté », « Synchronisation… », « n élément(s) à envoyer », « Hors ligne — vos saisies sont conservées » avec tonalité (vert/bleu/orange/orange-rouge selon gravité : hors ligne = orange, erreur = rouge) + texte + icône ; placé dans la barre du haut.
- Menu : **mêmes entrées, mêmes chemins, mêmes droits** qu'aujourd'hui (liste de `menuItems` inchangée) ; regroupées sous des intertitres (ex. « Activité » : rendez-vous, dossiers patients, hospitalisations, rotations ; « Médical » : dossier médical, prescriptions, résultats d'examens ; « Suivi » : tableau de bord médecins, échecs de synchronisation avec son badge) ; **libellés toujours visibles** (tiroir sous `md` ouvert par un bouton menu, pas d'icônes seules) ; page active marquée (trait + fond) ; entête avec logo/nom de la structure comme aujourd'hui (logo résolu par `resolveAssetUrl`). Barre du haut : message de bienvenue, date, `ConnectionStatus`, langue FR/EN, cloche (`NotificationBell` inchangée), compte, déconnexion (bouton discret mais visible). Conteneur `.app-refonte` (taille de texte de base si Task 1 l'a limitée à ce conteneur).

- [ ] **Step 1: Tests** : `connectionStatus.test.mjs` — tableau de cas d'états (connecté sans file → online ; connecté avec envoi → syncing ; connecté avec file non vide → pending avec le nombre ; non connecté → offline ; erreur → error ; entrées manquantes/null → offline), priorité entre états, pluriel du libellé (1 / n) ; test de parité de clés `medicalShell.*`.
- [ ] **Step 2: Lancer** `node --test ah2-admin-web/tests/connectionStatus.test.mjs` — attendu : échec.
- [ ] **Step 3: Implémenter** utilitaire, composable, composant, nouveau gabarit ; **ne pas modifier** la logique d'authentification, de langue, de déconnexion ni le comptage de quarantaine ; documenter les noms d'API PowerSync réellement utilisés.
- [ ] **Step 4: Vérifier** tests node + `npx vite build` (dernier). Rapport : liste « avant/après » des éléments de la barre et du menu (aucun perdu), classes à regarder à 360/768/1280 px.

---

### Task 4: Page de connexion

**Files:**
- Modify: `ah2-admin-web/src/views/LoginView.vue`
- Modify: `ah2-admin-web/src/i18n.js` (clés `loginPage.*` seulement si de nouveaux textes sont ajoutés : mention « Accès sécurisé · Données médicales protégées », sous-titre)
- Create (si utile) : `ah2-admin-web/tests/loginViewContract.test.mjs`

**Interfaces:**
- Consumes (Tasks 1-2) : jetons, `AppButton`, `FormField`. **Inchangés** : appels du store d'authentification, gestion d'erreur et limitation de débit, `getPostLoginPath`, lien « mot de passe oublié », sélecteur de langue s'il existe.
- Produces : page de connexion en deux zones (volet de marque bleu nuit/teal avec logo, nom du centre et phrase d'accueil ; formulaire à droite) **sans photo** (variante légère) ; sous `md`, une seule colonne avec le logo en haut ; champs avec libellés, bouton principal pleine largeur, affichage du mot de passe, message d'erreur clair (rouge, texte + icône), état de chargement ; mention de sécurité sous le bouton. Aucun asset > 100 Ko ajouté (le logo existant est servi par `resolveAssetUrl`/`structureInfo` comme aujourd'hui, avec repli sur les initiales).

- [ ] **Step 1: Test de contrat** : un test node qui lit `LoginView.vue` et vérifie que les appels (`authStore.login`, `getPostLoginPath`, route de mot de passe oublié) et les clés i18n d'erreur utilisées avant la refonte sont toujours présents (liste figée dans le test), et que les nouvelles clés existent en FR+EN.
- [ ] **Step 2: Lancer** `node --test ah2-admin-web/tests/loginViewContract.test.mjs` — attendu : échec (nouvelles clés/structure absentes) puis PASS après implémentation.
- [ ] **Step 3: Implémenter** le gabarit ; ne pas toucher au script hors imports/classes ; vérifier le focus au chargement et la touche Entrée.
- [ ] **Step 4: Vérifier** tests node + `npx vite build` (dernier) ; relever la taille du chunk de la page de connexion avant/après dans le rapport.

---

### Task 5: Tableau de bord médecin / infirmière orienté tâches

**Files:**
- Modify: `ah2-admin-web/src/views/modules/doctors/DoctorKpiView.vue` (+ composants enfants éventuels de cet écran)
- Create (si nécessaire) : `ah2-admin-web/src/utils/doctorDashboardLayout.js`, `ah2-admin-web/tests/doctorDashboardLayout.test.mjs`
- Modify: `ah2-admin-web/src/i18n.js` (clés `doctorKpi.*` ajoutées seulement)

**Interfaces:**
- Consumes (Tasks 1-3) : composants `ui/`, données **déjà fournies** par `/doctor-dashboard/kpi`, `/doctors` et les stores existants ; règle d'affichage déjà en place : l'infirmière ne voit pas les cartes « total des rendez-vous », « patients distincts », « prescriptions », ni le panneau « par statut », ni le bouton de prise en charge.
- Produces : écran dont l'ordre est **« à faire d'abord »** : (1) file « patients à prendre en charge » (file de triage en attente de revue, avec ancienneté et gravité si présentes dans les données, bouton « Prendre en charge » réservé au médecin) ; (2) rendez-vous du jour et hospitalisations en cours / alertes d'aggravation **seulement si ces données sont déjà disponibles côté client pour ce rôle** (sinon lien vers l'écran concerné, sans nouvelle route) ; (3) statistiques de période en bas (cartes `AppCard`), tonalités selon la règle de couleur ; filtres de période conservés ; états vides aimables avec une phrase d'aide ; erreurs de chargement avec « Réessayer ». `utils/doctorDashboardLayout.js` (pure) décide quels blocs afficher selon le rôle (`medecin`/`nurse`) et selon les données disponibles — **testé**.
- Aucun nouveau calcul, aucune nouvelle route, aucune donnée inventée (pas de « vs mois dernier », pas de pourcentages fictifs).

- [ ] **Step 1: Tests** : `doctorDashboardLayout.test.mjs` — blocs affichés pour médecin et infirmière (aucune carte « médecin assigné » pour l'infirmière, bouton de prise en charge seulement pour le médecin), file vide → état vide, absence de données → blocs masqués sans erreur ; parité des clés ajoutées.
- [ ] **Step 2: Lancer** le test — attendu : échec.
- [ ] **Step 3: Implémenter** ; conserver exactement les appels réseau et la logique de prise en charge (`claim`), de rafraîchissement et de filtre ; rapport : tableau « élément avant → élément après » (rien de perdu).
- [ ] **Step 4: Vérifier** tests node + `npx vite build` (dernier).

---

### Task 6: Rendez-vous

**Files:**
- Modify: `ah2-admin-web/src/views/modules/appointments/AppointmentsList.vue`, `ah2-admin-web/src/components/appointments/{AppointmentsCalendar,AppointmentDayPanel,AppointmentModal,StatusBadge}.vue`
- Modify: `ah2-admin-web/src/i18n.js` (ajouts de clés seulement)

**Interfaces:**
- Consumes (Tasks 1-2) : `PageHeader`, `AppCard`, `AppButton`, `FormField`, `FormSection`, `ResponsiveTable`, `StatusBadge` (`ui/`), `EmptyState`. **Props, événements et appels de stores/services inchangés** (y compris l'assignation du médecin et la file de triage).
- Produces : écran rendez-vous (liste/calendrier/panneau du jour) restylé : titre + actions, calendrier lisible (jour courant marqué, jours avec rendez-vous), statuts par `StatusBadge` avec tonalités (urgent = rouge seulement si la donnée existe), formulaire de rendez-vous groupé en sections avec aide/erreurs claires, tableau → cartes sous `lg`.

- [ ] **Step 1: Test de contrat** : test node qui liste les clés i18n et les événements/props utilisés par les composants avant la refonte (liste figée) et vérifie qu'ils sont toujours présents après ; parité des clés ajoutées.
- [ ] **Step 2: Lancer** — attendu : échec là où des clés/structures sont nouvelles ; baseline verte avant modification des composants.
- [ ] **Step 3: Implémenter** ; rapport : tableau « actions et boutons avant → après » (rien de perdu), changements de script (idéalement imports seulement).
- [ ] **Step 4: Vérifier** tests node + `npx vite build` (dernier).

---

### Task 7: Hospitalisations, rotations des infirmières et protocole de test d'utilisation

**Files:**
- Modify: `ah2-admin-web/src/views/modules/hospitalization/HospitalizationsList.vue`, `ah2-admin-web/src/components/hospitalization/HospitalizationCard.vue`, `ah2-admin-web/src/views/modules/nurseshift/NurseShiftsView.vue`, `ah2-admin-web/src/components/nurseshift/{NurseShiftCalendar,NurseShiftDayPanel}.vue`, `ah2-admin-web/src/i18n.js` (ajouts)
- Create: `docs/superpowers/usability-test-protocol-medical.md`

**Interfaces:**
- Consumes (Tasks 1-2) : composants `ui/`. **Inchangés** : alerte d'aggravation, sortie d'hospitalisation (motif obligatoire, lettre de sortie), droits de la chef infirmière et du calendrier de rotation, props/événements.
- Produces : écrans restylés sur le même principe (alerte d'aggravation en rouge avec texte + icône, motifs/états par `StatusBadge`, confirmation avant sortie conservée). Protocole de test d'utilisation (1 page) : **5 tâches types** à faire exécuter à 2-3 membres du personnel (ex. se connecter et trouver le tableau de bord ; prendre en charge un patient de la file ; créer un rendez-vous ; consulter l'état de connexion et dire s'il y a quelque chose à envoyer ; ouvrir la fiche d'un patient), grille d'observation (temps, hésitations, erreurs, remarques), consignes (ne pas aider, penser à voix haute), modèle de synthèse.

- [ ] **Step 1: Test de contrat** comme à la Tâche 6 (clés et événements figés avant/après).
- [ ] **Step 2: Lancer** — attendu : baseline verte puis PASS après.
- [ ] **Step 3: Implémenter** + rédiger le protocole ; rapport « avant → après ».
- [ ] **Step 4: Vérifier** tests node + `npx vite build` (dernier). **Point de contrôle : l'utilisateur vérifie les phases 1-2 dans le navigateur et fait le test d'utilisation avant la Tâche 8.**

---

### Task 8: Dossier médical et formulaire de consultation (panneau plein écran)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/medical-records/MedicalRecordsList.vue`, `ah2-admin-web/src/components/medical-records/MedicalRecordModal.vue`, `ah2-admin-web/src/components/consultations/ConsultationModal.vue`, `ah2-admin-web/src/components/patients/medical/{MedicalRecordTimeline,VitalsCard,MedicalHistory}.vue`, `ah2-admin-web/src/i18n.js` (ajouts)
- Create: `ah2-admin-web/src/components/ui/FullScreenPanel.vue`, `ah2-admin-web/tests/consultationFormContract.test.mjs`

**Interfaces:**
- Consumes (Tasks 1-2) : `FormSection`, `FormField`, `ActionBar`, `AppButton`, `ResponsiveTable`, `StatusBadge`. **Inchangés** : ouverture depuis les mêmes endroits, props/événements, appels aux stores (`medicalRecordStore`), règle de lecture seule des consultations passées (`consultationLock`, `is_editable`, messages « Consultation clôturée »), écriture hors ligne, validation existante des champs, calcul de l'IMC si présent.
- Produces : `FullScreenPanel` (panneau plein écran sur tablette/téléphone, grande fenêtre centrée sur PC ; fermeture par bouton et Échap ; focus piégé ; avertissement si fermeture avec saisie non enregistrée **si ce mécanisme existe déjà** — sinon ne pas l'ajouter) ; formulaire de consultation en **sections nommées repliables** (Motif, Signes vitaux, Antécédents/Allergies, Examen/Symptômes, Diagnostic/Traitement, Notes) avec libellés au-dessus, astérisque, aide sous les champs difficiles, **barre d'actions fixe** en bas (Enregistrer = bouton principal, Annuler discret), compteurs de caractères conservés, messages d'erreur clairs ; liste du dossier médical en `ResponsiveTable` (cartes sous `lg`), consultations passées marquées « Clôturée » par `StatusBadge` + message existant.

- [ ] **Step 1: Test de contrat** (`consultationFormContract.test.mjs`) : figer la liste des champs du formulaire (noms de champs envoyés au store), des événements et des clés de lecture seule ; le test échoue si un champ disparaît ou change de nom ; exécuter la baseline avant modification.
- [ ] **Step 2: Lancer** — baseline verte avant, PASS après ; tests existants `consultationLock*.test.mjs` verts.
- [ ] **Step 3: Implémenter** ; interdire toute modification de `medicalRecordStore.js`, `DossierConnector.js` et `consultationLock.js` ; rapport « champs avant → après », changements de script listés.
- [ ] **Step 4: Vérifier** tests node + `npx vite build` (dernier).

---

### Task 9: Prescriptions

**Files:**
- Modify: `ah2-admin-web/src/views/modules/prescriptions/PrescriptionsList.vue`, `ah2-admin-web/src/components/prescriptions/PrescriptionModal.vue`, `ah2-admin-web/src/components/patients/medical/PrescriptionList.vue`, `ah2-admin-web/src/i18n.js` (ajouts)

**Interfaces:**
- Consumes (Tasks 1-2, 8) : composants `ui/`, `FullScreenPanel` si utile. **Inchangés** : règle de lecture seule des prescriptions des consultations passées (`isPrescriptionEditable`, messages), rattachement à la consultation, droits médecin/infirmière, props/événements.
- Produces : liste en `ResponsiveTable`, état de chaque prescription par `StatusBadge`, formulaire en sections avec aide/erreurs, actions principales claires.

- [ ] **Step 1: Test de contrat** (clés/événements figés, baseline verte avant).
- [ ] **Step 2: Lancer** — PASS avant et après ; tests de lecture seule existants verts.
- [ ] **Step 3: Implémenter** ; rapport « avant → après ».
- [ ] **Step 4: Vérifier** tests node + `npx vite build` (dernier).

---

### Task 10: Dossiers patients (liste et fiche)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/patients/PatientList.vue`, `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue`, `ah2-admin-web/src/components/patients/{PatientHeader,PatientModal}.vue`, `ah2-admin-web/src/components/patients/labs/{LabResultTable,LabResultsList}.vue`, `ah2-admin-web/src/components/patients/medical/SpiritualTimeline.vue`, `ah2-admin-web/src/i18n.js` (ajouts)

**Interfaces:**
- Consumes (Tasks 1-2, 8) : composants `ui/`. **Inchangés** : cloisonnement par rôle (le médecin et l'infirmière ne voient que le clinique : aucune apparition de données toxico/spirituelles), recherche et pagination existantes, indicateurs « personnel »/« toxico » existants, onglets de la fiche, exports si présents, props/événements.
- Produces : liste patients en `ResponsiveTable` (cartes sous `lg`) avec recherche lisible ; fiche patient avec en-tête clair (identité, code, indicateurs), onglets lisibles (libellés complets), contenu en `AppCard`/`FormSection` ; formulaire patient (modale) en sections nommées avec libellés au-dessus et astérisques ; états vides utiles.

- [ ] **Step 1: Test de contrat** (clés/onglets/événements figés ; vérifier explicitement qu'aucun onglet toxico/spirituel n'est ajouté pour les rôles médicaux).
- [ ] **Step 2: Lancer** — baseline verte avant, PASS après.
- [ ] **Step 3: Implémenter** ; rapport « avant → après ».
- [ ] **Step 4: Vérifier** tests node + `npx vite build` (dernier).

---

### Task 11: Résultats d'examens (lecture), échecs de synchronisation et harmonisation des libellés

**Files:**
- Modify: `ah2-admin-web/src/views/modules/sync/SyncFailuresView.vue`, la vue des résultats d'examens du médical (`src/views/modules/labo/MedicalLabResults.vue`) et `ah2-admin-web/src/components/lab/ResultDetailModal.vue` **uniquement pour l'usage depuis `/medical`** (aucune régression sur le laboratoire : vérifier qui d'autre les utilise avant d'y toucher et, en cas d'usage partagé, créer une variante ou des classes conditionnelles au lieu de modifier), `ah2-admin-web/src/i18n.js`

**Interfaces:**
- Consumes (Tasks 1-2) : composants `ui/`. **Inchangés** : tout le comportement de quarantaine (patients, consultations et prescriptions refusées, bouton « Retirer »), lecture seule des résultats pour médecin/infirmière.
- Produces : vues restylées (tableaux → cartes sous `lg`, états vides aimables, tonalités). **Harmonisation des libellés « Dossier Médical » / « Dossiers Patients »** : proposer au rapport une liste des libellés incohérents du menu médical et ne les changer **qu'après validation de l'utilisateur** (sinon laisser tel quel).

- [ ] **Step 1: Test de contrat** (clés/événements figés, baseline verte avant).
- [ ] **Step 2: Lancer** — PASS avant et après ; tests de quarantaine existants verts.
- [ ] **Step 3: Implémenter** ; confirmer par `grep` l'usage des composants partagés avant toute modification.
- [ ] **Step 4: Vérifier** tests node + `npx vite build` (dernier).

---

### Task 12: Recette finale et documentation

**Files:**
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`
- Create: `ah2-admin-web/tests/refonteGuard.test.mjs`

**Interfaces:**
- Consumes : tous les éléments précédents.
- Produces : `refonteGuard.test.mjs` — garde-fous durables : (a) aucune vue du périmètre médical n'utilise de couleur de marque ou d'état en dur (recherche d'hexadécimaux et de classes `indigo-`, `emerald-`, `slate-` dans les fichiers refondus) ; (b) paires de contraste (rappel du test des jetons) ; (c) parité i18n ; (d) chaque fichier refondu importe au moins un composant `ui/` ou est listé comme exception justifiée ; (e) les fichiers interdits listés dans les Global Constraints n'ont pas été modifiés depuis la base (comparaison avec `git diff --name-only <base>` si git est disponible dans le test, sinon liste de contrôle manuelle dans le rapport). Section « Refonte UX médicale » dans le suivi : ce qui a été livré, les décisions (couleurs, menu, composants), la **checklist à vérifier par l'utilisateur** par écran et par largeur (360/768/1280 px) avec les points précis tirés des rapports de tâches, les résiduels, le protocole de test d'utilisation et ce qu'il reste à migrer (autres espaces), la mise à jour de la mémoire du projet.

- [ ] **Step 1: Test** : écrire `refonteGuard.test.mjs` et le voir échouer sur un fichier volontairement non conforme ou sur une exception non listée, puis corriger.
- [ ] **Step 2: Lancer** `node --test ah2-admin-web/tests/*.test.mjs` puis `cd ah2-admin-web && npx vite build` (dernier) — attendu : PASS.
- [ ] **Step 3: Rédiger** la section du suivi et la checklist.
