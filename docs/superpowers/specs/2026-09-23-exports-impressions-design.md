# Exports et impressions (registre L3d) — Design

**Statut** : approuvé par l'utilisateur le 2026-09-23, prêt pour le plan d'implémentation.

## Contexte

Dernier point du groupe 3 de la dette technique observée par l'utilisateur en test réel (après groupes 1 et 2, déjà livrés). Le registre `L3d` (`SUIVI-AVANCEMENT.md`) listait à l'origine 4 manques : facture PDF, export patients (PDF/CSV), export dossiers médicaux (PDF/Excel), export consultations spirituelles. Vérification faite avant ce brainstorming : **la facture PDF caisse existe déjà** (chantier 7b, `GET /caisse/{id}/invoice/download`, bouton dans `CaisseList.vue`) — mais avec un défaut réel découvert pendant le cadrage (voir Section 1). Le périmètre réel de ce chantier est donc : le correctif de la facture caisse, plus les 3 exports réellement absents.

## Décisions actées pendant le brainstorming

1. **En-tête PDF dynamique obligatoire partout** (exigence explicite de l'utilisateur) : tout nouveau PDF, et la facture caisse existante, doivent utiliser les informations d'établissement (nom, adresse, contacts, logo) définies dans `SystemConfig.vue` — jamais de valeur codée en dur. Le motif de référence est celui déjà utilisé par les PDF labo (WeasyPrint + Jinja2 + `ConfigController.get_structure_info()`).
2. **Filtre de période obligatoire sur les exports de liste** (patients, consultations spirituelles) : l'utilisateur doit pouvoir choisir une période précise (jour, semaine, mois, ou plage personnalisée), pas seulement exporter la totalité.
3. **Export dossier médical = un seul patient à la fois**, réutilisant le dossier consolidé déjà construit au chantier 6 (`GET /patients/{id}/dossier`) — pas une nouvelle agrégation de données, une mise en forme PDF/Excel de ce qui existe déjà.
4. **Export consultations spirituelles** : PDF et CSV, même motif que l'export patients (format + période).
5. L'export patients respecte le filtre d'onglet déjà actif à l'écran (Tous/Clinique/Toxico/Spirituel) au moment de l'export — il ne redéfinit pas le périmètre déjà choisi par l'utilisateur.

## Section 1 — Utilitaire d'en-tête PDF partagé (fondation) + correctif facture caisse

**Constat vérifié avant conception** : la facture caisse (`utils/invoice_pdf_generator.py`) utilise un générateur **FPDF** entièrement séparé du pipeline WeasyPrint+Jinja2 déjà utilisé pour les PDF labo. Sa fonction `get_company_info()` renvoie un dictionnaire **codé en dur** :
```python
return {
    "name": "AH2 Santé",
    "address": "123 Rue de l'Hôpital, Ville, Pays",
    "contact": "+237 6xx xxx xxx",
    "email": "contact@ah2sante.com",
    "logo_path": os.path.join('assets','logo_light.png')
}
```
Ni `ConfigController.get_structure_info()` ni `OrganizationConfig` ne sont référencés nulle part dans ce fichier ni dans `repositories/caisse_repo.py::generate_invoice_pdf_content`. Changer le nom ou le logo de l'établissement dans `SystemConfig.vue` n'a donc **aucun effet** sur les factures déjà en production — contrairement à ce que l'utilisateur croyait et à ce que le motif visuel des autres PDF laisse supposer.

**Nouveau module** : `api_backend/backend_app/utils/pdf_header.py` — fonction `get_pdf_header_context(config_ctrl) -> dict` qui appelle `get_structure_info()` et résout `logo_url` en `logo_path` exploitable par WeasyPrint, exactement le motif déjà validé (`controller/lab_controller.py::get_print_data`) :
```python
logo_path = None
if structure and structure.logo_url:
    local_logo = Path(structure.logo_url.lstrip("/")).resolve()
    if local_logo.is_file():
        logo_path = local_logo.as_uri()
```
Jamais une URL absolue — toujours un chemin de fichier local résolu via `.as_uri()`.

**Template partagé** : `api_backend/backend_app/utils/templates/_pdf_header.html`, extrait du bloc `header`/`hospital-info`/`logo-container` déjà présent dans `lab_result_template.html`, inclus (`{% include %}`) par tous les nouveaux templates PDF de ce chantier.

**Correctif facture caisse** : `utils/invoice_pdf_generator.py` (FPDF) est remplacé par un template WeasyPrint+Jinja2 (`api_backend/backend_app/utils/templates/invoice_template.html`, incluant `_pdf_header.html`), consommé par `repositories/caisse_repo.py::generate_invoice_pdf_content` via le même `pdf_generator.py::render_pdf_from_template` générique déjà utilisé pour le labo. Le contenu métier de la facture (lignes, montants, patient, mode de paiement) reste identique — seul le mécanisme de rendu et la source de l'en-tête changent.

## Section 2 — Export liste patients (PDF + CSV)

**Frontend** : nouveau bouton "Exporter" sur `PatientList.vue`, ouvrant une modale `PatientExportModal.vue` : choix du format (PDF/CSV) + période (boutons préréglages Jour/Semaine/Mois, motif déjà utilisé dans `LabDashboard.vue`, plus une plage personnalisée avec 2 champs date, motif déjà utilisé dans `FinancialList.vue`). L'onglet actif (`ALL`/`CLINIQUE`/`TOXICO`/`SPIRITUEL`) et la recherche en cours sont transmis tels quels — l'export respecte ce que l'utilisateur voit déjà à l'écran.

**Backend** : nouvel endpoint `GET /patients/export` (routeur `patients_endpoints.py`), paramètres `format` (`pdf`|`csv`), `date_from`/`date_to` (filtrant sur `Patient.created_at`), plus les mêmes paramètres de filtre déjà utilisés par `GET /patients/`/`/clinical`/`/toxicology`/`/spiritual/list` (`type`, `search`). Réutilise `PatientController.list_patients()` (ou la méthode de domaine correspondante) sans limite de pagination pour l'export — mais avec le filtre de date en plus, nouveau sur ce contrôleur. CSV : `csv.writer` stdlib, colonnes = les mêmes champs déjà affichés dans `PatientList.vue`. PDF : nouveau template `patients_export_template.html` (en-tête partagé + tableau).

## Section 3 — Export dossier médical (un seul patient, PDF + Excel)

**Frontend** : nouveau bouton "Exporter le dossier" sur `PatientDetailView.vue`, choix du format (PDF/Excel), pas de filtre de période (le dossier consolidé complet, tel qu'affiché à l'écran).

**Backend** : nouvel endpoint `GET /patients/{id}/dossier/export`, paramètre `format` (`pdf`|`excel`). Réutilise directement `PatientDossierController.get_full_dossier(patient_id)` — **doit respecter le même cloisonnement medecin/nurse déjà en place** (chantier périmètre médical, 2026-09-22) : un medecin/nurse import/exportant un dossier ne doit pas se retrouver avec le détail toxico/spirituel dans le fichier téléchargé, alors que l'écran le lui masque déjà. PDF : nouveau template réutilisant les mêmes sections que `PatientDetailView.vue` (clinique, labo, prescriptions, + toxico/spirituel si présents dans la réponse). Excel (`openpyxl`) : un onglet par domaine présent dans la réponse.

**Dépendance de build** : `openpyxl` est aujourd'hui listé uniquement dans `requirements-desktop.txt` (chantier `2c`, 2026-09-23) — ce chantier le rend nécessaire côté API aussi. Il migre vers `requirements-api.txt` (consommé par les deux via l'inclusion `-r requirements-api.txt` déjà en place dans `requirements-desktop.txt`, donc aucune régression desktop).

