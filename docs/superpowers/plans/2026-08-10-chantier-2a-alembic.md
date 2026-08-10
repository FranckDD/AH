# Chantier 2a — Alembic + migration de référence — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adopter Alembic sur la base PostgreSQL existante et déjà peuplée, avec une migration de référence marquée comme déjà appliquée (`stamp`, jamais exécutée), pour que toute évolution de schéma future soit versionnée et reproductible.

**Architecture:** Dossier `alembic/` dédié à la racine (distinct de `migrations/`, qui garde son script de synchronisation SQLite sans rapport). `env.py` importe `DATABASE_URL` depuis `api_backend.backend_app.config` et les 19 modèles réels via `models/__init__.py` étendu, pour que `Base.metadata` reflète le schéma complet.

**Tech Stack:** Alembic, SQLAlchemy, PostgreSQL.

## Global Constraints

- La migration de référence ne doit **jamais être exécutée** (`alembic upgrade`) — les tables existent déjà en base avec des données réelles. Seul `alembic stamp head` l'enregistre comme point de départ.
- `requirements.txt` est en plein travail en cours (remplacé par un `pip freeze` complet, sans base commune avec `HEAD`) — `alembic==1.18.5` y est ajouté dans la copie de travail, **non commité**, même traitement que `slowapi` au chantier 0.
- `App.py` et `medical.py` sous `models/` sont vides de contenu SQLAlchemy — explicitement exclus des imports.

---

## Task 1: Dépendance et initialisation

**Files:**
- Modify: `requirements.txt` (copie de travail uniquement, non commité)
- Create: `alembic/` (généré par `alembic init`), `alembic.ini`

**Interfaces:**
- Consumes: rien
- Produces: structure `alembic/` standard (`env.py`, `script.py.mako`, `versions/`), consommée par les tâches suivantes

- [ ] **Step 1: Vérifier qu'Alembic est disponible**

```bash
python -c "import alembic; print(alembic.__version__)"
```

Attendu : `1.18.5` (déjà installé dans cet environnement).

- [ ] **Step 2: Ajouter la ligne à `requirements.txt` (copie de travail, non commitée)**

Dans `requirements.txt`, `alembic` se place avant `altgraph` (première ligne du fichier après le BOM). Remplacer :

```
﻿altgraph==0.17.4
```

par :

```
﻿alembic==1.18.5
altgraph==0.17.4
```

- [ ] **Step 3: Initialiser Alembic**

```bash
cd "c:/Users/DD/Desktop/Project Stage/ah2_v2/AH2"
alembic init alembic
```

Attendu : création de `alembic.ini` à la racine, et du dossier `alembic/` avec `env.py`, `script.py.mako`, `README`, `versions/` (vide).

- [ ] **Step 4: Vérifier la structure créée**

```bash
ls alembic/
cat alembic.ini | head -5
```

Attendu : les fichiers standard sont présents.

- [ ] **Step 5: Pas de commit à cette étape** — `alembic.ini` et `alembic/` seront commités à la fin de la Task 4, une fois `env.py` correctement configuré (éviter un commit intermédiaire avec une config par défaut non fonctionnelle).

---

## Task 2: Étendre `models/__init__.py`

**Files:**
- Modify: `models/__init__.py` (fichier propre)

**Interfaces:**
- Consumes: rien
- Produces: `models.__init__` expose les 19 classes de modèles réelles, consommé par `alembic/env.py` (Task 4) via `import models`

- [ ] **Step 1: Lire le contenu actuel**

```bash
cat models/__init__.py
```

Attendu :
```python
# models/__init__.py
from .patient        import Patient
from .medical_record import MedicalRecord
from .prescription   import Prescription
# etc.
```

- [ ] **Step 2: Réécrire le fichier avec les 19 modèles réels**

Remplacer tout le contenu par :

