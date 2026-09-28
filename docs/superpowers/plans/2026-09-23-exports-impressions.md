# Exports et impressions (registre L3d) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corriger l'en-tête codé en dur de la facture caisse et livrer 3 exports absents (liste patients, dossier médical, liste consultations spirituelles), tous avec un en-tête PDF dynamique partagé (nom/logo depuis la config système) et un filtre de période sur les exports de liste.

**Architecture:** Un utilitaire Python partagé (`pdf_header.py`) résout une seule fois le nom/logo d'établissement depuis `OrganizationConfig`, réutilisé par tous les générateurs PDF (labo existant, facture caisse retrofittée, 3 nouveaux exports). Chaque export de liste (patients, consultations) suit le même triplet endpoint-backend + composant-modal-frontend-partagé. L'export dossier réutilise directement `PatientDossierController.get_full_dossier()` déjà construit (chantier 6), sans nouvelle agrégation de données.

**Tech Stack:** FastAPI, Jinja2 + WeasyPrint (PDF), `csv` stdlib (CSV), `openpyxl` (Excel), Vue 3 + Pinia (frontend), pytest.

**Spec:** `docs/superpowers/specs/2026-09-23-exports-impressions-design.md`

## Global Constraints

- **En-tête PDF dynamique partout** : tout nouveau PDF, et la facture caisse existante, utilisent `OrganizationConfig` (nom, adresse, contacts, logo) — jamais de valeur codée en dur. `logo_url` (chemin relatif servi par `/static`) est toujours résolu en `file://...` via `Path(structure.logo_url.lstrip("/")).resolve().as_uri()` — jamais utilisé comme URL absolue (motif déjà validé, `controller/lab_controller.py::get_print_data`).
- **Filtre de période obligatoire** sur les exports de liste (patients, consultations spirituelles) : `date_from`/`date_to`, filtrant respectivement sur `Patient.created_at` et `ConsultationSpirituel.consultation_date`.
- **Export dossier médical = un seul patient**, réutilise `PatientDossierController.get_full_dossier(patient_id)` tel quel — le cloisonnement medecin/nurse déjà en place (clés `dossier_toxico`/`historique_spirituel` absentes de la réponse pour ce rôle) doit se répercuter dans le fichier exporté sans code supplémentaire : ne jamais lire ces clés autrement qu'avec `.get(...)`.
- **L'export patients respecte le filtre d'onglet déjà actif à l'écran** (`ALL`/`CLINIQUE`/`TOXICO`/`SPIRITUEL`) — il ne redéfinit pas le périmètre.
- Aucun commit git à aucune étape (règle immuable de ce projet).

---

### Task 1: Utilitaire d'en-tête PDF partagé + retrofit labo

**Files:**
- Create: `api_backend/backend_app/utils/pdf_header.py`
- Create: `api_backend/backend_app/utils/templates/_pdf_header.html`
- Modify: `api_backend/backend_app/utils/templates/lab_result_template.html:97-128` (remplacer le bloc `<div class="header">` par un include)
- Modify: `controller/lab_controller.py:267-282` (`get_print_data`, utiliser le nouvel utilitaire)
- Test: `tests/test_lab_pdf_export.py` (nouveau fichier)

**Interfaces:**
- Produces: `get_pdf_header_context(config_ctrl) -> dict` avec les clés `structure` (objet `OrganizationConfig` ou `None`) et `logo_path` (`str | None`, URI `file://...`). Toutes les tâches suivantes qui génèrent un PDF appellent cette fonction et fusionnent son retour dans le contexte passé à leur template (`{**get_pdf_header_context(config_ctrl), ...autres_cles...}`).
- Consumes: `ConfigController.get_structure_info()` (déjà existant, `controller/config_controller.py`).

- [ ] **Step 1: Créer l'utilitaire partagé**

Créer `api_backend/backend_app/utils/pdf_header.py` :

```python
# api_backend/backend_app/utils/pdf_header.py
from pathlib import Path
from typing import Any, Dict


def get_pdf_header_context(config_ctrl: Any) -> Dict[str, Any]:
    """
    Resout une seule fois les infos d'etablissement (nom, adresse, logo)
    pour tout generateur PDF de ce projet - source unique, evite la
    derive deja constatee (facture caisse ignorait completement
    OrganizationConfig avant ce chantier, nom/logo codes en dur).

    logo_url est un chemin relatif servi par /static (ex.
    "/static/uploads/logos/xxx.png"), jamais une URL absolue - WeasyPrint
    ne peut pas la resoudre via base_url si elle commence par "/". On
    resout donc ici directement le fichier local sur disque (meme
    convention que UPLOAD_DIR dans config_controller.py, relative au CWD
    du process), motif deja valide par controller/lab_controller.py.
    """
    structure = config_ctrl.get_structure_info()

    logo_path = None
    if structure and structure.logo_url:
        local_logo = Path(structure.logo_url.lstrip("/")).resolve()
        if local_logo.is_file():
            logo_path = local_logo.as_uri()

    return {"structure": structure, "logo_path": logo_path}
```

- [ ] **Step 2: Extraire le bloc d'en-tête en partiel Jinja2**

Créer `api_backend/backend_app/utils/templates/_pdf_header.html` avec exactement le contenu actuellement en ligne 97-128 de `lab_result_template.html` :

```html
<div class="header">
    <div class="hospital-info">
        <h1>{{ structure.name }}</h1>
        {% if structure.slogan %}
            <p style="font-style: italic; color: #555;">{{ structure.slogan }}</p>
        {% endif %}

        <p>
            {{ structure.address }}
            {% if structure.city %} - {{ structure.city }}{% endif %}
            {% if structure.po_box %} | BP: {{ structure.po_box }}{% endif %}
        </p>

        <p>
            Tel: {{ structure.phone }}
            {% if structure.phone2 %} / {{ structure.phone2 }}{% endif %}
        </p>

        {% if structure.email %}<p>Email: {{ structure.email }}</p>{% endif %}
        {% if structure.website %}<p>Web: {{ structure.website }}</p>{% endif %}
    </div>
    <div style="margin-top: 40px; font-size: 8pt; color: #7f8c8d; text-align: center; border-top: 1px solid #ccc; padding-top: 10px;">
    {% if structure.niu %}NIU: {{ structure.niu }} | {% endif %}
    {% if structure.rccm %}RCCM: {{ structure.rccm }} | {% endif %}
    {% if structure.legal_info %}{{ structure.legal_info }}{% endif %}
</div>
    <div class="logo-container">
        {% if logo_path %}
            <img src="{{ logo_path }}" class="logo" alt="Logo">
        {% endif %}
    </div>
</div>
```

- [ ] **Step 3: Remplacer le bloc en ligne par l'include dans le template labo**

Dans `api_backend/backend_app/utils/templates/lab_result_template.html`, remplacer les lignes 97-128 (le bloc `<div class="header">...</div>` complet) par :

```html
    {% include '_pdf_header.html' %}
```

Le reste du fichier (styles CSS lignes 1-93, `info-section` ligne 130 et après) reste identique.

- [ ] **Step 4: Retrofitter `get_print_data` pour utiliser l'utilitaire**

Dans `controller/lab_controller.py`, importer en tête de fichier :

```python
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
```

Puis remplacer (lignes 267-282) :

```python
        structure = config_ctrl.get_structure_info()

        # logo_url est desormais un chemin relatif servi par /static (ex.
        # "/static/uploads/logos/xxx.png" - voir config_controller.py), pas
        # une URL absolue http://host:port/... comme avant. WeasyPrint
        # (utils/pdf_generator.py) resout les chemins relatifs d'un <img>
        # contre base_url=utils_dir, ce qui casserait un chemin commencant
        # par "/". On resout donc ici directement le fichier local sur
        # disque (meme convention que UPLOAD_DIR dans config_controller.py,
        # relative au CWD du process) - pas de dependance a l'hote/port du
        # backend, ni a un aller-retour HTTP inutile vers soi-meme.
        logo_path = None
        if structure and structure.logo_url:
            local_logo = Path(structure.logo_url.lstrip("/")).resolve()
            if local_logo.is_file():
                logo_path = local_logo.as_uri()
```

