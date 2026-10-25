# Comptage physique du stock de la pharmacie : conception

Date : 2026-10-24. Statut : validee par l'utilisateur en discussion (fonctionnement et frequence d'un mois). Troisieme des quatre morceaux "Rapports" (ordre : 1 cloture de caisse, 3 sorties declarees, 2 comptage physique du stock, 4 Rapports et controle quotidien). L'utilisateur n'a pas de probleme avec le controle actuel : il demande de suivre la norme des comptages d'inventaire.

## Pourquoi

Un audit a montre des stocks manquants. Le systeme ne connait que le stock theorique (entrees moins ventes, avaries, ajustements) ; personne ne le compare regulierement a ce qui est reellement sur l'etagere, et rien ne dit quels produits n'ont jamais ete comptes. Les Rapports (morceau 4) devront pouvoir signaler les produits jamais ou trop rarement comptes et les ecarts.

## Ce qui est decide

- **Qui compte** : le `StockController` (verificateur du stock) ou l'`admin`. Le `promoteur` consulte seulement. Les autres roles n'ont aucun acces.
- **Comptage a l'aveugle** : l'ecran de comptage liste les produits sans aucune quantite du systeme. Le compteur saisit ce qu'il voit sur l'etagere, pour tous les produits ou une selection. A la validation, le systeme compare, fige le comptage et revele les ecarts. Un comptage valide ne se modifie plus.
- **Ecart** : chaque ecart non nul cree automatiquement une demande d'ajustement de type `correction` dans le circuit existant (`stock_adjustment_requests`). L'`admin` l'approuve ou la refuse comme aujourd'hui, et le stock ne change qu'a l'approbation (l'ajustement existant applique `quantite comptee - stock du systeme a la demande` au stock actuel, donc les ventes faites entre-temps ne sont pas ecrasees). Le demandeur est le compteur. La route existante de creation reste reservee a la secretaire et ne change pas.
- **Pas de refus a la validation** (decision de l'assistant, pour ne pas reveler les ecarts avant la validation) : le compteur peut joindre une observation facultative a chaque ligne ; sans observation, le motif de la demande est genere ("Ecart constate au comptage n. X : systeme S, compte C").
- **Ventes pendant le comptage** : le comptage a une heure de debut cote serveur ; a la validation, pour chaque ligne, le systeme enregistre le stock lu a cet instant et le nombre de mouvements de stock survenus depuis le debut, afin que le revelateur d'ecart signale "mouvements pendant le comptage" et qu'une vente ne passe pas pour une perte.
- **Frequence** : chaque produit devrait etre compte au moins une fois tous les **30 jours** (reglage modifiable par l'admin). L'ecran montre pour chaque produit la date du dernier comptage et un mot : "jamais compte", "en retard" ou "a jour". Pas de notification push dans ce morceau (decision de l'assistant : le controle quotidien du morceau 4 previent le promoteur et l'admin) ; un rappel visible a l'ouverture de l'ecran suffit.
- **Trace** : debut, validation, chaque ecart et chaque demande creee sont dans l'audit existant ; les admins recoivent la notification existante de demande d'ajustement.
- **Perimetre** : stock des produits de la pharmacie (table `pharmacy`). Hors perimetre : le stock du labo (comptage hebdomadaire qui lui est propre), les intrants de fabrication, les graphiques et rapports (morceau 4).

## Non-buts et anti-buts

Pas de recalage automatique du stock sans approbation de l'admin. Pas de modification d'un comptage valide. Un ecran qui montre le stock du systeme avant la validation est un defaut.

## A decider par le constructeur

Noms et colonnes des tables, forme exacte du statut de comptage, ergonomie de saisie rapide, selection de produits, ou mettre le reglage des 30 jours, libelles. Respecter les conventions du projet : roles par route, table des routes comparee dans les tests de role, aucune couleur brute, textes FR/EN sans tiret long ni points de suspension typographiques, garde-fou de perimetre.