```python
# models/__init__.py
from .patient import Patient
from .medical_record import MedicalRecord
from .prescription import Prescription
from .application_role import ApplicationRole
from .appointment import Appointment
from .audit import AuditAccess, AuditUserAction
from .caisse import Caisse
from .caisse_item import CaisseItem
from .consultation_spirituelle import ConsultationSpirituel
from .lab import Examen, Parametre, ReferenceRange, LabResult, LabResultDetail
from .medical_speciality import MedicalSpecialty
from .organization_config import OrganizationConfig
from .paiement_echelonne import PaiementEchelonne
from .pharmacy import Pharmacy
from .prayer_book_type import PrayerBookType
from .retrait import CaisseRetrait
from .stock_movement import StockMovement
from .toxico import ToxicoPhaseEnum, ToxicoDossier, ToxicoPhaseHistory, ToxicoEvaluation
from .user import User
```

(`App.py` et `medical.py` volontairement exclus — vides de contenu SQLAlchemy.)

- [ ] **Step 3: Vérifier que le module se charge sans erreur**

```bash
python -c "import models; from models.database import Base; print(len(Base.metadata.tables))"
```

Attendu : pas d'exception, un nombre de tables cohérent avec les 19 modèles (certains modèles définissent plusieurs classes/tables, par exemple `lab.py` et `toxico.py` — le nombre de tables sera donc supérieur à 19).

- [ ] **Step 4: Commit**

```bash
git add models/__init__.py
git commit -m "chore: importer les 19 modeles reels dans models/__init__.py (chantier 2a)

Seuls 3 des 21 fichiers de models/ etaient importes (Patient,
MedicalRecord, Prescription). App.py et medical.py sont vides de
contenu SQLAlchemy, exclus. Necessaire pour qu'Alembic voie le
schema complet via Base.metadata lors de l'autogeneration.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Configurer `alembic/env.py`

**Files:**
- Modify: `alembic/env.py` (généré par Task 1, propre)

**Interfaces:**
- Consumes: `DATABASE_URL` de `api_backend.backend_app.config`, `Base.metadata` de `models.database` (via `models/__init__.py`, Task 2)
- Produces: `target_metadata` correctement configuré, consommé par `alembic revision --autogenerate` (Task 4)

- [ ] **Step 1: Localiser les lignes par défaut à remplacer**

```bash
grep -n "config = context.config\|target_metadata = None" alembic/env.py
```

Attendu : deux lignes trouvées (le template standard d'Alembic).

- [ ] **Step 2: Ajouter le chemin racine et la config `DATABASE_URL`**

Remplacer :

```python
config = context.config
```

par :

```python
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api_backend.backend_app.config import DATABASE_URL

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)
```

- [ ] **Step 3: Câbler `target_metadata`**

Remplacer :

```python
target_metadata = None
```

par :

```python
import models  # noqa: E402 - importe les 19 modeles reels, enregistre les tables sur Base.metadata
from models.database import Base

target_metadata = Base.metadata
```

- [ ] **Step 4: Vérifier qu'Alembic peut charger la configuration**

```bash
alembic current
```

Attendu : ne lève pas d'exception (peut afficher qu'aucune révision n'est encore appliquée — normal, aucune migration n'existe encore).

- [ ] **Step 5: Commit**

```bash
git add alembic.ini alembic/
git commit -m "chore: initialiser Alembic, env.py cable sur config.py et models (chantier 2a)

Dossier alembic/ dedie, distinct de migrations/ (script de
synchronisation SQLite sans rapport). env.py importe DATABASE_URL
depuis config.py (source unique) et les 19 modeles reels pour que
Base.metadata reflete le schema complet.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Migration de référence

**Files:**
- Create: `alembic/versions/<hash>_baseline.py` (généré automatiquement)

**Interfaces:**
- Consumes: `target_metadata` (Task 3), état actuel de la base PostgreSQL
- Produces: révision Alembic baseline, marquée comme appliquée

- [ ] **Step 1: Générer la migration par autogénération**

