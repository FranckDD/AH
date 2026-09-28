# _corbeille

Fichiers retirés de l'arborescence active parce que confirmés orphelins
(plus référencés par aucune route, aucun import, aucun test) au moment du
retrait — jamais supprimés directement, pour rester récupérables (`git`
ou simple déplacement inverse) si un usage caché était découvert plus tard.

Chaque entrée garde son chemin d'origine sous `_corbeille/`, pour pouvoir
la restaurer avec un simple `mv` inverse.

## Entrées

- `ah2-admin-web/src/views/modules/labo/LabValidation.vue` (retiré 2026-09-25,
  chantier 4 sous-projet 5) — écran de saisie labo legacy, remplacé en
  pratique par `LabTechnician.vue` (contrat de données différent : `exams`
  imbriqué au lieu d'un `details` plat, valeurs scalaires au lieu de
  `{valeur, flag, interpretation}`). Routé mais jamais réellement atteint
  avant son retrait (`/labo/validation/:id?` redirige maintenant vers
  `lab-technician`, voir `ah2-admin-web/src/router/index.js`) : son unique
  point d'entrée navigationnel (`LabDashboard.vue`) poussait vers cette
  route sans `id`, et son propre bouton « terminé » référençait un nom de
  route (`LabTechnician`, casse différente de `lab-technician`) qui n'a
  jamais existé. Découvert en lisant le code pendant une revue de tâche du
  chantier 4 sous-projet 5, pas signalé par l'utilisateur — voir
  `docs/superpowers/SUIVI-AVANCEMENT.md`, section « Chantier 4, sous-projet
  5 » pour le détail complet de l'investigation.