par :

```python
        # Resolution nom/logo centralisee (chantier exports, 2026-09-23) -
        # voir api_backend/backend_app/utils/pdf_header.py pour le detail.
        header_ctx = get_pdf_header_context(config_ctrl)
```

Puis dans le `return` final (ligne ~340-355), remplacer :

```python
        return {
            "structure": structure,
            "logo_path": logo_path,
            "patient": patient_info,
```

par :

```python
        return {
            **header_ctx,
            "patient": patient_info,
```

(le reste du dict retourné est inchangé).

- [ ] **Step 5: Écrire le test de non-régression**

Créer `tests/test_lab_pdf_export.py` :

```python
# tests/test_lab_pdf_export.py
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from api_backend.backend_app.routes.admin import config_endpoints
from models.lab import Examen, LabResult
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "Correct123!"


def test_lab_pdf_reflete_le_nom_etablissement_configure(db_session, api_client):
    """Chantier exports (2026-09-23) : le PDF labo doit refleter le nom
    d'etablissement reellement configure, pas une valeur figee - preuve
    que get_pdf_header_context() lit bien OrganizationConfig en direct."""
    admin = create_test_user(db_session, "pdf_labo_admin", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="PdfLabo")
    examen = Examen(code="PDFTEST1", nom="Glycemie", categorie="Biochimie", prix=1000)
    db_session.add(examen)
    db_session.flush()
    resultat = LabResult(
        patient_id=patient_id, test_type="Glycemie", status="completed",
        examen_id=examen.id, code_lab_patient="LABPDF-001",
    )
    db_session.add(resultat)
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints, config_endpoints)
    headers = auth_headers(client, "pdf_labo_admin", TEST_PASSWORD)

    nom_unique = "Clinique Test Chantier Exports 2026"
    # /config/structure est POST + multipart/form-data (Form(...) cote
    # endpoint, pas de JSON) - "name" est le seul champ requis.
    resp_config = client.post("/config/structure", data={"name": nom_unique}, headers=headers)
    assert resp_config.status_code == 200, resp_config.text

    resp_pdf = client.get(f"/labo/results/{resultat.result_id}/pdf", headers=headers)

    assert resp_pdf.status_code == 200, resp_pdf.text
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert len(resp_pdf.content) > 1000
```

- [ ] **Step 6: Lancer le test, vérifier qu'il échoue avant le retrofit puis passe après**

Run: `python -m pytest tests/test_lab_pdf_export.py -v`
Expected: PASS une fois les Steps 1-4 appliqués (le test seul, sans les Steps précédents, échouerait sur un `AttributeError`/`ImportError` puisque `get_pdf_header_context` n'existerait pas encore — appliquer les steps dans l'ordre écrit suffit, pas besoin de le lancer avant le Step 4).

- [ ] **Step 7: Vérifier qu'aucun PDF labo existant ne casse**

Run: `python -m pytest tests/test_lab_medical_scope.py -v`
Expected: tous les tests déjà existants sur ce module continuent de passer (aucun ne dépend du détail interne de `get_print_data`, seulement de son comportement observable).

- [ ] **Step 8: Commit**

(Pas de commit — règle immuable de ce projet.)

---

### Task 2: Retrofit facture caisse (FPDF codé en dur → WeasyPrint + en-tête dynamique)

**Files:**
- Modify: `repositories/caisse_repo.py:594-609` (`generate_invoice_pdf_content`)
- Create: `api_backend/backend_app/utils/templates/invoice_template.html`
- Modify: `api_backend/backend_app/utils/pdf_generator.py` (généraliser `build_medical_pdf` en fonction réutilisable par template)
- Test: `tests/test_caisse.py` (étendre le test existant)

**Interfaces:**
- Consumes: `get_pdf_header_context()` (Task 1).
- Produces: `render_pdf_from_template(template_name: str, context: dict) -> bytes` dans `pdf_generator.py`, réutilisée par la Tâche 3 (export patients PDF) et la Tâche 5 (export consultations PDF).

- [ ] **Step 1: Généraliser `pdf_generator.py`**

Remplacer le contenu de `api_backend/backend_app/utils/pdf_generator.py` par :

```python
import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


def render_pdf_from_template(template_name: str, context: dict) -> bytes:
    """
    Rend un template Jinja2 (dossier utils/templates/) fusionne avec
    context, retourne les bytes du PDF genere par WeasyPrint. Fonction
    generique reutilisee par tous les exports PDF de ce projet (labo,
    facture caisse, export patients, export consultations) - chantier
    exports 2026-09-23, remplace l'ancienne build_medical_pdf() specifique
    au labo (conservee ci-dessous comme fine wrapper retro-compatible).
    """
    utils_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(utils_dir, 'templates')

    if not os.path.exists(template_dir):
        raise FileNotFoundError(f"Le dossier des templates est introuvable ici : {template_dir}")

    env = Environment(loader=FileSystemLoader(template_dir))

    try:
        template = env.get_template(template_name)
    except Exception:
        raise FileNotFoundError(f"Impossible de trouver '{template_name}' dans {template_dir}")

    html_content = template.render(**context)

    pdf_bytes = HTML(string=html_content, base_url=utils_dir).write_pdf()

    if not pdf_bytes:
        raise ValueError("Erreur interne : WeasyPrint n'a pas pu générer le PDF.")

    return pdf_bytes


def build_medical_pdf(print_data: dict) -> bytes:
    """
    Prend le dictionnaire complet de donnees du laboratoire, le fusionne
    avec le template labo, et retourne les bytes du PDF. Conserve tel
    quel (signature et comportement inchanges) pour ne pas toucher
    controller/lab_controller.py au-dela de la Tache 1 de ce plan.
    """
    return render_pdf_from_template('lab_result_template.html', print_data)
```

- [ ] **Step 2: Créer le template de facture**

