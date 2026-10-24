# Sorties declarees de la production (echantillons et autres) : conception

Date : 2026-10-24. Statut : validee par l'utilisateur en discussion (sans circuit d'approbation). Deuxieme des quatre morceaux "Rapports" decides le 2026-10-23 (ordre : 1 cloture de caisse, 3 sorties declarees, 2 comptage physique du stock, 4 Rapports et controle quotidien). Elle etend le module Fabrication (`specs/2026-10-23-fabrication-production-design.md`).

## Pourquoi

La production se fait chez le promoteur, hors du centre. Un echantillon donne a un partenaire sort des bouteilles bonnes AVANT l'envoi au stock du centre. Sans trace, ces bouteilles ressemblent a un manque inexplique dans le bilan du lot. Le promoteur veut seulement que le responsable de production enregistre le nombre d'echantillons (et toute autre sortie imprevue) sans ralentir la chaine : pas d'approbation, mais une trace complete et visible.

## Ce qui est decide

- Le `ProductionManager` declare une sortie sur un lot dont le resultat est saisi (statut `termine`) et qui n'est pas encore expedie.
- Motifs : `echantillon` ou `autre`. Ni don ni vente directe. Nombre de bouteilles entier > 0. Note obligatoire pour `autre` (situation imprevue), facultative pour `echantillon` (destinataire). Le total des sorties actives d'un lot ne depasse jamais ses bouteilles bonnes.
- **Aucune approbation** : la sortie prend effet des la declaration et ne bloque jamais l'expedition.
- Une sortie peut etre annulee, avec motif, tant que le lot n'est pas expedie. Elle reste dans l'historique (statut `annulee`) ; rien ne s'efface.
- A l'expedition, le stock envoye au centre = bouteilles bonnes moins sorties actives.
- Dans le bilan du lot, les sorties actives forment une categorie expliquee (par motif : "12 echantillons, 3 autres"), pas un manque.
- Trace : chaque declaration et chaque annulation garde auteur, heure, motif, note, et ecrit dans la trace d'audit existante.
- Visibilite : `ProductionManager` ecrit ; `promoteur` et `admin` lisent (fiche du lot et "Suivi et anomalies") ; tout autre role : 403. Pas de notification a chaque declaration (decision de l'assistant, pour ne pas faire de bruit) ; le controle quotidien du morceau 4 signalera les sorties `autre` ou inhabituelles. Les chiffres ne sortent pas du module `/fabrication`.

## Non-buts

Pas de circuit d'approbation. Pas de graphiques ni de rapports (morceau 4). Pas de sortie sur du stock deja envoye au centre (cela releve du stock et de ses avaries).

## A decider par le constructeur

Forme exacte de la table (par exemple `fab_batch_outputs`), nom des champs, migration, ou mettre la categorie dans le calcul du bilan et les anomalies existantes, libelles, ergonomie de la fiche du lot. Respecter les conventions du module : roles par route, route table comparee dans les tests de role, aucune couleur brute, textes FR/EN sans tiret long ni points de suspension typographiques, garde-fou de perimetre.
