# Refonte UX — espace médical (médecin et infirmière) — conception (2026-10-22)

## Intention

L'interface a été construite en 2025 et paraît datée à son auteur. Le personnel médical du centre est **peu habitué au numérique** : une interface « belle » mais décorative leur nuirait. L'objectif est une interface **plus actuelle, plus calme et plus guidée**, qui réduit l'hésitation (« où cliquer ? », « est-ce enregistré ? ») sans toucher aux règles métier.

On commence par l'espace médical (rôles `medecin` et `nurse`, même interface, l'infirmière n'ayant pas accès à certaines fonctions du médecin). Les autres espaces (secrétariat, labo, toxico, stock, admin, caisse) suivront plus tard, en réutilisant le système de design posé ici.

Succès : une personne qui n'a jamais vu l'application sait, sur chaque écran, ce qui est urgent, quelle est la prochaine action, et si ses données sont enregistrées et synchronisées. Mesure : test d'utilisation avec 2 à 3 membres du personnel (protocole fourni, voir « Livrables »).

## Références visuelles

Dossier `Image_propos_test_ui/` (maquettes générées fournies par l'utilisateur). **On en retient le style, jamais le contenu** : aucune donnée, aucun bloc ni aucune fonctionnalité inventés (pas d'« Actions rapides », de « +12 % vs mois dernier », de fausses statistiques). Bases théoriques consultées : Refactoring UI, Laws of UX, Don't Make Me Think, Atomic Design, heuristiques de Nielsen.

## Décisions de l'utilisateur (ce qu'il a validé)

1. **Changement de couleur de marque accepté** : de l'ardoise grise actuelle vers un **bleu nuit + vert-teal** (proche du logo : globe bleu et vert), comme sur les maquettes.
2. Retenu des maquettes : hiérarchie claire (gros titre, sous-titre, cartes séparées) ; menu avec **icône + libellé** ; formulaires **groupés en sections nommées** avec libellés au-dessus des champs, astérisque sur les champs obligatoires, gros bouton principal et « Annuler » discret ; **états vides aimables** ; identité cohérente avec le logo ; **page de connexion accueillante** avec la mention « Données médicales protégées ».
3. Réserves acceptées, à appliquer : (a) tableau de bord médecin **orienté tâches** (file des patients à prendre en charge d'abord, statistiques ensuite) ; (b) **icônes seulement** dans le menu, sur les boutons d'action et pour les états — pas dans chaque champ ni sur chaque titre ; (c) **couleur = sens** : rouge pour l'urgent, orange pour l'attention, vert pour « fait/validé », bleu pour l'information ; **une seule couleur d'action principale** ; (d) texte de base **15 à 16 px**, contraste **WCAG AA**, zones tactiles **≥ 44 px** ; (e) formulaire de consultation en **page à sections repliables avec barre d'actions fixe**, la fenêtre modale restant pour les formulaires courts ; (f) **menu non replié par défaut** (libellés toujours visibles, repli possible mais jamais imposé sur tablette) ; (g) **images légères** (connexion du centre ≈ 7 Mbps) : page de connexion sans grosse photo obligatoire, ou photo compressée en format léger ; licence/propriété de toute photo à vérifier par l'utilisateur ; (h) **indicateur de connexion et de synchronisation** visible (« Connecté », « Hors ligne », « n éléments à envoyer ») car l'application fonctionne hors ligne ; (i) **aides intégrées** : phrase d'aide sous les champs difficiles, messages d'erreur en langage clair, confirmation avant toute action irréversible.
4. **Refusé** : recherche de patient globale dans la barre du haut. Ne pas la construire ni la laisser en maquette.
5. Méthode : application progressive, module par module ; test d'utilisation avec le personnel avant d'étendre au reste.
6. Mises à jour de dépendances : déjà faites (Tailwind 4, vue-router 5, pinia 3, vue-i18n 11).

## Périmètre — écrans du médical

Rendez-vous, prescriptions, dossier médical (consultations), dossiers patients (liste et fiche), tableau de bord médecin/infirmière (`/medical/doctors`), résultats d'examens (lecture), hospitalisations, rotations des infirmières, échecs de synchronisation, ainsi que le cadre commun (`MedicalLayout.vue` : menu, barre du haut, notifications) et les composants partagés (fenêtre modale, pagination, carte statistique, notifications/toasts). La page de connexion est reprise dans la phase 1 car c'est la première impression de tout le monde.

## Hors périmètre

- Recherche de patient globale (refusée) ; toute nouvelle fonctionnalité métier ; modification du backend ou des règles de droits ; contenu inventé ; refonte des autres espaces (secrétariat, labo, toxico, stock, caisse, admin) — ils gardent leur apparence actuelle mais **peuvent adopter les composants** ensuite ; mode sombre.
- Changer le vocabulaire métier ou l'organisation des menus (sauf libellés incohérents relevés : « Dossier Médical » / « Dossiers Patients » à harmoniser avec l'utilisateur).

## Anti-objectifs

Échec même si c'est « beau » : un écran où l'utilisateur ne sait plus où cliquer ; du texte gris clair illisible sur tablette en salle lumineuse ; des icônes partout qui noient l'information ; la couleur rouge utilisée pour autre chose que l'urgent ; une régression fonctionnelle ou de droits ; une interface qui n'affiche pas clairement l'état hors ligne ; une page de connexion lente sur la connexion du centre ; des écrans différents les uns des autres.

## Contraintes

