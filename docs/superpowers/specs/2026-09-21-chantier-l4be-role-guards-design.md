# Chantier L4b-e — Nettoyage des gardes de rôle : design

**Registre couvert :** `L4a`-`L4e` (`docs/superpowers/SUIVI-AVANCEMENT.md`), plus la dette technique explicitement parquée « à traiter avec L4b-e » par les chantiers 6, 7a et 7c.

**Ordre confirmé par l'utilisateur (2026-09-21) :** `7c` (fait) → `7b` (fait) → **ce chantier** → `7d`.

## 1. Constat

Le registre `L4` documente cinq écarts entre ce que l'interface montre et ce
que le serveur autorise réellement, plus un item de décision organisationnelle
(`L4a`). Trois chantiers récents (6, 7a, 7c) ont chacun découvert et parqué
un item supplémentaire relevant du même thème (gardes de rôle) plutôt que de
le traiter hors de leur périmètre déclaré. En creusant ce chantier avant
d'écrire la spec, la vérification du code réel a élargi ou réduit trois des
items d'origine :

- **`L4a`** — vérifié : `role_required()` (`auth_endpoints.py:194`) normalise
  déjà la casse et reconnaît déjà `"ToxicoManager"` comme alias canonique
  ailleurs (labo, toxico) — le trou est ponctuel à 3 routeurs, pas un
  problème de normalisation.
- **`L4e`** — élargi : le même défaut que `MainLayout.vue:221` (comparaison
  de rôle sans normalisation de casse, alors que `router/index.js` normalise
  déjà) existe à 6 autres endroits du frontend, découverts par grep exhaustif.
- **`L4d`** — réduit : la moitié « secrétaire sans accès Rendez-vous » est
  **retirée du périmètre** — décision utilisateur (2026-09-21) : les
  rendez-vous ne concernent que les patients médicaux, l'absence d'accès
  côté secrétariat est un comportement voulu, pas un bug. La moitié
  « médecin sans accès aux consultations spirituelles » reste dans le
  périmètre.

## 2. Périmètre

**Dans le périmètre :**
1. `L4a` — ajouter `"ToxicoManager"` aux 3 routeurs backend qui l'excluent
   encore (`/users`, `/audit`, `/patients`). Aucune création de compte : le
   rôle est déjà assignable de bout en bout via `UserModal.vue` ; l'utilisateur
   crée le compte réel lui-même après livraison.
2. `L4b` — `nurse` ajouté au `meta.roles` de la route `lab-history`.
3. `L4c` — `Assistant` retiré de l'accès à `SystemConfig` (menu **et** garde
   de route), côté frontend uniquement (le backend était déjà correct :
   `POST /config/structure` admin seul).
4. `L4d` (réduit) — nouvelle route/entrée de menu « Consultations
   spirituelles » pour `medecin` **et** `nurse` sous `/medical`, réutilisant
   `ConsultationsList.vue` déjà existant (le backend `/cs` les autorise
   déjà tous les deux).
5. `L4e` (élargi) — un point de vérité pour la comparaison de rôle
   (`authStore.hasRole(...)`, insensible à la casse), appliqué aux 7 endroits
   réels trouvés par grep, pas seulement la ligne citée par l'audit.
6. Dette parquée, confirmée dans le périmètre :
   - `assistant` restreint à lecture/recherche sur `/patients` (accès
     `PUT`/`DELETE` retiré, sans toucher aux routes `GET`).
   - Surcharge morte de la procédure stockée `create_medical_record`
     (19 anciens paramètres) supprimée par migration.
   - Bloc de code mort jumeau dans `PatientController.create_patient`
     (même motif que celui retiré de `update_patient` au chantier 7a)
     supprimé.

**Hors périmètre (décisions utilisateur, 2026-09-21) :**
- `L4a` : création du compte réel — l'utilisateur la fait lui-même.
- `L4d`, moitié secrétariat : accès Rendez-vous pour `secretaire` — retiré
  du périmètre, comportement voulu (les RDV ne concernent que les patients
  médicaux).

## 3. `L4a` — ToxicoManager reconnu par les 3 routes qui le refusaient

Ajouter `"ToxicoManager"` à `role_required(...)` sur :
- `api_backend/backend_app/routes/admin/users_endpoint.py` — `list_users`
  (actuellement `role_required("admin", "manager")`).
- `api_backend/backend_app/routes/audit/audit_endpoint.py` — dépendance de
  routeur (actuellement `role_required("admin", "manager")`).
- `api_backend/backend_app/routes/patients/patients_endpoints.py` —
  dépendance de routeur (actuellement `role_required("medecin", "nurse",
  "secretaire", "admin", "manager", "assistant")`).