## Section 4 — Export liste consultations spirituelles (PDF + CSV)

Même motif que la Section 2, sur `ConsultationsList.vue` : bouton "Exporter" → modale format + période (filtrant sur `ConsultationSpirituel.consultation_date`), nouvel endpoint `GET /cs/export`. Réutilise le filtre `search` déjà corrigé au groupe 2 (`J1`) et l'enrichissement `patient_name`/`patient_code` déjà en place pour l'affichage tabulaire (PDF et CSV).

## Hors périmètre

- Aucun export en masse de plusieurs dossiers médicaux à la fois (confirmé par l'utilisateur : un seul patient par export dossier).
- Aucun changement aux filtres d'écran existants (onglets patients, recherche) — l'export les consomme, ne les redéfinit pas.
- Aucun export pour la pharmacie/stock, le labo, ou les prescriptions — hors du périmètre `L3d` tel que listé.

## Tests à prévoir (indicatif, détaillé dans le plan)

- Changer le nom/logo dans `SystemConfig.vue`, télécharger une facture caisse, vérifier que le nouveau nom/logo apparaît (non-régression du correctif Section 1).
- Export patients PDF/CSV sur une période sans résultat → fichier valide mais vide (pas d'erreur).
- Export dossier médical par un compte `medecin` sur un patient multi-domaines → fichier ne contient jamais toxico/spirituel (même garantie que l'écran, chantier périmètre médical).
- Export consultations spirituelles avec le filtre `search` actif → seules les lignes correspondantes dans le fichier exporté.