- Tailwind 4 en configuration CSS (`@theme` dans `src/style.css`) ; **jetons de design** (couleurs, rayons, ombres, tailles de texte, espacements) définis une seule fois ; aucun hexadécimal en dur dans les vues.
- **Police embarquée localement** (application installable/hors ligne : pas de CDN) ; fichiers de police limités aux graisses utilisées.
- Tout texte visible en **FR et EN** (clés i18n avec test de parité) ; conserver les clés existantes quand le sens ne change pas.
- Adaptabilité : téléphone 360 px, tablette 768 px, PC 1280 px ; les tableaux deviennent des cartes empilées sous `md`.
- Accessibilité : contraste AA vérifié par un **test automatique des paires de couleurs des jetons** ; focus visible ; libellés associés aux champs ; états non portés par la seule couleur (texte ou icône en plus).
- Aucune régression : tests `node` existants verts, `vite build` sans avertissement nouveau, comportements métier inchangés (droits, hors ligne, règles de lecture seule des consultations passées, etc.).
- Les écrans sont revus un par un avec les contenus **réels** de l'application.

## Système de design (à définir dans le plan, valeurs exactes à fixer par le concepteur)

- Palette : bleu nuit (menu, fond de marque), vert-teal (action principale, marque), neutres froids, quatre couleurs d'état (danger, attention, succès, info) avec variantes claire/foncée ; chaque paire texte/fond validée AA.
- Typographie : une police sans empattement lisible (type Inter), échelle courte (titre de page, titre de section, texte, petit texte), texte de base 15–16 px, interlignage généreux.
- Formes : rayons 10 à 12 px sur les cartes, 8 px sur les champs et boutons ; ombres légères ; pas de dégradés décoratifs sauf, éventuellement, l'en-tête du menu.
- Composants partagés : bouton (principal, secondaire, danger, discret), carte, en-tête de page (titre + sous-titre + actions), badge d'état, état vide, tableau responsif (tableau ≥ lg, cartes en dessous), champ de formulaire (libellé, aide, erreur), section de formulaire repliable, barre d'actions fixe, fenêtre modale, notification, indicateur de connexion/synchronisation.
- Menu : sections nommées (ex. Activité / Suivi), page active marquée, libellés toujours visibles, badges de comptage (échecs de synchronisation) conservés.

## Ordre de réalisation (à détailler dans le plan)

1. **Fondations** : jetons, police locale, composants partagés, test de contraste, cadre `MedicalLayout` (menu, barre du haut, indicateur de connexion), page de connexion.
2. **Tableau de bord médecin/infirmière** orienté tâches, puis rendez-vous et hospitalisations.
3. **Dossier médical, prescriptions, dossiers patients (liste et fiche), rotations, résultats, échecs de synchronisation**, avec le formulaire de consultation en page à sections repliables.
4. **Livrables de validation** : protocole de test d'utilisation (1 page : 5 tâches types à faire exécuter à 2–3 membres du personnel, grille d'observation) et liste « à vérifier par vous » dans le suivi.

## Laissé au concepteur

Valeurs exactes des couleurs et des tailles (dans les contraintes ci-dessus) ; découpage exact des composants ; choix de la police ; organisation interne de chaque écran tant que les principes ci-dessus sont tenus ; icônes (jeu Heroicons déjà utilisé).

## Hypothèses du concepteur (à contester)

- L'indicateur de connexion/synchronisation s'appuie sur ce que PowerSync expose déjà (état connecté, opérations en attente) sans nouveau code serveur.
- Le menu garde les mêmes entrées et les mêmes droits par rôle ; seul l'habillage et le regroupement changent.
- Les libellés « Dossier Médical » et « Dossiers Patients » seront harmonisés après validation de l'utilisateur.
- La photo de la page de connexion est facultative : variante sans photo (couleur de marque + logo) livrée en premier.
- **Portée des jetons et composants (relecture du concepteur)** : les nouveaux jetons sont **ajoutés** dans `@theme` sous de nouveaux noms (`brand-*`, `nav-*`, `tone-*`) sans modifier les couleurs Tailwind par défaut, et les nouveaux composants vivent dans `src/components/ui/` ; les composants partagés existants (`Modal`, `Pagination`, `StatCard`, `ToastContainer`) et **tous les espaces hors médical gardent leur apparence** tant qu'ils ne migrent pas. Seuls `MedicalLayout.vue`, les écrans médicaux listés et la **page de connexion** (commune à tous les rôles, première impression) changent. Le logo, la cloche de notifications et le bandeau de notification sont partagés : ils ne changent pas de comportement.
- **File « patients à prendre en charge »** : construite **uniquement à partir des données et routes existantes** (file de triage en attente de prise en charge, rendez-vous du jour du médecin, hospitalisations en cours, alertes d'aggravation) — aucune nouvelle route ni logique serveur. L'infirmière voit la même file, sans le bouton de prise en charge (réservé au médecin) ni les chiffres calculés pour le médecin assigné.
- **Formulaire de consultation** : le composant et le flux d'ouverture actuels sont **conservés** (même route, même logique hors ligne, même règle de lecture seule des consultations passées) ; il passe en **panneau plein écran** avec sections repliables et barre d'actions fixe. Pas de nouvelle URL dans ce chantier.
- **Points de contrôle** : revue indépendante après chaque tâche, **test d'utilisation avec le personnel après la phase 2** (fondations + tableau de bord + rendez-vous/hospitalisations), avant la phase 3.
- **Règle de sécurité du chantier** : refonte **sans changement de comportement** — les balises `<script>` ne changent que pour importer les nouveaux composants ; toute modification de logique doit être signalée et justifiée.
