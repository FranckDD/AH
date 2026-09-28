# Imprimante thermique POS — ticket de caisse

**Date :** 2026-09-28
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** point 2 de la feuille de route post-notifications (voir `docs/superpowers/SUIVI-AVANCEMENT.md`, mémoire `project_roadmap_post_notifications.md`), enchaîné juste après le chantier "notifications + réduction caisse" (fermé le 2026-09-25) et l'écran "historique des demandes de réduction" (fermé le 2026-09-28) — le ticket doit pouvoir afficher le résultat d'une réduction validée.

## Contexte et objectif

Chaque facture caisse enregistrée par la secrétaire doit désormais aussi s'imprimer sous forme de ticket physique (format POS classique), avec un poste secrétariat unique et partagé en rotation entre plusieurs secrétaires (pattern déjà établi ailleurs sur ce projet, ex. chantier caisse hors-ligne). Quand une facture a été soumise à une demande de réduction (voir chantier notifications/réduction caisse), le ticket doit afficher clairement que la réduction a été validée, par qui, et à quel pourcentage — c'est la continuation directe de l'objectif anti-fraude du chantier précédent (remplacer un "okey" manuscrit falsifiable par une preuve imprimée dérivée d'une décision auditée en base).

Rien n'existe aujourd'hui côté impression sur ce projet — c'est un nouveau sous-système.

## Décisions actées en brainstorming

1. **Déclenchement — toujours automatique**, jamais manuel-seul, dès que la facture atteint le statut `active` :
   - Facture normale (pas de demande de réduction) : juste après `POST /caisse/` réussi.
   - Facture qui a suivi un cycle de réduction : quand la secrétaire est notifiée (`discount_decided`, boucle de polling 30s déjà en place) que SA facture est passée à `active`.
   - Un bouton "Réimprimer le ticket" existe dans `CaisseList.vue` dans tous les cas (bourrage papier, imprimante hors ligne au moment T, etc.).
   - **Correction actée en cours de brainstorming** : une première proposition envisageait une impression manuelle pour le cas "post-réduction", au motif que le client pourrait vouloir ajuster ses achats après avoir vu le résultat de la réduction. Analyse de risque : une fois une facture décidée (`active`), aucune édition d'articles n'est possible dans ce module — le seul levier si le client n'est pas satisfait est l'annulation existante (`cancel_transaction`, justification obligatoire, auditée, établie au chantier 7b). Rendre l'impression conditionnelle à cette étape aurait rouvert une variante de la fraude que le chantier précédent vient de fermer (encaisser, ne jamais imprimer, annuler ensuite sous un prétexte quelconque, sans preuve papier remise au patient pour contredire). **L'impression reste donc automatique dans tous les cas**, et le cas "client insatisfait" est géré exclusivement par le circuit d'annulation déjà existant, jamais par un saut d'impression.