Créer `api_backend/backend_app/utils/templates/invoice_template.html` — porte fidèlement le contenu métier de l'ancien générateur FPDF (`utils/invoice_pdf_generator.py`, transaction, patient, caissier, tableau des lignes, total/avance/reste à payer) :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Facture {{ transaction.transaction_id }}</title>
    <style>
        @page { size: A4; margin: 2cm; @bottom-right { content: "Page " counter(page) " sur " counter(pages); font-size: 9pt; color: #666; } }
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; font-size: 11pt; line-height: 1.5; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; margin-bottom: 20px; }
        .hospital-info h1 { margin: 0; color: #2c3e50; font-size: 18pt; }
        .hospital-info p { margin: 2px 0; font-size: 10pt; }
        .logo { max-width: 150px; max-height: 80px; }
        .invoice-title { text-align: center; font-size: 16pt; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; color: #2c3e50; }
        .meta-row { display: flex; justify-content: space-between; background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 25px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th { background-color: #2c3e50; color: white; text-align: left; padding: 8px; font-size: 10pt; }
        td { padding: 8px; border-bottom: 1px solid #ddd; font-size: 10pt; }
        .num { text-align: right; }
        .center { text-align: center; }
        .totals { margin-top: 15px; width: 100%; }
        .totals td { border: none; padding: 4px 8px; }
        .totals .label { text-align: right; }
        .totals .value { text-align: right; width: 120px; font-weight: bold; }
        .remaining { color: #d9534f; }
    </style>
</head>
<body>

    {% include '_pdf_header.html' %}

    <div class="invoice-title">Facture détaillée</div>

    <div class="meta-row">
        <div>
            <p><strong>Transaction N°</strong> {{ transaction.transaction_id }}</p>
            <p><strong>Statut :</strong> {{ transaction.status | upper }}</p>
            <p><strong>Patient :</strong> {{ transaction.patient_name }}</p>
        </div>
        <div>
            <p><strong>Enregistré par :</strong> {{ transaction.caissier_name }}</p>
            <p><strong>Date de la facture :</strong> {{ date_impression }}</p>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Description</th>
                <th>Référence</th>
                <th class="center">Qté</th>
                <th class="num">P. Unit. (CFA)</th>
                <th class="num">Total (CFA)</th>
            </tr>
        </thead>
        <tbody>
            {% for item in transaction.items %}
            <tr>
                <td>{{ item.description }}</td>
                <td class="center">{{ item.ref }}</td>
                <td class="center">{{ item.quantity }}</td>
                <td class="num">{{ "%.2f"|format(item.unit_price) }}</td>
                <td class="num">{{ "%.2f"|format(item.line_total) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <table class="totals">
        <tr>
            <td class="label">TOTAL FACTURE :</td>
            <td class="value">{{ "%.2f"|format(transaction.amount) }} CFA</td>
        </tr>
        <tr>
            <td class="label">Montant payé (avance) :</td>
            <td class="value">{{ "%.2f"|format(transaction.advance_amount) }} CFA</td>
        </tr>
        {% if transaction.remaining > 0 %}
        <tr>
            <td class="label remaining">RESTE À PAYER :</td>
            <td class="value remaining">{{ "%.2f"|format(transaction.remaining) }} CFA</td>
        </tr>
        {% endif %}
    </table>

</body>
</html>
```

- [ ] **Step 3: Remplacer le générateur FPDF par le rendu WeasyPrint dans le repo**

Dans `repositories/caisse_repo.py`, en tête de fichier, ajouter les imports :

```python
from datetime import datetime
from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository
```

Remplacer (lignes 594-609) :

```python
    def generate_invoice_pdf_content(self, transaction_id: int) -> bytes:
        transaction_data = self.get_transaction_details_for_invoice(transaction_id)
        if not transaction_data:
            raise ValueError(f"Transaction ID {transaction_id} non trouvée pour génération PDF.")
        pdf_bytes = export_invoice_to_pdf_bytes(transaction_data)
        return pdf_bytes
```

par :

```python
    def generate_invoice_pdf_content(self, transaction_id: int) -> bytes:
        transaction_data = self.get_transaction_details_for_invoice(transaction_id)
        if not transaction_data:
            raise ValueError(f"Transaction ID {transaction_id} non trouvée pour génération PDF.")

        config_ctrl = ConfigController(repo=ConfigRepository(self.session))
        header_ctx = get_pdf_header_context(config_ctrl)

        amount = float(transaction_data.get('amount', 0) or 0)
        advance = float(transaction_data.get('advance_amount', 0) or 0)
        items = []
        for item in transaction_data.get('items', []):
            try:
                unit_price = float(item.get('unit_price', 0) or 0)
                line_total = float(item.get('line_total', 0) or 0)
            except (TypeError, ValueError):
                unit_price = 0.0
                line_total = 0.0
            items.append({
                "description": f"{item.get('item_type', 'Service')} - {item.get('item_name', 'Détail')}",
                "ref": str(item.get('item_ref_id', '') or ''),
                "quantity": item.get('quantity', 1),
                "unit_price": unit_price,
                "line_total": line_total,
            })

        context = {
            **header_ctx,
            "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            "transaction": {
                "transaction_id": transaction_data.get('transaction_id', 'N/A'),
                "status": transaction_data.get('status', ''),
                "patient_name": transaction_data.get('patient_name') or transaction_data.get('patient_label', 'Inconnu'),
                "caissier_name": transaction_data.get('user_name') or transaction_data.get('created_by_name', 'N/A'),
                "items": items,
                "amount": amount,
                "advance_amount": advance,
                "remaining": amount - advance,
            },
        }

        return render_pdf_from_template('invoice_template.html', context)
```

Vérifié : `export_invoice_to_pdf_bytes` n'est appelé qu'à cet unique endroit dans ce fichier (ligne 608 avant ce Step). Retirer la ligne d'import devenue inutile en tête de fichier (ligne 12) :

```python
from utils.invoice_pdf_generator import export_invoice_to_pdf_bytes
```

(Le fichier `utils/invoice_pdf_generator.py` lui-même n'est pas supprimé par ce plan — il devient simplement du code mort, à nettoyer dans un futur chantier de dette technique si jugé utile.)

- [ ] **Step 4: Étendre le test existant pour vérifier l'en-tête dynamique**

Dans `tests/test_caisse.py`, retrouver `test_download_invoice_pdf_success` et ajouter juste après (nouveau test, ne pas modifier l'existant) :

```python
def test_invoice_pdf_reflete_le_nom_etablissement_configure(db_session, api_client):
    """Chantier exports (2026-09-23) : avant ce chantier, la facture
    utilisait un nom/logo code en dur ('AH2 Sante'), ignorant totalement
    OrganizationConfig - ce test verifie que ce n'est plus le cas."""
    from api_backend.backend_app.routes.admin import config_endpoints

    admin = create_test_user(db_session, "invoice_pdf_admin", "admin", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, admin)
    db_session.flush()

    client = api_client(auth_endpoints, caisse_endpoints, config_endpoints)
    headers = auth_headers(client, "invoice_pdf_admin", TEST_PASSWORD)

    resp_config = client.post("/config/structure", data={"name": "Clinique Facture Test 2026"}, headers=headers)
    assert resp_config.status_code == 200, resp_config.text

    resp = client.get(f"/caisse/{tx.transaction_id}/invoice/download", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 1000
```

(Vérifier les imports déjà présents en tête de `tests/test_caisse.py` — `create_test_transaction`, `caisse_endpoints`, `auth_endpoints`, `create_test_user`, `auth_headers` sont déjà utilisés par `test_download_invoice_pdf_success` d'après le plan ; ajouter uniquement l'import local de `config_endpoints` montré ci-dessus si absent du fichier.)

- [ ] **Step 5: Lancer les tests**

Run: `python -m pytest tests/test_caisse.py -k invoice -v`
Expected: tous les tests liés à la facture passent, y compris le nouveau et l'existant `test_download_invoice_pdf_success`/`test_download_invoice_pdf_not_found`.

- [ ] **Step 6: Commit**

(Pas de commit — règle immuable de ce projet.)

---

### Task 3: Export liste patients — backend (PDF + CSV)

**Files:**
- Modify: `api_backend/backend_app/routes/patients/patients_endpoints.py` (nouvelle route)
- Modify: `controller/patient_controller.py` (nouvelle méthode d'export)
- Modify: `repositories/patient_repo.py` (nouvelle méthode, filtre de date sans pagination)
- Create: `api_backend/backend_app/utils/templates/patients_export_template.html`
- Test: `tests/test_patients_export.py` (nouveau fichier)

**Interfaces:**
- Consumes: `render_pdf_from_template()`, `get_pdf_header_context()` (Task 1-2).
- Produces: `GET /patients/export?format=pdf|csv&type=ALL|CLINIQUE|TOXICO|SPIRITUEL&search=...&date_from=...&date_to=...` — réutilisé nulle part ailleurs dans ce plan (chaque export a son propre endpoint), mais le motif (filtre + génération PDF/CSV) est répliqué à l'identique par la Tâche 5.

- [ ] **Step 1: Nouvelle méthode repo — liste complète filtrée, sans pagination**

Dans `repositories/patient_repo.py`, ajouter une nouvelle méthode (à côté de `list_patients`) :

```python
    def list_patients_for_export(self, search: Optional[str] = None, filters: Optional[Dict[str, bool]] = None,
                                   date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[Patient]:
        """
        Meme logique de filtrage que list_patients (recherche, drapeaux de
        domaine), sans pagination - destine a l'export (PDF/CSV), jamais a
        l'affichage ecran. Filtre de periode supplementaire sur created_at
        (registre exports, 2026-09-23) - absent de list_patients.
        """
        query = self.session.query(Patient).filter(Patient.is_deleted == False)  # noqa: E712

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Patient.first_name.ilike(term),
                    Patient.last_name.ilike(term),
                    Patient.code_patient.ilike(term),
                    Patient.national_id.ilike(term),
                    Patient.contact_phone.ilike(term),
                )
            )
        elif filters:
            if filters.get('is_clinical'):
                query = query.filter(exists().where(MedicalRecord.patient_id == Patient.patient_id))
            if filters.get('is_toxicology'):
                query = query.filter(exists().where(ToxicoDossier.patient_id == Patient.patient_id))
            if filters.get('is_spiritual'):
                query = query.filter(exists().where(ConsultationSpirituel.patient_id == Patient.patient_id))

        if date_from:
            query = query.filter(func.date(Patient.created_at) >= date_from)
        if date_to:
            query = query.filter(func.date(Patient.created_at) <= date_to)

        return query.order_by(Patient.last_updated_at.desc()).all()
```

Vérifier en tête de fichier que `MedicalRecord`, `ToxicoDossier`, `ConsultationSpirituel`, `exists`, `or_`, `func`, `date` sont déjà importés (déjà utilisés par `list_patients`/`list_clinical_patients` dans ce même fichier) — ajouter uniquement les imports manquants.

- [ ] **Step 2: Nouvelle méthode controller — construit le filtre selon le rôle et le type d'onglet**

Dans `controller/patient_controller.py`, ajouter :

```python
    def list_patients_for_export(self, tab_type: str = "ALL", search: Optional[str] = None,
                                   date_from=None, date_to=None) -> List:
        """
        Meme mapping onglet -> filtre que les endpoints /clinical,
        /toxicology, /spiritual/list existants - l'export respecte
        l'onglet actif a l'ecran (decision utilisateur, chantier exports).
        """
        filters = None
        if tab_type == "CLINIQUE":
            filters = {"is_clinical": True}
        elif tab_type == "TOXICO":
            filters = {"is_toxicology": True}
        elif tab_type == "SPIRITUEL":
            filters = {"is_spiritual": True}
        return self.repo.list_patients_for_export(search=search, filters=filters, date_from=date_from, date_to=date_to)
```

- [ ] **Step 3: Template PDF export patients**

Créer `api_backend/backend_app/utils/templates/patients_export_template.html` :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Export Patients</title>
    <style>
        @page { size: A4 landscape; margin: 1.5cm; @bottom-right { content: "Page " counter(page) " sur " counter(pages); font-size: 9pt; color: #666; } }
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; font-size: 10pt; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; margin-bottom: 15px; }
        .hospital-info h1 { margin: 0; color: #2c3e50; font-size: 16pt; }
        .hospital-info p { margin: 2px 0; font-size: 9pt; }
        .logo { max-width: 120px; max-height: 60px; }
        .export-title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 5px; color: #2c3e50; }
        .export-meta { text-align: center; font-size: 9pt; color: #666; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; }
        th { background-color: #2c3e50; color: white; text-align: left; padding: 6px; font-size: 9pt; }
        td { padding: 6px; border-bottom: 1px solid #ddd; font-size: 9pt; }
    </style>
</head>
<body>

    {% include '_pdf_header.html' %}

    <div class="export-title">Liste des patients</div>
    <div class="export-meta">{{ periode_label }} — {{ patients|length }} patient(s) — généré le {{ date_impression }}</div>

    <table>
        <thead>
            <tr>
                <th>Code</th>
                <th>Nom</th>
                <th>Prénom</th>
                <th>Téléphone</th>
                <th>Date de naissance</th>
                <th>Inscrit le</th>
            </tr>
        </thead>
        <tbody>
            {% for p in patients %}
            <tr>
                <td>{{ p.code_patient }}</td>
                <td>{{ p.last_name }}</td>
                <td>{{ p.first_name }}</td>
                <td>{{ p.contact_phone or '-' }}</td>
                <td>{{ p.birth_date }}</td>
                <td>{{ p.created_at }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

</body>
</html>
```

- [ ] **Step 4: Endpoint d'export**

Dans `api_backend/backend_app/routes/patients/patients_endpoints.py`, ajouter en tête de fichier :

```python
import csv
import io
from datetime import date as date_type, datetime
from fastapi.responses import Response, StreamingResponse
from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository
```

Puis ajouter la route (avant la route générique `GET /{patient_id}`, pour éviter tout risque de shadowing par cette dernière — même précaution déjà appliquée aux autres routes fixes de ce fichier) :

```python
@router.get("/export")
def export_patients(
    format: str = Query(..., regex="^(pdf|csv)$"),
    type: str = Query("ALL", regex="^(ALL|CLINIQUE|TOXICO|SPIRITUEL)$"),
    search: Optional[str] = Query(None),
    date_from: Optional[date_type] = Query(None),
    date_to: Optional[date_type] = Query(None),
    patient_ctrl: PatientController = Depends(get_patient_controller),
    db: Session = Depends(get_db),
):
    patients = patient_ctrl.list_patients_for_export(tab_type=type, search=search, date_from=date_from, date_to=date_to)

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Code", "Nom", "Prénom", "Téléphone", "Date de naissance", "Inscrit le"])
        for p in patients:
            writer.writerow([
                p.code_patient, p.last_name, p.first_name,
                p.contact_phone or "", p.birth_date or "", p.created_at or "",
            ])
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=patients_export.csv"},
        )

    config_ctrl = ConfigController(repo=ConfigRepository(db))
    header_ctx = get_pdf_header_context(config_ctrl)

    if date_from and date_to:
        periode_label = f"Période du {date_from} au {date_to}"
    elif date_from:
        periode_label = f"Depuis le {date_from}"
    elif date_to:
        periode_label = f"Jusqu'au {date_to}"
    else:
        periode_label = "Toutes périodes"

    pdf_bytes = render_pdf_from_template('patients_export_template.html', {
        **header_ctx,
        "patients": patients,
        "periode_label": periode_label,
        "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M"),
    })
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=patients_export.pdf"},
    )
```

- [ ] **Step 5: Tests**

Créer `tests/test_patients_export.py` :

```python
# tests/test_patients_export.py
from datetime import date, timedelta

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "Correct123!"


def test_export_patients_csv_contient_le_patient_cree(db_session, api_client):
    admin = create_test_user(db_session, "export_patients_csv", "admin", password=TEST_PASSWORD)
    _, data = create_test_patient(db_session, admin, first_name="ExportCsvUnique", last_name="TestExport")
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "export_patients_csv", TEST_PASSWORD)

    resp = client.get("/patients/export?format=csv", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "ExportCsvUnique" in resp.text
    assert "TestExport" in resp.text


def test_export_patients_pdf_genere_un_fichier_valide(db_session, api_client):
    admin = create_test_user(db_session, "export_patients_pdf", "admin", password=TEST_PASSWORD)
    create_test_patient(db_session, admin, first_name="ExportPdfUnique")
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "export_patients_pdf", TEST_PASSWORD)

    resp = client.get("/patients/export?format=pdf", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 500


def test_export_patients_filtre_par_periode_exclut_hors_plage(db_session, api_client):
    admin = create_test_user(db_session, "export_patients_periode", "admin", password=TEST_PASSWORD)
    _, data = create_test_patient(db_session, admin, first_name="ExportPeriodeUnique")
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "export_patients_periode", TEST_PASSWORD)

    hier = date.today() - timedelta(days=1)
    avant_hier = date.today() - timedelta(days=2)

    resp_hors_plage = client.get(
        f"/patients/export?format=csv&date_from={avant_hier}&date_to={hier}", headers=headers
    )
    resp_dans_plage = client.get("/patients/export?format=csv", headers=headers)

    assert "ExportPeriodeUnique" not in resp_hors_plage.text
    assert "ExportPeriodeUnique" in resp_dans_plage.text
```

- [ ] **Step 6: Lancer les tests**

Run: `python -m pytest tests/test_patients_export.py -v`
Expected: 3 passed.

- [ ] **Step 7: Commit**

(Pas de commit — règle immuable de ce projet.)

---

### Task 4: Export liste patients — frontend (modale partagée + bouton)

**Files:**
- Create: `ah2-admin-web/src/components/common/ExportModal.vue`
- Modify: `ah2-admin-web/src/views/modules/patients/PatientList.vue`
- Modify: `ah2-admin-web/src/i18n.js` (nouvelles clés `export.*`)

**Interfaces:**
- Produces: `ExportModal.vue`, props `{ title: String, formats: Array<{value,label}>, onExport: Function }`, émet `close`. Réutilisée telle quelle par la Tâche 6 (export consultations) — ne pas la coupler aux patients dans son implémentation.

- [ ] **Step 1: Créer la modale d'export générique**

Créer `ah2-admin-web/src/components/common/ExportModal.vue` :

```vue
<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50" @click.self="$emit('close')">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-5">
      <div class="flex justify-between items-center">
        <h3 class="text-lg font-bold text-gray-800">{{ title }}</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('export.format_label') }}</label>
        <div class="flex gap-2">
          <button v-for="f in formats" :key="f.value" @click="format = f.value"
                  :class="format === f.value ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
                  class="px-4 py-2 rounded-lg text-sm font-medium transition">
            {{ f.label }}
          </button>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('export.period_label') }}</label>
        <div class="flex gap-2 mb-3">
          <button v-for="p in presets" :key="p.value" @click="applyPreset(p.value)"
                  :class="activePreset === p.value ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
                  class="px-3 py-1.5 rounded-lg text-xs font-bold transition">
            {{ p.label }}
          </button>
        </div>
        <div class="flex gap-2">
          <input type="date" v-model="dateFrom" @input="activePreset = null" class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          <input type="date" v-model="dateTo" @input="activePreset = null" class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
        </div>
      </div>

      <div v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</div>

      <div class="flex justify-end gap-3 pt-2">
        <button @click="$emit('close')" class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm">{{ t('export.cancel') }}</button>
        <button @click="handleExport" :disabled="isExporting"
                class="px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 disabled:opacity-50">
          {{ isExporting ? t('export.exporting') : t('export.confirm') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  title: { type: String, required: true },
  formats: { type: Array, required: true },
  onExport: { type: Function, required: true },
});
const emit = defineEmits(['close']);
const { t } = useI18n();

const format = ref(props.formats[0]?.value);
const dateFrom = ref('');
const dateTo = ref('');
const activePreset = ref(null);
const isExporting = ref(false);
const errorMessage = ref('');

const today = () => new Date().toISOString().slice(0, 10);
const daysAgo = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
};

const presets = [
  { value: 'day', label: t('export.preset_day') },
  { value: 'week', label: t('export.preset_week') },
  { value: 'month', label: t('export.preset_month') },
];

const applyPreset = (preset) => {
  activePreset.value = preset;
  dateTo.value = today();
  if (preset === 'day') dateFrom.value = today();
  else if (preset === 'week') dateFrom.value = daysAgo(7);
  else if (preset === 'month') dateFrom.value = daysAgo(30);
};

const handleExport = async () => {
  isExporting.value = true;
  errorMessage.value = '';
  try {
    await props.onExport({ format: format.value, dateFrom: dateFrom.value || null, dateTo: dateTo.value || null });
    emit('close');
  } catch (err) {
    errorMessage.value = t('export.error');
  } finally {
    isExporting.value = false;
  }
};
</script>
```

- [ ] **Step 2: Ajouter les clés i18n**

Dans `ah2-admin-web/src/i18n.js`, bloc `fr`, ajouter un nouveau namespace top-level `export` (à côté des autres namespaces comme `patients`, `consultations`) :

```javascript
    export: {
      format_label: "Format",
      period_label: "Période",
      preset_day: "Aujourd'hui",
      preset_week: "7 derniers jours",
      preset_month: "30 derniers jours",
      cancel: "Annuler",
      confirm: "Exporter",
      exporting: "Export en cours...",
      error: "Échec de l'export. Veuillez réessayer.",
    },
```

Même bloc en anglais :

```javascript
    export: {
      format_label: "Format",
      period_label: "Period",
      preset_day: "Today",
      preset_week: "Last 7 days",
      preset_month: "Last 30 days",
      cancel: "Cancel",
      confirm: "Export",
      exporting: "Exporting...",
      error: "Export failed. Please try again.",
    },
```

- [ ] **Step 3: Brancher le bouton dans `PatientList.vue`**

Dans la zone d'en-tête où se trouve déjà le bouton "Ajouter un patient" (repérer ce bouton dans le template), ajouter juste avant :

```html
<button @click="showExportModal = true" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition">
  {{ t('export.confirm') }}
</button>
```

Puis, juste avant la fermeture du composant racine du template, ajouter :

```html
<ExportModal
  v-if="showExportModal"
  :title="t('export.confirm') + ' — ' + t('patients.title')"
  :formats="[{ value: 'pdf', label: 'PDF' }, { value: 'csv', label: 'CSV' }]"
  :onExport="exportPatients"
  @close="showExportModal = false"
/>
```

Dans le `<script setup>`, ajouter l'import et la logique :

```javascript
import ExportModal from '@/components/common/ExportModal.vue';
import api from '@/services/api';

const showExportModal = ref(false);

const exportPatients = async ({ format, dateFrom, dateTo }) => {
  const params = {
    format,
    type: patientStore.filters.type,
    search: patientStore.filters.search || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };
  const response = await api.get('/patients/export', {
    params,
    responseType: format === 'pdf' ? 'blob' : 'text',
  });
  const blob = format === 'pdf'
    ? new Blob([response.data], { type: 'application/pdf' })
    : new Blob([response.data], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `patients_export.${format}`;
  link.click();
  window.URL.revokeObjectURL(url);
};
```

(`ref` est déjà importé dans ce fichier via `import { ... } from 'vue'` — ajouter `ref` à cette liste d'import existante s'il n'y est pas déjà. Vérifier avec `grep -n "^import { " src/views/modules/patients/PatientList.vue` avant d'éditer.)

- [ ] **Step 4: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi, aucune erreur.

- [ ] **Step 5: Commit**

(Pas de commit — règle immuable de ce projet.)

---

### Task 5: Export liste consultations spirituelles — backend (PDF + CSV)

**Files:**
- Modify: `api_backend/backend_app/routes/cs/cs_endpoint.py` (nouvelle route)
- Modify: `controller/cs_controller.py` (nouvelle méthode)
- Modify: `repositories/cs_repo.py` (nouvelle méthode, filtre de date + recherche + patient enrichi, sans pagination)
- Create: `api_backend/backend_app/utils/templates/cs_export_template.html`
- Test: `tests/test_cs_export.py` (nouveau fichier)

**Interfaces:**
- Consumes: `render_pdf_from_template()`, `get_pdf_header_context()` (Task 1-2), même motif de filtre de période que la Tâche 3.

- [ ] **Step 1: Nouvelle méthode repo**

Dans `repositories/cs_repo.py`, ajouter (réutilise le join `Patient` déjà introduit par `list_all` au groupe 2 de la dette technique) :

```python
    def list_all_for_export(self, search: Optional[str] = None, date_from=None, date_to=None):
        """Meme filtre que list_all (recherche + jointure Patient), plus
        periode sur consultation_date - destine a l'export, sans
        pagination."""
        query = (
            self.session.query(ConsultationSpirituel)
            .options(joinedload(ConsultationSpirituel.patient))
        )
        if search:
            term = f"%{search.strip()}%"
            query = query.join(Patient, ConsultationSpirituel.patient_id == Patient.patient_id).filter(
                or_(
                    Patient.first_name.ilike(term),
                    Patient.last_name.ilike(term),
                    Patient.code_patient.ilike(term),
                )
            )
        if date_from:
            query = query.filter(func.date(ConsultationSpirituel.consultation_date) >= date_from)
        if date_to:
            query = query.filter(func.date(ConsultationSpirituel.consultation_date) <= date_to)
        return query.order_by(desc(ConsultationSpirituel.consultation_date)).all()
```

Vérifié : `repositories/cs_repo.py` importe actuellement (ligne 3) `from sqlalchemy import desc, or_` — `func` n'y est pas encore. Remplacer cette ligne par :

```python
from sqlalchemy import desc, or_, func
```

- [ ] **Step 2: Nouvelle méthode controller**

Dans `controller/cs_controller.py`, ajouter :

```python
    def list_consultations_for_export(self, search: Optional[str] = None, date_from=None, date_to=None) -> List:
        return self.repo.list_all_for_export(search=search, date_from=date_from, date_to=date_to)
```

- [ ] **Step 3: Template PDF export consultations**

Créer `api_backend/backend_app/utils/templates/cs_export_template.html` (même structure que `patients_export_template.html`, colonnes adaptées) :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Export Consultations Spirituelles</title>
    <style>
        @page { size: A4 landscape; margin: 1.5cm; @bottom-right { content: "Page " counter(page) " sur " counter(pages); font-size: 9pt; color: #666; } }
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; font-size: 10pt; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; margin-bottom: 15px; }
        .hospital-info h1 { margin: 0; color: #2c3e50; font-size: 16pt; }
        .hospital-info p { margin: 2px 0; font-size: 9pt; }
        .logo { max-width: 120px; max-height: 60px; }
        .export-title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 5px; color: #2c3e50; }
        .export-meta { text-align: center; font-size: 9pt; color: #666; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; }
        th { background-color: #2c3e50; color: white; text-align: left; padding: 6px; font-size: 9pt; }
        td { padding: 6px; border-bottom: 1px solid #ddd; font-size: 9pt; }
    </style>
</head>
<body>

    {% include '_pdf_header.html' %}

    <div class="export-title">Consultations spirituelles</div>
    <div class="export-meta">{{ periode_label }} — {{ consultations|length }} consultation(s) — généré le {{ date_impression }}</div>

    <table>
        <thead>
            <tr>
                <th>Patient</th>
                <th>Code</th>
                <th>Type</th>
                <th>Date</th>
                <th>Intervenant</th>
            </tr>
        </thead>
        <tbody>
            {% for c in consultations %}
            <tr>
                <td>{{ c.patient_name or ('#' ~ c.patient_id) }}</td>
                <td>{{ c.patient_code or '-' }}</td>
                <td>{{ c.type_consultation }}</td>
                <td>{{ c.consultation_date }}</td>
                <td>{{ c.created_by_name }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

</body>
</html>
```

- [ ] **Step 4: Endpoint d'export**

Dans `api_backend/backend_app/routes/cs/cs_endpoint.py`, ajouter en tête de fichier (compléter les imports déjà présents, ne pas dupliquer ceux qui existent) :

```python
import csv
import io
from datetime import date as date_type, datetime
from fastapi.responses import Response, StreamingResponse
from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository
```

Puis ajouter la route (avant la route générique `GET /{cs_id}`, même précaution anti-shadowing que la Tâche 3) :

```python
@router.get("/export")
def export_consultations(
    format: str = Query(..., regex="^(pdf|csv)$"),
    search: Optional[str] = Query(None),
    date_from: Optional[date_type] = Query(None),
    date_to: Optional[date_type] = Query(None),
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
    db: Session = Depends(get_db),
):
    raw = cs_ctrl.list_consultations_for_export(search=search, date_from=date_from, date_to=date_to)
    items = [normalize_consultation_data(c) for c in raw]

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Patient", "Code", "Type", "Date", "Intervenant"])
        for c in items:
            writer.writerow([
                c.get("patient_name") or f"#{c.get('patient_id')}", c.get("patient_code") or "",
                c.get("type_consultation"), c.get("consultation_date"), c.get("created_by_name"),
            ])
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=consultations_export.csv"},
        )

    config_ctrl = ConfigController(repo=ConfigRepository(db))
    header_ctx = get_pdf_header_context(config_ctrl)

    if date_from and date_to:
        periode_label = f"Période du {date_from} au {date_to}"
    elif date_from:
        periode_label = f"Depuis le {date_from}"
    elif date_to:
        periode_label = f"Jusqu'au {date_to}"
    else:
        periode_label = "Toutes périodes"

    pdf_bytes = render_pdf_from_template('cs_export_template.html', {
        **header_ctx,
        "consultations": items,
        "periode_label": periode_label,
        "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M"),
    })
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=consultations_export.pdf"},
    )
```

(`normalize_consultation_data` est déjà importé dans ce fichier, réutilisé tel quel pour obtenir `patient_name`/`patient_code` — même fonction que la liste paginée standard.)

- [ ] **Step 5: Tests**

Créer `tests/test_cs_export.py` :

```python
# tests/test_cs_export.py
from datetime import date, timedelta

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.cs import cs_endpoint
from tests.conftest import create_test_user, create_test_patient, auth_headers
from repositories.cs_repo import ConsultationSpirituelRepository

TEST_PASSWORD = "Correct123!"


def test_export_consultations_csv_contient_le_patient(db_session, api_client):
    admin = create_test_user(db_session, "export_cs_csv", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="ExportCsUnique", last_name="TestCs")
    db_session.flush()

    repo = ConsultationSpirituelRepository(db_session)
    repo.create({"patient_id": patient_id, "type_consultation": "Spiritual"}, admin)

    client = api_client(auth_endpoints, cs_endpoint)
    headers = auth_headers(client, "export_cs_csv", TEST_PASSWORD)

    resp = client.get("/cs/export?format=csv", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "ExportCsUnique" in resp.text


def test_export_consultations_pdf_genere_un_fichier_valide(db_session, api_client):
    admin = create_test_user(db_session, "export_cs_pdf", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="ExportCsPdfUnique")
    db_session.flush()

    repo = ConsultationSpirituelRepository(db_session)
    repo.create({"patient_id": patient_id, "type_consultation": "Spiritual"}, admin)

    client = api_client(auth_endpoints, cs_endpoint)
    headers = auth_headers(client, "export_cs_pdf", TEST_PASSWORD)

    resp = client.get("/cs/export?format=pdf", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 500


def test_export_consultations_filtre_par_periode(db_session, api_client):
    admin = create_test_user(db_session, "export_cs_periode", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="ExportCsPeriodeUnique")
    db_session.flush()

    repo = ConsultationSpirituelRepository(db_session)
    repo.create({"patient_id": patient_id, "type_consultation": "Spiritual"}, admin)

    client = api_client(auth_endpoints, cs_endpoint)
    headers = auth_headers(client, "export_cs_periode", TEST_PASSWORD)

    avant_hier = date.today() - timedelta(days=2)
    hier = date.today() - timedelta(days=1)

    resp_hors_plage = client.get(f"/cs/export?format=csv&date_from={avant_hier}&date_to={hier}", headers=headers)
    resp_dans_plage = client.get("/cs/export?format=csv", headers=headers)

    assert "ExportCsPeriodeUnique" not in resp_hors_plage.text
    assert "ExportCsPeriodeUnique" in resp_dans_plage.text
```

- [ ] **Step 6: Lancer les tests**

Run: `python -m pytest tests/test_cs_export.py -v`
Expected: 3 passed.

- [ ] **Step 7: Commit**

(Pas de commit — règle immuable de ce projet.)

---

### Task 6: Export liste consultations spirituelles — frontend (réutilise la modale)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/consultations/ConsultationsList.vue`

**Interfaces:**
- Consumes: `ExportModal.vue` (Task 4), sans aucune modification de ce composant.

- [ ] **Step 1: Brancher le bouton**

Dans la zone toolbar de `ConsultationsList.vue` (le conteneur `flex items-center gap-3` où vit déjà le bouton de nouvelle consultation), ajouter :

```html
<button @click="showExportModal = true" class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition">
  {{ t('export.confirm') }}
</button>
```

Puis, juste avant la fermeture du composant racine du template, ajouter :

```html
<ExportModal
  v-if="showExportModal"
  :title="t('export.confirm') + ' — ' + t('consultations.title')"
  :formats="[{ value: 'pdf', label: 'PDF' }, { value: 'csv', label: 'CSV' }]"
  :onExport="exportConsultations"
  @close="showExportModal = false"
/>
```

Dans le `<script setup>` :

```javascript
import ExportModal from '@/components/common/ExportModal.vue';
import api from '@/services/api';

const showExportModal = ref(false);

const exportConsultations = async ({ format, dateFrom, dateTo }) => {
  const params = {
    format,
    search: consultationStore.filters.search || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };
  const response = await api.get('/cs/export', {
    params,
    responseType: format === 'pdf' ? 'blob' : 'text',
  });
  const blob = format === 'pdf'
    ? new Blob([response.data], { type: 'application/pdf' })
    : new Blob([response.data], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `consultations_export.${format}`;
  link.click();
  window.URL.revokeObjectURL(url);
};
```

(Vérifier si `ref`/`api` sont déjà importés dans ce fichier avant d'ajouter — `grep -n "^import" src/views/modules/consultations/ConsultationsList.vue`.)

- [ ] **Step 2: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

- [ ] **Step 3: Commit**

(Pas de commit — règle immuable de ce projet.)

---

### Task 7: Export dossier médical — backend (PDF + Excel, un seul patient)

**Files:**
- Modify: `requirements-api.txt` (ajouter `openpyxl`)
- Modify: `api_backend/backend_app/routes/patient_dossier/patient_dossier_endpoint.py` (nouvelle route)
- Create: `api_backend/backend_app/utils/templates/dossier_export_template.html`
- Create: `api_backend/backend_app/utils/dossier_excel_export.py`
- Test: `tests/test_dossier_export.py` (nouveau fichier)

**Interfaces:**
- Consumes: `PatientDossierController.get_full_dossier()` (déjà existant, chantier 6 + chantier périmètre médical) — **ne jamais accéder aux clés `dossier_toxico`/`historique_spirituel` autrement qu'avec `.get(...)`**, elles sont absentes de la réponse pour medecin/nurse (garantie déjà en place, ce chantier ne doit rien y changer).

- [ ] **Step 1: Migrer `openpyxl` vers `requirements-api.txt`**

Dans `requirements-desktop.txt`, retirer la ligne `openpyxl==3.1.5` (elle reste disponible pour le desktop via l'inclusion `-r requirements-api.txt` déjà en place, aucune perte d'accès).

Dans `requirements-api.txt`, ajouter dans la section `=== Backend API ===` (avec les autres paquets déjà là) :

```
openpyxl==3.1.5
```

- [ ] **Step 2: Générateur Excel**

Créer `api_backend/backend_app/utils/dossier_excel_export.py` :

```python
# api_backend/backend_app/utils/dossier_excel_export.py
import io
from typing import Any, Dict
from openpyxl import Workbook


def build_dossier_excel(dossier: Dict[str, Any]) -> bytes:
    """
    Un onglet par domaine PRESENT dans le dossier (dict.get, jamais un
    acces direct par cle - dossier_toxico/historique_spirituel sont
    absents pour medecin/nurse, chantier perimetre medical 2026-09-22 -
    ce fichier ne doit jamais casser cette garantie ni la contourner).
    """
    wb = Workbook()
    wb.remove(wb.active)

    patient = dossier.get("patient") or {}
    ws_patient = wb.create_sheet("Patient")
    ws_patient.append(["Champ", "Valeur"])
    for key in ("code_patient", "first_name", "last_name", "birth_date", "gender", "contact_phone"):
        ws_patient.append([key, patient.get(key)])

    if dossier.get("historique_medical") is not None:
        ws = wb.create_sheet("Historique medical")
        ws.append(["Date", "Motif", "Diagnostic"])
        for r in dossier["historique_medical"]:
            ws.append([r.get("consultation_date") or r.get("created_at"), r.get("motif_code"), r.get("diagnosis")])

    if dossier.get("prescriptions") is not None:
        ws = wb.create_sheet("Prescriptions")
        ws.append(["Médicament", "Dosage", "Fréquence", "Début", "Fin"])
        for p in dossier["prescriptions"]:
            ws.append([p.get("medication"), p.get("dosage"), p.get("frequency"), p.get("start_date"), p.get("end_date")])

    if dossier.get("historique_labo") is not None:
        ws = wb.create_sheet("Labo")
        ws.append(["Date", "Examen", "Statut"])
        for r in dossier["historique_labo"]:
            ws.append([r.get("test_date"), r.get("examen_name"), r.get("status")])

    if dossier.get("dossier_toxico") is not None:
        ws = wb.create_sheet("Toxicologie")
        toxico = dossier["dossier_toxico"]
        ws.append(["Champ", "Valeur"])
        for key in ("substance", "current_phase", "admission_date"):
            ws.append([key, toxico.get(key)])

    if dossier.get("historique_spirituel") is not None:
        ws = wb.create_sheet("Spirituel")
        ws.append(["Date", "Type", "Intervenant"])
        for r in dossier["historique_spirituel"]:
            ws.append([r.get("consultation_date"), r.get("type_consultation"), r.get("created_by_name")])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
```

- [ ] **Step 3: Template PDF dossier**

Créer `api_backend/backend_app/utils/templates/dossier_export_template.html` :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Dossier patient</title>
    <style>
        @page { size: A4; margin: 2cm; @bottom-right { content: "Page " counter(page) " sur " counter(pages); font-size: 9pt; color: #666; } }
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; font-size: 10pt; line-height: 1.4; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; margin-bottom: 15px; }
        .hospital-info h1 { margin: 0; color: #2c3e50; font-size: 16pt; }
        .hospital-info p { margin: 2px 0; font-size: 9pt; }
        .logo { max-width: 120px; max-height: 60px; }
        .section-title { font-size: 12pt; font-weight: bold; color: #2c3e50; margin-top: 20px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th { background-color: #2c3e50; color: white; text-align: left; padding: 5px; font-size: 9pt; }
        td { padding: 5px; border-bottom: 1px solid #ddd; font-size: 9pt; }
    </style>
</head>
<body>

    {% include '_pdf_header.html' %}

    <div class="section-title">Patient</div>
    <p><strong>{{ patient.first_name }} {{ patient.last_name }}</strong> — {{ patient.code_patient }}</p>

    {% if historique_medical is not none %}
    <div class="section-title">Historique médical</div>
    <table>
        <thead><tr><th>Date</th><th>Motif</th><th>Diagnostic</th></tr></thead>
        <tbody>
            {% for r in historique_medical %}
            <tr><td>{{ r.consultation_date or r.created_at }}</td><td>{{ r.motif_code }}</td><td>{{ r.diagnosis }}</td></tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

    {% if prescriptions is not none %}
    <div class="section-title">Prescriptions</div>
    <table>
        <thead><tr><th>Médicament</th><th>Dosage</th><th>Fréquence</th><th>Début</th><th>Fin</th></tr></thead>
        <tbody>
            {% for p in prescriptions %}
            <tr><td>{{ p.medication }}</td><td>{{ p.dosage }}</td><td>{{ p.frequency }}</td><td>{{ p.start_date }}</td><td>{{ p.end_date }}</td></tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

    {% if historique_labo is not none %}
    <div class="section-title">Laboratoire</div>
    <table>
        <thead><tr><th>Date</th><th>Examen</th><th>Statut</th></tr></thead>
        <tbody>
            {% for r in historique_labo %}
            <tr><td>{{ r.test_date }}</td><td>{{ r.examen_name }}</td><td>{{ r.status }}</td></tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

    {% if dossier_toxico is not none %}
    <div class="section-title">Toxicologie</div>
    <p>Substance : {{ dossier_toxico.substance }} — Phase : {{ dossier_toxico.current_phase }}</p>
    {% endif %}

    {% if historique_spirituel is not none %}
    <div class="section-title">Suivi spirituel</div>
    <table>
        <thead><tr><th>Date</th><th>Type</th><th>Intervenant</th></tr></thead>
        <tbody>
            {% for r in historique_spirituel %}
            <tr><td>{{ r.consultation_date }}</td><td>{{ r.type_consultation }}</td><td>{{ r.created_by_name }}</td></tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

</body>
</html>
```

- [ ] **Step 4: Endpoint d'export**

Dans `api_backend/backend_app/routes/patient_dossier/patient_dossier_endpoint.py`, la ligne d'import FastAPI actuelle (ligne 3) est `from fastapi import APIRouter, Depends, HTTPException` — `Query` n'y est pas encore, la remplacer par :

```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

Puis ajouter en tête de fichier (avec les autres imports) :

```python
from datetime import datetime
from fastapi.responses import Response
from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from api_backend.backend_app.utils.pdf_header import get_pdf_header_context
from api_backend.backend_app.utils.dossier_excel_export import build_dossier_excel
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository
```

Puis ajouter la route :

```python
@router.get(
    "/{patient_id}/dossier/export",
    dependencies=[Depends(role_required(
        "medecin", "nurse", "psychologist", "spiritualcounsellor",
        "toxicomanager", "laborantin", "assistant", "admin", "promoteur",
    ))],
)
def export_patient_dossier(
    patient_id: int,
    format: str = Query(..., regex="^(pdf|excel)$"),
    ctrl: PatientDossierController = Depends(get_patient_dossier_controller),
    db: Session = Depends(get_db),
):
    try:
        dossier = ctrl.get_full_dossier(patient_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if format == "excel":
        excel_bytes = build_dossier_excel(dossier)
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=dossier_{patient_id}.xlsx"},
        )

    config_ctrl = ConfigController(repo=ConfigRepository(db))
    header_ctx = get_pdf_header_context(config_ctrl)

    pdf_bytes = render_pdf_from_template('dossier_export_template.html', {
        **header_ctx,
        "patient": dossier.get("patient") or {},
        "historique_medical": dossier.get("historique_medical"),
        "prescriptions": dossier.get("prescriptions"),
        "historique_labo": dossier.get("historique_labo"),
        "dossier_toxico": dossier.get("dossier_toxico"),
        "historique_spirituel": dossier.get("historique_spirituel"),
        "date_impression": datetime.now().strftime("%d/%m/%Y à %H:%M"),
    })
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=dossier_{patient_id}.pdf"},
    )
```

(La même liste de rôles que la route `GET /{patient_id}/dossier` déjà existante dans ce fichier — copier exactement, ne pas la redéfinir différemment.)

- [ ] **Step 5: Tests — garantie de cloisonnement medecin/nurse préservée dans l'export**

Créer `tests/test_dossier_export.py` :

```python
# tests/test_dossier_export.py
from datetime import date

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patient_dossier import patient_dossier_endpoint
from models.medical_record import MedicalRecord
from models.toxico import ToxicoDossier
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "Correct123!"


def test_export_dossier_pdf_medecin_ne_contient_pas_toxico(db_session, api_client):
    """Chantier exports (2026-09-23) : la garantie de cloisonnement du
    chantier perimetre medical (2026-09-22) doit se propager au fichier
    exporte, pas seulement a l'ecran."""
    medecin = create_test_user(db_session, "export_dossier_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="ExportDossierMulti")
    db_session.flush()

    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
    db_session.add(ToxicoDossier(patient_id=patient_id, admission_date=date(2026, 1, 10), substance="Alcool"))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "export_dossier_medecin", TEST_PASSWORD)

    resp_pdf = client.get(f"/patients/{patient_id}/dossier/export?format=pdf", headers=headers)
    resp_excel = client.get(f"/patients/{patient_id}/dossier/export?format=excel", headers=headers)

    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert b"Toxicologie" not in resp_pdf.content

    assert resp_excel.status_code == 200
    assert resp_excel.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_export_dossier_admin_contient_toxico(db_session, api_client):
    """Non-regression : seul medecin/nurse est concerne par le
    cloisonnement, admin garde tout."""
    admin = create_test_user(db_session, "export_dossier_admin", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="ExportDossierAdminMulti")
    db_session.flush()

    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
    db_session.add(ToxicoDossier(patient_id=patient_id, admission_date=date(2026, 1, 10), substance="Alcool"))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "export_dossier_admin", TEST_PASSWORD)

    resp_pdf = client.get(f"/patients/{patient_id}/dossier/export?format=pdf", headers=headers)

    assert resp_pdf.status_code == 200
    assert b"Toxicologie" in resp_pdf.content
```

- [ ] **Step 6: Lancer les tests**

Run: `python -m pytest tests/test_dossier_export.py -v`
Expected: 2 passed.

- [ ] **Step 7: Commit**

(Pas de commit — règle immuable de ce projet.)

---

### Task 8: Export dossier médical — frontend (bouton)

**Files:**
- Modify: `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue`

**Interfaces:**
- Consumes: aucune interface des tâches précédentes (appel API direct, pas de nouveau composant partagé — un seul déclencheur, pas de filtre de période à ce niveau).

- [ ] **Step 1: Ajouter le bouton d'export**

Dans `PatientDetailView.vue`, repérer le composant `<PatientHeader :patient="dossierStore.patientSummary" @back="goBack" />` en tête de template. Ajouter juste après, un bloc dédié aux actions d'export (deux boutons, PDF et Excel) :

```html
<div class="flex justify-end gap-2 px-1">
  <button @click="exportDossier('pdf')" :disabled="isExportingDossier"
          class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition disabled:opacity-50">
    {{ t('export.confirm') }} PDF
  </button>
  <button @click="exportDossier('excel')" :disabled="isExportingDossier"
          class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition disabled:opacity-50">
    {{ t('export.confirm') }} Excel
  </button>
</div>
```

Dans le `<script setup>` :

```javascript
import api from '@/services/api';

const isExportingDossier = ref(false);

const exportDossier = async (format) => {
  isExportingDossier.value = true;
  try {
    const response = await api.get(`/patients/${route.params.id}/dossier/export`, {
      params: { format },
      responseType: 'blob',
    });
    const mimeType = format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    const blob = new Blob([response.data], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `dossier_${route.params.id}.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
    link.click();
    window.URL.revokeObjectURL(url);
  } finally {
    isExportingDossier.value = false;
  }
};
```

(Vérifier si `ref`, `api`, et `route` — `useRoute()` — sont déjà importés/déclarés dans ce fichier avant d'ajouter des doublons ; ce composant charge déjà le patient via `route.params.id` d'après `fetchDossierComplete`, donc `route` existe déjà quelque part dans le `<script setup>`.)

- [ ] **Step 2: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

- [ ] **Step 3: Commit**

(Pas de commit — règle immuable de ce projet.)

---

## Vérification finale (hors tâches, à la charge du contrôleur après la dernière tâche)

- Relancer la suite complète (`python -m pytest tests/ -q`) et confirmer qu'aucun nouvel échec n'apparaît en dehors des 9 échecs pré-existants déjà documentés dans `docs/superpowers/SUIVI-AVANCEMENT.md`.
- Vérifier `pip install -r requirements-api.txt --dry-run` et `pip install -r requirements-desktop.txt --dry-run` après le déplacement d'`openpyxl` (Task 7) — aucune erreur de résolution.
- Vérification manuelle (ou demandée à l'utilisateur) : changer le nom/logo dans `SystemConfig.vue`, télécharger une facture caisse ET un export patients PDF ET un export dossier PDF — les trois doivent refléter le changement.