`normalize_role_name()` gère déjà la casse — `"ToxicoManager"` (casse
mixte, comme stocké en base) fonctionne immédiatement, comme il le fait
déjà sur `lab_endpoints.py`/`toxico_endpoint.py`.

## 4. `L4b` — `nurse` sur `lab-history`

`ah2-admin-web/src/router/index.js:99` — `meta.roles` passe de
`['admin', 'laborantin', 'ToxicoManager', 'medecin']` à
`['admin', 'laborantin', 'ToxicoManager', 'medecin', 'nurse']`, alignant
sur `lab_endpoints.py:66,141` qui autorise déjà `nurse`.

## 5. `L4c` — Assistant retiré de SystemConfig

Deux retraits (sinon Assistant garde un accès direct par URL même sans
entrée de menu) :
- `MainLayout.vue` — l'item de menu `/dashboard/configuration` perd
  `ROLES.ASSISTANT` de son tableau `roles` (garde `ROLES.TOXICO_MANAGER`).
- `router/index.js` — le `meta.roles` de la route `configuration` perd
  `'Assistant'`.

## 6. `L4d` (réduit) — Consultations spirituelles pour medecin/nurse

Nouvelle route `/medical/consultations` (bloc `/medical` de
`router/index.js`, `roles: [ROLES.MEDECIN, ROLES.NURSE]`), réutilisant tel
quel le composant `ConsultationsList.vue` déjà utilisé par
`/secretariat/consultations`. Nouvelle entrée de menu dans
`MedicalLayout.vue::menuItems`, libellé `consultations.title` (clé i18n
déjà présente en fr/en, aucune nouvelle clé requise).

`ConsultationsList.vue` n'est pas modifié — vérifié qu'il ne contient
aucune hypothèse codée en dur sur le rôle `secretaire` qui empêcherait sa
réutilisation telle quelle (le filtrage d'accès à la création/modification
est déjà porté par le backend `/cs`, qui autorise déjà `medecin`/`nurse`
en écriture).

## 7. `L4e` (élargi) — un point de vérité pour la comparaison de rôle

Nouveau getter `hasRole` dans `ah2-admin-web/src/stores/auth.js` (store
Options API — `getters: { ... }`), retournant une fonction insensible à la
casse, même logique que `router/index.js:386-389` :

```javascript
hasRole(state) {
    return (allowedRoles) => {
        const role = (this.userRole || '').toLowerCase();
        return (allowedRoles || []).some((r) => (r || '').toLowerCase() === role);
    };
},
```