```bash
alembic revision --autogenerate -m "baseline"
```

Attendu : un nouveau fichier apparaît dans `alembic/versions/`. La sortie console peut lister des différences détectées (colonnes/tables sans modèle correspondant, ou l'inverse) — **normal**, la base et les modèles ont évolué séparément pendant des mois. Ne pas corriger ces différences dans ce chantier (hors périmètre, voir spec).

- [ ] **Step 2: Lire le fichier généré pour confirmer qu'il correspond à un schéma cohérent**

```bash
cat alembic/versions/*baseline*.py
```

Vérifier que le fichier contient des opérations `op.create_table(...)` pour les tables principales (`patients`, `users`, `application_roles`, etc.) — confirme que l'autogénération a bien vu le schéma.

- [ ] **Step 3: Marquer la base comme déjà à cette révision (ne jamais `upgrade`)**

```bash
alembic stamp head
```

Attendu : aucune erreur. Cette commande **n'exécute aucune opération SQL du fichier de migration** — elle insère seulement la révision dans la table `alembic_version`.

- [ ] **Step 4: Vérifier**

```bash
alembic current
```

Attendu : affiche la révision baseline comme courante.

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "SELECT * FROM alembic_version;"
```

Attendu : une ligne, avec l'identifiant de la révision baseline.

- [ ] **Step 5: Confirmer qu'aucune table n'a été modifiée par erreur**

```bash
PGPASSWORD='<mot_de_passe_postgres_actuel>' "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d AH2 -c "SELECT count(*) FROM patients;"
```

Attendu : `102` (ou le nombre actuel, inchangé depuis avant ce chantier — confirme qu'aucune donnée n'a été touchée).

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/
git commit -m "chore: migration de reference (baseline), marquee comme appliquee (chantier 2a)

Genere par autogeneration puis 'alembic stamp head' - jamais
executee, la base contient deja ce schema avec des donnees reelles.
Point de depart pour toute evolution de schema future, versionnee
via alembic revision --autogenerate + alembic upgrade head.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Vérification finale

**Files:** aucun (vérification uniquement)

- [ ] **Step 1: L'API démarre toujours normalement**

```bash
PYTHONIOENCODING=utf-8 uvicorn api_backend.backend_app.main:app --port 8000 &
sleep 5
curl -s -o /dev/null -w "healthcheck: %{http_code}\n" http://127.0.0.1:8000/health
```

Attendu : `200` (Alembic est un outil hors-ligne, aucun impact sur le chemin d'exécution de l'API).

- [ ] **Step 2: Suite de tests complète**

```bash
pytest tests/ -v
```

Attendu : même résultat qu'avant ce chantier (les échecs pré-existants et non liés restent identiques).

- [ ] **Step 3: Confirmer qu'une nouvelle autogénération à blanc ne détecte plus rien de nouveau**

```bash
alembic revision --autogenerate -m "verification_vide"
cat alembic/versions/*verification_vide*.py
```

Attendu : le fichier généré ne contient que `pass` dans `upgrade()`/`downgrade()` (aucune différence entre les modèles et la base, puisque la baseline vient d'être stampée avec exactement cet état).

- [ ] **Step 4: Supprimer ce fichier de vérification (ne pas le committer)**

```bash
rm alembic/versions/*verification_vide*.py
```

- [ ] **Step 5: Récapitulatif**

Confirmer un par un :
- [ ] Alembic initialisé, `env.py` cablé sur `config.py` et `models`
- [ ] `models/__init__.py` importe les 19 modèles réels
- [ ] Migration baseline générée et stampée, jamais exécutée
- [ ] `alembic_version` contient une ligne cohérente
- [ ] Données de la base inchangées (`patients` toujours à son compte d'origine)
- [ ] API et suite de tests fonctionnent comme avant ce chantier
- [ ] Une autogénération à blanc ne détecte plus de différence (baseline fidèle)
