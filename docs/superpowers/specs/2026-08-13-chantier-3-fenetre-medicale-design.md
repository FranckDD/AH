# Chantier 3 — Fenêtre médicale (medecin + nurse)

**Date :** 2026-08-13
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** premier sous-projet du chantier 3 (portage web), choisi avant le chantier 4 (PowerSync + PWA) car la synchronisation hors-ligne n'a de sens que sur des pages qui existent déjà côté web.

## Contexte

Le client desktop PyQt6 organise l'application en **fenêtres indépendantes par rôle**, matérialisées par `view_pyqt6/factory/dashboard_factory.py` :

```python
def get_dashboard_class(role_name: str):
    return {
        'admin'      : DashboardAdminView,
        'medecin'    : DashboardView,
        'nurse'      : DashboardView,
        'secretaire' : SecretaireDashboardView
    }.get(role_name, DefaultDashboardView)
```

Chaque rôle reçoit une classe de fenêtre totalement distincte — pas un shell unique avec un menu filtré par rôle. `ah2-admin-web` aujourd'hui ne suit pas ce modèle : un seul `MainLayout.vue` avec un menu (`menuItems`) filtré par rôle sert tous les rôles déjà convertis (`admin`, `ToxicoManager`, `Psychologist`, `SpiritualCounsellor`, `Assistant`, `laborantin`). Décision explicite de l'utilisateur : **les rôles encore à convertir (médical, secrétariat) reçoivent leur propre shell de dashboard**, indépendant de `MainLayout.vue`, pour rester fidèle à l'architecture desktop. `MainLayout.vue` n'est pas touché — il continue de servir les rôles qui l'utilisent déjà.

**`medecin` et `nurse` partagent la même classe** (`DashboardView`, `view_pyqt6/dashboard_view_qt.py`) — un seul shell web les servira aussi.

### Contenu réel de la fenêtre médicale (extrait du code desktop, pas deviné)

`dashboard_view_qt.py` ligne 282 : `titles = ["Médecins", "Patients", "Rendez-vous", "Dossier Médical", "Prescription"]`. Vérifié section par section :

- **Rendez-vous** : `appointment_views/list_appointment.py` + `book_appoint_view.py` (import direct, ligne 31-32).
- **Patients** : `patient_view/patient_list.py` + `patient_form.py` (import conditionnel avec fallback `None`, ligne 18-22).
- **Dossier Médical** : `medical_record/mr_form_view.py` + `mr_list_view.py` (import direct, ligne 15-16).
- **Prescription** : `prescription_views/prescription_form_viewqt.py` + `prescription_list.py` — **import paresseux**, à l'intérieur des méthodes (`_show_prescription_form_view`/`_show_prescription_list_view`, lignes 782/832), pas visible dans les imports en tête de fichier — trouvé en cherchant `"prescription"` dans tout le fichier, pas seulement dans le bloc d'imports.
- **Médecins** : `show_doctors_dashboard` → tableau de bord/statistiques sur l'activité des médecins (`doctor_views/dashboard_doctor.py`). Pas de saisie transactionnelle — priorité la plus basse.

### État actuel côté web (avant ce chantier)

- **Rendez-vous** : inexistant avant ce soir. Une ébauche liste+filtres a été construite (`AppointmentsList.vue`, `appointmentStore.js`, `AppointmentGateway.js`, `StatusBadge.vue`, entrées i18n `appointments.*`) mais initialement montée à tort dans `MainLayout.vue`/`router/index.js` — retiré de ces deux fichiers (voir Registre, ce chantier réutilisera ces fichiers de contenu tels quels sous le nouveau shell).
- **Patients** : couverture partielle (`PatientList.vue`, `PatientDetailView.vue`), déjà utilisé par plusieurs rôles.
- **Dossier Médical** : lecture seule dans `PatientDetailView.vue` (onglet "MEDICAL", timeline). Bouton "Nouvelle consultation" présent mais **non câblé** (aucun `@click`).
- **Prescription** : lecture seule dans le même composant (onglet "PHARMA", liste simple). Aucune création/édition/suppression côté web.

### Découverte annexe (registre C4, déjà tranchée)

