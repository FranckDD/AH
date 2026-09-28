# Chantier 3, sous-projet 2 — Fenêtre secrétariat

**Date :** 2026-09-13
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** deuxième sous-projet du chantier 3 (portage web), après la fenêtre médicale (medecin+nurse, terminée — voir `docs/superpowers/SUIVI-AVANCEMENT.md`, section "Chantier 3, sous-projet 1"). Même méthode, même contrainte de non-commit tant que l'utilisateur n'a pas repris la main sur son arbre de travail.

## Contexte

Le rôle `secretaire` **existe déjà côté backend** (`api_backend/backend_app/security/role_map.py:10,29`) et est déjà autorisé sur plusieurs jeux d'endpoints (`/cs/*`, `/pharmacy/*`, `/caisse/*` — vérifié par lecture directe des `dependencies=[Depends(role_required(...))]` de chaque routeur). Mais il n'existe **aucun accès web pour ce rôle** : ni dans la constante `ROLES` de `ah2-admin-web/src/router/index.js`, ni dans la logique de redirection post-login, ni dans aucun shell.

### Rupture méthodologique actée avant ce sous-projet

Le desktop (`view_pyqt6/`) n'est **plus** considéré comme référence de portée pour ce portage (décision utilisateur explicite, 2026-09-13, pendant le cadrage de l'Étape 4 du sous-projet précédent — voir `SUIVI-AVANCEMENT.md`). Le code desktop (`view_pyqt6/secretaire/`) a été lu pour ce document, mais uniquement comme matériau d'inspiration et comme preuve empirique de ce que le backend expose réellement (ses appels HTTP y sont visibles) — jamais comme définition du périmètre. Chaque affirmation ci-dessous a été vérifiée directement dans le code backend actuel (routers FastAPI, schémas Pydantic), pas supposée depuis le desktop.

### État réel de chaque section (vérifié, pas deviné)

Le desktop (`view_pyqt6/secretaire/secretaire_dashboard.py`) organise la fenêtre secrétariat en 5 sections : Dashboard, Patients, Consultations (spirituelles), Stock, Caisse.