Remplace le motif `[...].includes(authStore.userRole)` / `item.roles.includes(userRole)`
partout où il apparaît réellement dans le code (vérifié par grep exhaustif,
pas seulement la ligne citée par l'audit) :

| Fichier | Usage actuel |
|---|---|
| `MainLayout.vue:221` | `item.roles.includes(userRole)` (menu filtré) |
| `ToxicoList.vue:318,323` | deux gardes UI (édition/suppression admission) |
| `PatientList.vue:190` (`canManagePatients`) | dette parquée chantier 7a |
| `LabConfig.vue:63` | garde de configuration labo |
| `LabLayout.vue:66` (`canConfigure`) | garde de configuration labo |
| `PatientDetailView.vue:184` (`canCreateConsultation`) | dette parquée chantier 7c |

Chaque site devient `authStore.hasRole([...])`, mêmes listes de rôles
qu'aujourd'hui (aucun élargissement ni restriction de périmètre — seule la
robustesse à la casse change).

## 8. Dette parquée

**`assistant` restreint à lecture/recherche sur `/patients`** — ajout d'une
dépendance `role_required("medecin", "nurse", "secretaire", "admin",
"manager")` (sans `"assistant"`) directement sur `@router.put("/{patient_id}")`
et `@router.delete("/{patient_id}")` dans `patients_endpoints.py`. La
composition des dépendances FastAPI est un ET logique (fait établi,
chantier 6) : la dépendance de routeur (large, avec `assistant`) continue
de s'appliquer à toutes les routes du fichier ; la nouvelle dépendance de
route, plus stricte, s'applique en plus sur `PUT`/`DELETE` uniquement — leur
intersection exclut `assistant` de l'écriture sans toucher à son accès en
lecture/recherche (`GET`), qui reste nécessaire au flux d'admission toxico.

**Surcharge morte de `create_medical_record` (19 paramètres)** — nouvelle
migration Alembic `DROP PROCEDURE public.create_medical_record(integer,
timestamp without time zone, character varying, character varying,
numeric, numeric, numeric, text, text, text, text, text, character
varying, text, character varying, integer, character varying, integer,
character varying)` (signature exacte à 19 paramètres, confirmée dans
`ci/schema_only.sql` avant écriture du plan). Aucun changement de modèle
ni de code applicatif : seul l'appelant à 20 paramètres
(`repositories/medical_repo.py::create`) existe, déjà vérifié par grep
exhaustif au chantier 7c.

**Bloc de code mort jumeau dans `create_patient`** — même motif que celui
retiré de `update_patient` au chantier 7a (rôles `app_admin`/`app_secretaire`/
`app_toxico_web` qui ne correspondent à aucun rôle réel du système) : supprimé.

## 9. Fichiers touchés (résumé)

**Backend :**
- `api_backend/backend_app/routes/admin/users_endpoint.py` (L4a)
- `api_backend/backend_app/routes/audit/audit_endpoint.py` (L4a)
- `api_backend/backend_app/routes/patients/patients_endpoints.py` (L4a,
  dette assistant)
- `controller/patient_controller.py` (dette : bloc mort `create_patient`)
- `alembic/versions/007_drop_medrec_19param_overload.py` (nouveau)
- `ci/schema_only.sql` (régénéré après application)

**Frontend :**
- `ah2-admin-web/src/router/index.js` (L4b, L4c, L4d)
- `ah2-admin-web/src/components/layout/MainLayout.vue` (L4c, L4e)
- `ah2-admin-web/src/components/layout/MedicalLayout.vue` (L4d)
- `ah2-admin-web/src/stores/auth.js` (nouveau getter `hasRole`, L4e)
- `ah2-admin-web/src/views/modules/toxico/ToxicoList.vue` (L4e)
- `ah2-admin-web/src/views/modules/patients/PatientList.vue` (L4e)
- `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue` (L4e)
- `ah2-admin-web/src/views/modules/labo/LabConfig.vue` (L4e)
- `ah2-admin-web/src/views/modules/labo/LabLayout.vue` (L4e)

**Tests :** `tests/test_patients.py` (garde `assistant`/PUT/DELETE),
`tests/test_users.py`/`tests/test_audit.py` (ToxicoManager reconnu),
nouveau test de migration si le projet en a la convention pour les
migrations précédentes (vérifié : 003/005/006 n'ont pas de test dédié,
seulement une vérification manuelle post-application — même traitement ici).

## 10. Rôles et accès

Aucun élargissement de périmètre au-delà de ce que les backends autorisent
déjà (L4b, L4d) ou de ce que la casse aurait dû laisser passer depuis le
début (L4a, L4e). Le seul retrait de droit est L4c (Assistant/SystemConfig,
décision utilisateur) et la dette assistant/patients (retrait de PUT/DELETE,
décision utilisateur) — les deux resserrent l'accès, n'en accordent aucun
de nouveau.

## 11. Erreurs et cas limites

- Migration 007 : `DROP PROCEDURE` sur une signature précise (surcharge
  ciblée par sa liste de types exacte) — ne touche pas la surcharge à 20
  paramètres réellement utilisée. Vérifiée par lecture de
  `ci/schema_only.sql` avant écriture du plan, pas supposée.
- `hasRole([])` (liste vide) renvoie `false` — même comportement que
  `[].includes(x)` aujourd'hui, pas de changement de sémantique.
- Un compte réellement `ToxicoManager` navigant vers `/dashboard/users` ou
  `/dashboard/logs` recevra désormais 200 au lieu de 403 — comportement
  voulu, seul un compte réel (créé par l'utilisateur après livraison) peut
  l'exercer.

## 12. Auto-review

- **Placeholders** : aucun — chaque item référence un fichier et une ligne
  réels, vérifiés dans le code actuel avant rédaction (contrats de rôle,
  routes existantes, clés i18n déjà présentes).
- **Cohérence interne** : section 8 (dette assistant/patients) dépend du
  fait établi de composition ET des dépendances FastAPI (chantier 6) —
  cohérent avec la façon dont `patients_endpoints.py` est déjà structuré
  aujourd'hui (une seule dépendance de routeur, aucune dépendance de route
  existante à ce jour).
- **Portée** : un seul chantier cohérent (thème unique : gardes de rôle),
  décomposé en items indépendants dans le plan à venir — pas de
  décomposition en sous-projets séparés nécessaire.
- **Ambiguïté** : la réduction du périmètre L4d (secrétariat/RDV retiré) et
  l'élargissement du périmètre L4e (7 sites, pas 1) sont documentés
  explicitement (sections 1-2) avec leur justification, pour éviter toute
  confusion avec la formulation d'origine du registre L4 dans
  `SUIVI-AVANCEMENT.md`.