`/appointments/{id}/accept` n'a aucune sémantique réelle côté backend (écrit `status="pending"`, déjà la valeur par défaut — voir `docs/superpowers/SUIVI-AVANCEMENT.md`). Décision déjà actée : le bouton "Accepter" n'est **pas** reproduit côté web tant que ce ticket n'est pas tranché par le métier. Seuls "Refuser" (`/cancel`) et "Compléter" (`/complete`) sont exposés.

## Portée

Construire `MedicalLayout.vue`, un shell de dashboard indépendant de `MainLayout.vue`, pour `medecin`/`nurse`, avec sa propre navigation interne couvrant les 5 sections listées ci-dessus. Architecture REST classique (comme tous les modules web existants) — **pas** de préparation spécifique PowerSync à ce stade (décision utilisateur explicite : une couche séparée, chantier 4, pour ne pas complexifier ce chantier).

### Séquence d'implémentation (chaque étape finie avant la suivante)

1. **Rendez-vous** — finaliser ce qui a été commencé ce soir : remonter `AppointmentsList.vue`/`appointmentStore.js`/`AppointmentGateway.js`/`StatusBadge.vue` sous le nouveau shell, construire `AppointmentModal.vue` (création/édition, port de `book_appoint_view.py` : recherche patient par code, spécialité, date, créneau 30 min 08:00-18:30, raison).
2. **Prescription** — CRUD complet (le backend a été durci aujourd'hui, registre E, 9 bugs corrigés). Remplace l'affichage lecture-seule actuel dans le dossier patient par un vrai module.
3. **Dossier Médical** — câbler le bouton "Nouvelle consultation" existant, ajouter édition.
4. **Patients** — combler les écarts par rapport à ce que `patient_view/patient_list.py`/`patient_form.py` couvrent côté desktop (à vérifier précisément à ce moment-là, pas devinée maintenant).
5. **Médecins (KPI)** — tableau de bord de statistiques, priorité la plus basse, aucune donnée transactionnelle en jeu.

### Architecture du shell

- Nouveau composant `src/layouts/MedicalLayout.vue` (ou `src/components/layout/MedicalLayout.vue`, à trancher pendant le plan selon la convention exacte du dépôt — `MainLayout.vue` vit actuellement dans `components/layout/`), avec sa propre barre de navigation (5 entrées : Rendez-vous, Prescription, Dossier Médical, Patients, Médecins), sans réutiliser `menuItems`/`filteredMenu` de `MainLayout.vue`.
- Nouvelle branche de route (ex. `/medical/...` plutôt que `/dashboard/...`, à confirmer pendant le plan) avec `meta.roles: ['medecin', 'nurse']` (+ `admin` si l'utilisateur veut un accès de supervision — à trancher).
- Logique de redirection post-login (`LoginView.vue` ou le store `auth`) à ajuster : un utilisateur `medecin`/`nurse` doit atterrir sur le nouveau shell, pas sur `/dashboard/overview`.
- Un store Pinia + un gateway par module (même convention que `financialStore.js`/`FinanceGateway.js`, déjà appliquée pour Rendez-vous ce soir), REST classique.

## Vérification

- Chaque étape de la séquence (1 à 5) est fonctionnelle et testée manuellement (`npm run build` + test manuel navigateur, l'environnement de dev local a un problème `EACCES` connu sur Vite non lié à ce chantier) avant de passer à la suivante.
- Un utilisateur `medecin`/`nurse` connecté atterrit sur `MedicalLayout.vue`, jamais sur `MainLayout.vue`.
- Aucune régression sur les rôles déjà servis par `MainLayout.vue` (admin, toxico, labo, etc.) — ce chantier ne touche pas ce fichier.

## Hors périmètre

- La fenêtre secrétariat (`SecretaireDashboardView` : Patients, Consultation Spirituelle, Stock, Caisse) — sous-projet suivant, même méthode, après celui-ci.
- PowerSync / mode hors ligne (chantier 4) — couche séparée, après que cette fenêtre (et la fenêtre secrétariat) soient converties.
- Le ticket registre C4 (sémantique du statut `/accept`) — décision produit séparée, déjà actée comme non bloquante pour ce chantier.
- Toute modification de `MainLayout.vue` ou des rôles qu'il sert déjà.