| Section | État web actuel | Backend |
|---|---|---|
| **Patients** | Couverture complète déjà existante : `PatientList.vue` + `PatientDetailView.vue` (déjà utilisés par `admin`/`ToxicoManager`, et depuis l'Étape 4 du sous-projet précédent par `medecin`/`nurse`). Aucune logique de rôle codée en dur dans ces deux fichiers. | `api_backend/backend_app/routes/patients/patients_endpoints.py` — déjà autorisé pour `secretaire` (vérifié) |
| **Stock** | Couverture complète déjà existante, CRUD entier : `ah2-admin-web/src/views/modules/stock/StockList.vue` + `ah2-admin-web/src/components/stock/ProductModal.vue`, montés sous `/dashboard/stock`, rôles actuels `[ADMIN, TOXICO_MANAGER, ASSISTANT]`. Identifiant : `medication_id` (`PharmacyResponse.medication_id`, `pharmacy_schemas.py:30`). | `api_backend/backend_app/routes/pharmacy/pharmacy_endpoints.py` — `dependencies=[Depends(role_required("secretaire","admin","Assistant","ToxicoManager"))]` (ligne 23) : **déjà autorisé pour `secretaire`**, aucun changement backend requis |
| **Caisse** | Couverture complète déjà existante, sous le nom web "Finance" : `ah2-admin-web/src/views/modules/finance/FinancialList.vue` + `ah2-admin-web/src/components/finance/FinanceModal.vue`, montés sous `/dashboard/finance`, rôle actuel `[ADMIN]` seulement. Identifiant : `transaction_id`. | `api_backend/backend_app/routes/caisse/caisse_endpoints.py` — `dependencies=[Depends(role_required("secretaire", "admin"))]` (ligne 34) : **déjà autorisé pour `secretaire`**, aucun changement backend requis |
| **Consultation Spirituelle** | **N'existe pas du tout côté web.** Un seul point de contact existant : `patientDossierStore.js` lit `spiritualHistory`/`isSpiritual` en lecture seule dans l'onglet dossier patient (pas un module CRUD). | `api_backend/backend_app/routes/cs/cs_endpoint.py`, prefix `/cs`, `dependencies=[Depends(role_required("secretaire", "admin", "medecin", "nurse", "SpiritualCounsellor"))]` — CRUD complet déjà en place (voir "Module Consultation Spirituelle" ci-dessous). Identifiant : `consultation_id` |
| **Dashboard d'accueil** | N'existe pas côté web. Choix explicite de l'utilisateur (2026-09-13) de le construire plutôt que de rediriger directement vers la première section, contrairement à la fenêtre médicale. | Détaillé ci-dessous — la quasi-totalité des KPIs a un endpoint réel déjà en service |

### Identifiants — piège déjà rencontré 3 fois dans ce chantier

Chaque module de ce sous-projet a son propre nom de champ identifiant, comme pour la fenêtre médicale (`id`/`prescription_id`/`record_id`) : **Patients = `patient_id`**, **Stock = `medication_id`**, **Caisse = `transaction_id`**, **Consultation Spirituelle = `consultation_id`**. Ne jamais supposer qu'un nom générique (`id`) fonctionne pour un module donné sans vérifier son schéma Pydantic.

## Module Consultation Spirituelle — inventaire backend complet (déjà vérifié)

`api_backend/backend_app/routes/cs/cs_endpoint.py` + `schemas_cs.py` :

- `GET /cs/prayer-book-types` → `[{"type_code": str, "label": str}, ...]` (liste de référence, pas de pagination)
- `GET /cs/` (`page`, `per_page`, `search`) → `List[ConsultationResponse]` — **pagination en mémoire côté endpoint** (`all_raw[start:end]`), aucun champ `total`/`total_pages` renvoyé. Le plan devra prévoir un pattern de pagination "page suivante désactivée si la page reçue est plus courte que `per_page`", pas un composant de pagination classique à compteur total.
- `GET /cs/patient/{patient_id}` → historique brut pour un patient
- `GET /cs/last/{patient_id}` → dernière consultation ou `null`
- `GET /cs/patient/{patient_id}/history` → historique trié (utilisé par le dossier patient existant)
- `GET /cs/{cs_id}` → une consultation
- `POST /cs/` (`ConsultationCreate`) → 201
- `PUT /cs/{cs_id}` (`ConsultationUpdate`)
- `DELETE /cs/{cs_id}` → 204

Champs (`ConsultationBase`) : `patient_id` (obligatoire à la création), `type_consultation` (obligatoire à la création, `max_length=50` côté schéma, mais **en pratique deux valeurs seulement** — voir ci-dessous), `presc_generic` (liste de chaînes), `presc_med_spirituel` (liste de chaînes), `mp_type`, `psaume`, `notes`, `fr_registered_at`, `fr_appointment_at`, `fr_amount_paid` (`Decimal`), `fr_observation`, `consultation_date`. Réponse (`ConsultationResponse`) ajoute `consultation_id`, `created_by`, `created_by_name`.

**`type_consultation` a exactement deux valeurs utilisées en pratique, et détermine quels champs s'affichent** — vérifié dans le formulaire desktop (`view_pyqt6/secretaire/cs_form.py:118`, `self.combo_type.addItems(["Spiritual", "FamilyRestoration"])`) ; le schéma backend ne les impose pas via un enum, mais aucune troisième valeur n'a été trouvée en usage réel :
- **`"Spiritual"`** → affiche `mp_type` (type de livre de prière, select alimenté par `GET /cs/prayer-book-types` — `mp_type` stocke le `type_code` choisi) et `psaume` (champ texte libre, ex. "23").
- **`"FamilyRestoration"`** → affiche les champs préfixés `fr_*` (`fr_registered_at`, `fr_appointment_at`, `fr_amount_paid`, `fr_observation`) — le préfixe `fr_` correspond à ce type, pas à "français". `mp_type`/`psaume` n'ont pas de sens pour ce type.

Le formulaire (`ConsultationModal.vue`) doit donc afficher un select à 2 options pour `type_consultation`, avec une section de champs conditionnelle selon la valeur choisie (comme le formulaire desktop, qui masque/affiche des groupes de champs sur `currentIndexChanged`) — pas un formulaire plat avec tous les champs visibles en permanence.

`presc_generic`/`presc_med_spirituel` sont des tableaux de chaînes libres (pas de table de référence identifiée pour leur contenu — contrairement à `prayer-book-types` qui, lui, a une vraie table). Le plan devra les traiter comme des champs texte multi-valeurs simples (ex. saisie séparée par virgules ou petite liste éditable), pas comme des selects liés à une table de référence.

## Dashboard d'accueil — inventaire des KPIs (chaque endpoint vérifié individuellement, pas supposé depuis le desktop)

| Carte (inspirée du widget desktop) | Endpoint réel vérifié | Statut |
|---|---|---|
| Total encaissé (période) | `GET /caisse/total_payments` (déjà câblé : `FinanceGateway.getIncomeTotal`) | ✅ Existe, réutilisable tel quel |
| Total retraits (période) | `GET /retrait/total` (déjà câblé : `FinanceGateway.getExpenseTotal`) | ✅ Existe, réutilisable tel quel |
| Solde net | Calculé client (`income - withdrawals`), comme `DashboardOverview.vue` | ✅ Pattern déjà établi |
| Reste à recouvrer | `GET /caisse/total_remaining_due` (déjà câblé : `FinanceGateway.getDebtTotal`) | ✅ Existe, réutilisable tel quel |
| Stock critique | `GET /pharmacy/kpi/critical_stock_count` → `{"stock_alerts_count": int}` | ✅ Existe, pas encore câblé côté web — nouveau, mais trivial |
| Péremptions proches | `GET /pharmacy/kpi/expiring_product_count?days=30` → `{"expiring_alerts_count": int}` | ✅ Existe, pas encore câblé côté web — nouveau, mais trivial |
| Table alertes stock | `GET /pharmacy/alerts/critical` → `List[PharmacyResponse]` | ✅ Existe |
| Table transactions impayées | `GET /caisse/dashboard/caisse/unpaid` | ✅ Existe (déjà référencé par `FinanceGateway.getDashboardCaisseKpis` pour la variante "kpis") |
| **Nouveaux patients (période)** | Aucun endpoint fiable trouvé. Le desktop lui-même (`dashboard_home.py:577-588`) avale silencieusement une erreur 404 sur cet appel et affiche `"0"` en repli — preuve que cet indicateur est déjà cassé côté desktop, pas seulement absent côté web. | ❌ N'existe pas — **remplacé** par "Consultations spirituelles (période)" = `len(GET /cs/?page=1&per_page=200)` ou équivalent, cohérent avec le nouveau module de ce sous-projet plutôt qu'un chiffre garanti à zéro |

Toutes les cartes Caisse réutilisent `FinanceGateway.js` **sans modification** — aucun nouveau code de ce côté. Seules 2 cartes stock + 1 carte consultations sont du code réellement nouveau.

## Portée

Construire `SecretaireLayout.vue`, un shell de dashboard indépendant de `MainLayout.vue`, pour `secretaire`, suivant exactement le même patron architectural que `MedicalLayout.vue` (chantier 3, sous-projet 1) :

- `ROLES.SECRETAIRE = 'secretaire'` ajouté à la constante `ROLES` de `router/index.js`.
- Nouvelle branche de routes `/secretariat/...`, `meta.roles: ['secretaire']` sur chaque route enfant (pas d'accès admin — l'admin a déjà ses propres routes `/dashboard/patients`, `/dashboard/stock`, `/dashboard/finance` vers les mêmes composants ; ajouter `admin` ici serait redondant, pas un accès supplémentaire).
- Logique de redirection post-login à étendre (même fichier/store que pour `medecin`/`nurse`) : un utilisateur `secretaire` doit atterrir sur `/secretariat/`, jamais sur `/dashboard/overview`.
- Un store Pinia + gateway par module suivant la convention déjà établie (`doctorKpiStore.js`/`DoctorKpiGateway.js` pour un exemple récent) — sauf pour Patients/Stock/Caisse où les stores existants (`patientStore`? à vérifier son nom exact en début de plan, `stockStore.js`, `financialStore.js`) sont réutilisés tels quels, sans duplication.

### Séquence d'implémentation (chaque étape finie avant la suivante)

1. **Shell + Patients** — `SecretaireLayout.vue`, rôle `SECRETAIRE`, routes `/secretariat/patients` + `/secretariat/patients/:id` réutilisant `PatientList.vue`/`PatientDetailView.vue` (même montage que l'Étape 4 de la fenêtre médicale). Redirection post-login `secretaire` → `/secretariat/patients` (page d'atterrissage temporaire jusqu'à l'étape 5, où elle devient `/secretariat/` → dashboard d'accueil).
2. **Stock** — route `/secretariat/stock` réutilisant `StockList.vue`/`ProductModal.vue` tels quels. Extension du `meta.roles` de la route `/dashboard/stock` existante non nécessaire (routes indépendantes) ; vérifier qu'aucune logique de rôle codée en dur dans `StockList.vue`/`ProductModal.vue`/`stockStore.js` ne bloque `secretaire` côté frontend (le backend l'autorise déjà).
3. **Caisse** — route `/secretariat/caisse` réutilisant `FinancialList.vue`/`FinanceModal.vue` tels quels. Même vérification de logique de rôle codée en dur côté frontend.
4. **Consultation Spirituelle** — nouveau module complet (CRUD), premier module 100% neuf de ce sous-projet : `ConsultationSpirituelleGateway.js`, `consultationSpirituelleStore.js`, `ConsultationModal.vue` (création/édition — recherche patient par code, comme `usePatientLookup.js` déjà extrait au sous-projet précédent, réutilisable ici sans le retoucher), `ConsultationsList.vue` (recherche/pagination "page suivante désactivée si page courte", pas de compteur total). Route `/secretariat/consultations`.
5. **Dashboard d'accueil** — page d'accueil du shell (`SecretariatHomeView.vue` ou nom équivalent tranché en plan), route `/secretariat/` (racine, plus de redirection automatique vers Patients — décision de l'étape 1 remplacée ici). KPIs listés ci-dessus : 4 cartes Caisse (réutilisation pure de `FinanceGateway.js`), 2 cartes + 1 table Stock (nouveau, trivial), 1 carte Consultations (réutilise le gateway de l'étape 4).

## Architecture du shell

- `ah2-admin-web/src/components/layout/SecretaireLayout.vue`, même structure que `MedicalLayout.vue` (sidebar, `menuItems` local non filtré par rôle puisque ce shell n'est jamais chargé par un autre rôle).
- 5 entrées de navigation : Accueil, Patients, Consultations, Stock, Caisse.
- `router/index.js` : nouvelle route parente `/secretariat`, enfants `''` (redirect vers la racine du dashboard d'accueil), `patients`, `patients/:id`, `stock`, `caisse`, `consultations`.
- i18n : nouveau bloc `secretariat.*` (titre du shell, libellés de nav) + nouveau bloc `consultations.*` (module CS complet — motif, champs du formulaire, table). `stock.*` et `finance.*` existent déjà et sont réutilisés sans changement.

## Vérification

- Chaque étape de la séquence (1 à 5) est fonctionnelle et testée manuellement (`npm run build` + test manuel navigateur) avant de passer à la suivante — même contrainte que le sous-projet précédent (`EACCES` Vite connu en local, non bloquant).
- Un utilisateur `secretaire` connecté atterrit sur `SecretaireLayout.vue`, jamais sur `MainLayout.vue`.
- Aucune régression sur les rôles déjà servis par `MainLayout.vue` (admin, toxico, labo, medecin/nurse via `/dashboard/*` — aucun de ces rôles n'est touché) ni sur la fenêtre médicale (`/medical/*`).
- Aucun commit tant que l'utilisateur n'a pas donné un accord explicite distinct — même contrainte globale que tout ce chantier.

## Hors périmètre

- Toute modification de `MainLayout.vue`, `MedicalLayout.vue`, ou des rôles qu'ils servent déjà.
- Correction de l'indicateur "Nouveaux Patients" du desktop (remplacé, pas réparé — voir tableau KPIs ci-dessus).
- Refonte des tables de référence `presc_generic`/`presc_med_spirituel` (traités comme champs texte libres, pas de nouvelle table de référence créée dans ce sous-projet).
- Chantier 4 (PowerSync/PWA) — après que fenêtre médicale ET fenêtre secrétariat soient converties.