2. **Périmètre** : factures caisse (vente/consultation) uniquement. Pas de ticket pour les retraits de caisse (`caisse_retrait`) — ce n'est pas une vente remise à un client, pas de besoin de ticket physique. Extensible plus tard si un besoin réel apparaît.
3. **Contenu du ticket** — voir section dédiée ci-dessous.
4. **Matériel imprimante** : aucun modèle physique décidé pour l'instant — conception générique ESC/POS (standard de fait des imprimantes thermiques POS), 80mm par défaut. Développement/test contre un émulateur d'imprimante POS virtuel pour Windows (en cours d'installation par l'utilisateur), qui s'installe comme une imprimante Windows classique — le pont doit donc supporter l'interface `Win32Raw` de `python-escpos` (nom d'imprimante Windows) en plus de l'interface `Usb` (vendor/product ID) pour la vraie imprimante plus tard, **choix du type de connexion configurable, jamais codé en dur**, pour basculer de l'un à l'autre sans toucher au code.

## Structure du ticket

**En-tête (centré) :**
- Logo monochrome (nouveau champ dédié, voir section Backend — distinct du logo couleur existant utilisé pour les factures PDF/exports, parce que le rendu thermique a besoin d'un fichier déjà optimisé/converti pour l'impression monochrome).
- Nom de l'établissement (texte).
- Adresse, téléphone, NIU/RCCM (déjà en base via `OrganizationConfig`, même source que `_pdf_header.html`).

**Infos transaction (alignées à gauche ou deux colonnes) :**
- Numéro de facture (`transaction_id`).
- Date et heure (`paid_at`).
- Nom du caissier (`created_by_name`/`user_name`).
- Patient (`patient_name`/`patient_label`).

**Corps du ticket (tableau en colonnes) :**
- Désignation de l'article (`item.note`/`item_name`, déjà résolu par `get_transaction_details_for_invoice()` — pas besoin de nouvelle jointure Pharmacie/Labo), tronquée si trop longue pour la largeur papier.
- Quantité, prix unitaire, total ligne. Format de ligne type : `2x Article A     10.00 / Total: 20.00`.

**Totaux (alignés à droite ou en colonnes) :**
- Total TTC (`amount`) — **pas de décomposition HT/TVA** : aucune notion de taxe n'existe dans ce système, décision explicite de ne pas en ajouter dans ce chantier.
- **Bloc réduction, uniquement si une `DiscountRequest` approuvée existe pour cette transaction** : "Réduction validée par {nom du manager} — {pourcentage}%", montant réduit, nouveau total.
- Montant payé (`advance_amount`) / Reste à payer (si > 0) — **pas de "montant reçu/monnaie rendue"** : ce système suit un modèle avance/solde avec paiement échelonné, pas un modèle caisse classique "espèces données → monnaie rendue" ; les libellés reprennent ceux déjà utilisés sur la facture PDF existante.
- Mode de paiement (`payment_method`).

**Pied de page (centré) :**
- Message de remerciement.
- Mention légale (`structure.legal_info`, si renseigné — réutilise le champ déjà en base).
- **Pas de code-barres/QR code** dans cette première version : rien n'existe aujourd'hui côté suivi/retour par QR, ajouterait une complexité de rendu bitmap sans usage clair identifié. YAGNI, à reconsidérer si un besoin réel apparaît.

## Architecture technique

### Backend (FastAPI, étendu)

- **Nouveau champ `OrganizationConfig.ticket_logo_url`** (migration Alembic) + endpoint d'upload miroir de celui du logo couleur existant (`controller/config_controller.py`/`config_endpoints.py`). `SystemConfig.vue` gagne un second champ d'upload dédié ("Logo ticket (monochrome)"), admin-configurable sans redéploiement — cohérent avec le reste du projet où tout ce qui est établissement est déjà pilotable depuis Configuration Système.
- **Nouvel endpoint `GET /caisse/{id}/ticket`** : réutilise `CaisseRepository.get_transaction_details_for_invoice()` tel quel (patient, caissier, items déjà résolus — aucune duplication de logique). Ajoute :
  - Le chemin du logo monochrome (`ticket_logo_url`, résolu comme `logo_path` dans `get_pdf_header_context()`).
  - Le bloc réduction : recherche la `DiscountRequest` liée à ce `transaction_id` avec `status == 'approved'` (s'il y en a une — au plus une par construction du workflow déjà en place), inclut `decision_percent` et le nom du manager décideur.
  - Renvoie un **JSON structuré** (pas du texte déjà formaté ESC/POS) — le rendu bitmap/mise en page reste la responsabilité du pont local, le backend ne connaît rien à ESC/POS.
- Rôle-gardé `secretaire` (seul rôle qui crée des factures caisse et a accès à un poste avec imprimante dans ce périmètre).

### Service pont local (nouveau sous-système, tourne sur le poste secrétariat)

- Service Python autonome, séparé du backend FastAPI principal (ne tourne PAS sur le même serveur que l'API si elle est un jour hébergée à distance — voir chantier 8 — le pont doit rester local à la machine où est branchée l'imprimante).
- Utilise `python-escpos` pour le rendu ESC/POS et l'envoi à l'imprimante.
- Packagé en exécutable via PyInstaller — outillage déjà utilisé sur ce projet pour l'application desktop (`view_pyqt6/`), pas une nouvelle dépendance de packaging à introduire.
- Écoute en HTTP sur `localhost` uniquement, port fixe configurable (défaut `9123` — libre parmi les ports déjà utilisés par ce projet en local : 8200 backend API, 5173 frontend Vite dev, 6379 Redis, 5432/5433/18080 PowerSync).
- **Connexion imprimante configurable** (fichier de config local du pont, pas codé en dur) : soit `Win32Raw` (nom d'imprimante Windows — utilisé pour l'émulateur de développement), soit `Usb` (vendor/product ID — pour la vraie imprimante physique plus tard). Un seul type actif à la fois.
- **Sécurité** : un jeton partagé, généré une fois et stocké côté `SystemConfig` (même écran que le logo ticket), est exigé sur chaque appel HTTP entrant. Nécessaire parce que n'importe quelle page ouverte dans un autre onglet du même navigateur peut, en théorie, adresser des requêtes à `http://localhost:PORT` — le jeton empêche qu'un site tiers déclenche une impression silencieuse.
- Endpoint unique côté pont : `POST /print` (JSON du ticket → mise en page ESC/POS → envoi à l'imprimante active selon la config).

### Déclenchement côté frontend

- Facture normale : dans le callback de succès de `handleCreateInvoice` (`CaisseList.vue`) après `POST /caisse/` — appelle `GET /caisse/{id}/ticket` puis `POST` au pont local.
- Facture post-réduction : dans `notificationStore.js` (boucle de polling déjà en place), quand une notification `discount_decided` avec `payload.status === 'approved'` arrive pour une facture de la secrétaire connectée — même séquence `GET /caisse/{id}/ticket` → pont local.
- Nouveau bouton "Réimprimer le ticket" dans `CaisseList.vue`, disponible pour toute facture `active` (même logique de fetch+print, à la demande).

### Gestion des échecs

Toujours best-effort — le pont injoignable, l'imprimante hors ligne ou à court de papier ne doivent jamais bloquer la création/l'enregistrement de la facture (déjà persistée en base indépendamment de l'impression). En cas d'échec : bandeau d'erreur explicite ("Ticket non imprimé — imprimante indisponible"), la facture reste normalement enregistrée, le bouton "Réimprimer" reste disponible pour réessayer plus tard.

### Test en développement

Contre l'émulateur d'imprimante POS virtuel pour Windows (installé par l'utilisateur) via l'interface `Win32Raw` — permet une vérification visuelle réelle de la mise en page (troncature des désignations, alignement des colonnes, rendu du logo) sans matériel physique, plus fiable qu'un simple mode dry-run textuel.

## Hors périmètre (explicitement exclu de ce chantier)

- TVA / décomposition HT-TTC.
- Montant reçu en espèces / monnaie rendue.
- Code-barres / QR code.
- Ticket pour les retraits de caisse (`caisse_retrait`).
- Impression multi-copies, ouverture de tiroir-caisse (cash drawer kick) — non demandés, à reconsidérer si un besoin réel apparaît.
