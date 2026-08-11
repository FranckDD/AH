# Chantier 2e — Piste d'audit non silencieuse — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer les 11 `except Exception: pass` entourant des écritures d'audit par un `logger.exception(...)`, sur 6 contrôleurs, sans changer le comportement métier (un incident d'audit ne bloque jamais l'opération).

**Architecture:** Modification mécanique et uniforme, site par site, isolée du travail en cours de l'utilisateur sur chacun des 6 fichiers via injection directe dans l'index à partir de `HEAD`.

**Tech Stack:** Python, `logging` standard, pytest.

## Global Constraints

- Tous les 6 fichiers portent du travail en cours substantiel. Chaque modification doit être isolée via la technique établie (extraction depuis `HEAD`, transformation, injection dans l'index) — jamais de `git add` brut sur ces fichiers.
- Ne pas toucher aux 2 sites de `change_user_password()` (`auth_controller.py`) — cette méthode n'existe pas sur `HEAD`.
- Le pattern reste `except Exception: <log>` — ne jamais faire propager l'exception (préserve le comportement non-bloquant existant).
- **Ajustement par rapport à la spec** : un test représentatif par fichier (pas par site), le site le plus simple à isoler sans reconstruire un graphe d'objets profond. La couverture exhaustive des 11 sites est assurée par la vérification finale par `grep` (Task 7) et par la relecture du diff isolé de chaque commit.

---

## Task 1: `controller/auth_controller.py` (2 sites)

**Files:**
- Modify: `controller/auth_controller.py` (isolation requise)
- Test: `tests/test_audit_logging.py` (nouveau)

**Interfaces:**
- Consumes: rien
- Produces: rien

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_audit_logging.py` :

```python
# tests/test_audit_logging.py
import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock


def test_auth_controller_logs_when_audit_fails_on_login_error(caplog):
    from controller.auth_controller import AuthController

    ctrl = AuthController.__new__(AuthController)  # bypass __init__ (evite la cascade de sous-repos)
    ctrl.session = MagicMock()
    ctrl.user_repo = MagicMock()
    ctrl.user_repo.get_user_by_username.side_effect = RuntimeError("DB indisponible")
    ctrl.audit_repo = MagicMock()
    ctrl.audit_repo.log_access.side_effect = Exception("audit aussi en echec")

    with caplog.at_level(logging.ERROR):
        result = ctrl.authenticate("admin_test", "peu importe")

    assert result is None  # ne doit jamais lever, comportement inchange
    assert any("audit" in r.message.lower() for r in caplog.records)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_audit_logging.py -v
```

Attendu : échoue — aucun `logger` n'existe encore dans `auth_controller.py`, `caplog` ne capture rien.

- [ ] **Step 3: Appliquer les correctifs dans la copie de travail**

Ajouter l'import et le logger (après les imports existants, avant la classe) :

```python
import logging

logger = logging.getLogger(__name__)
```

Remplacer :

```python
            self.current_user = user
            try:
                self.audit_repo.log_access(user, "LOGIN_SUCCESS", details="Connexion via API")
            except Exception: pass
```

par :

```python
            self.current_user = user
            try:
                self.audit_repo.log_access(user, "LOGIN_SUCCESS", details="Connexion via API")
            except Exception:
                logger.exception("Échec de l'écriture d'audit")
```

Remplacer :

```python
        except Exception as e:
            try:
                self.audit_repo.log_access(None, "LOGIN_FAILURE", details=f"User: {username}. Erreur: {str(e)}")
            except Exception: pass
```

par :

```python
        except Exception as e:
            try:
                self.audit_repo.log_access(None, "LOGIN_FAILURE", details=f"User: {username}. Erreur: {str(e)}")
            except Exception:
                logger.exception("Échec de l'écriture d'audit")
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_audit_logging.py -v
```

Attendu : `PASS`.

- [ ] **Step 5: Isoler et stager (le fichier porte du travail en cours ailleurs)**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:controller/auth_controller.py > "$SCRATCH/auth_controller_base_2e.py"
python - <<'PYEOF'
path = r"C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad/auth_controller_base_2e.py"
content = open(path, encoding="utf-8").read()

old_import = '''# controllers/auth_controller.py
import os'''
new_import = '''# controllers/auth_controller.py
import os
import logging

logger = logging.getLogger(__name__)'''

old1 = '''            self.current_user = user
            try:
                self.audit_repo.log_access(user, "LOGIN_SUCCESS", details="Connexion via API")
            except Exception: pass'''
new1 = '''            self.current_user = user
            try:
                self.audit_repo.log_access(user, "LOGIN_SUCCESS", details="Connexion via API")
            except Exception:
                logger.exception("Échec de l'écriture d'audit")'''

old2 = '''        except Exception as e:
            try:
                self.audit_repo.log_access(None, "LOGIN_FAILURE", details=f"User: {username}. Erreur: {str(e)}")
            except Exception: pass'''
new2 = '''        except Exception as e:
            try:
                self.audit_repo.log_access(None, "LOGIN_FAILURE", details=f"User: {username}. Erreur: {str(e)}")
            except Exception:
                logger.exception("Échec de l'écriture d'audit")'''

for old, new in [(old_import, new_import), (old1, new1), (old2, new2)]:
    assert old in content, f"pattern introuvable: {old[:50]}"
    content = content.replace(old, new)

open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/auth_controller_base_2e.py")
git update-index --cacheinfo 100644,$BLOB,controller/auth_controller.py
git diff --cached -- controller/auth_controller.py
```

Vérifier que le diff ne contient que les 3 hunks (import+logger, LOGIN_SUCCESS, LOGIN_FAILURE), rien sur le reste du fichier (notamment pas `change_user_password`).

- [ ] **Step 6: Commit**

```bash
git add tests/test_audit_logging.py
git commit -m "fix(security): logger les echecs d'audit dans auth_controller (OPS-01, 2/11)

except Exception: pass -> logger.exception(...) sur LOGIN_SUCCESS et
LOGIN_FAILURE. Comportement inchange (un incident d'audit ne bloque
jamais l'authentification), mais l'echec devient visible.

change_user_password() (PASSWORD_CHANGE_*) non touche : absent de
HEAD, deja identifie au chantier SEC-09.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: `controller/caisse_controller.py` (1 site)

**Files:**
- Modify: `controller/caisse_controller.py` (isolation requise)
- Test: `tests/test_audit_logging.py` (étendu)

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_audit_logging.py` :

```python
def test_caisse_controller_logs_when_audit_fails_on_cancel(caplog):
    from controller.caisse_controller import CaisseController

    repo = MagicMock()
    repo.cancel_transaction.return_value = MagicMock()
    user = MagicMock()
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = CaisseController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        tx = ctrl.cancel_transaction(transaction_id=1)

    assert tx is not None  # ne doit jamais lever
    assert any("audit" in r.message.lower() for r in caplog.records)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_audit_logging.py::test_caisse_controller_logs_when_audit_fails_on_cancel -v
```

Attendu : échoue (aucun logger dans `caisse_controller.py`).

- [ ] **Step 3: Appliquer les correctifs dans la copie de travail**

Ajouter en tête de fichier (après les imports existants) :

```python
import logging

logger = logging.getLogger(__name__)
```

Remplacer :

```python
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Transaction",
                    action_performed="CANCEL",
                    resource_id=transaction_id,
                    details="Annulation transaction financière"
                )
            except Exception: pass
```

par :

```python
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Transaction",
                    action_performed="CANCEL",
                    resource_id=transaction_id,
                    details="Annulation transaction financière"
                )
            except Exception:
                logger.exception("Échec de l'écriture d'audit")
```

**Note :** la copie de travail peut avoir un `action_performed="CANCEL",` sans le commentaire `# Action critique !` présent sur `HEAD` — appliquer l'édition sur le texte réellement présent dans la copie de travail à ce moment (relire le fichier avant d'éditer), l'isolation à l'étape 5 se base sur `HEAD` séparément.

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_audit_logging.py -v
```

Attendu : tous les tests passent.

- [ ] **Step 5: Isoler et stager**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:controller/caisse_controller.py > "$SCRATCH/caisse_controller_base_2e.py"
python - <<'PYEOF'
path = r"C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad/caisse_controller_base_2e.py"
content = open(path, encoding="utf-8").read()

old_import = "from models.consultation_spirituelle import ConsultationSpirituel"
new_import = "from models.consultation_spirituelle import ConsultationSpirituel\n\nimport logging\n\nlogger = logging.getLogger(__name__)"
assert old_import in content, "ancre d'import introuvable"
content = content.replace(old_import, new_import)

old = '''                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Transaction",
                    action_performed="CANCEL", # Action critique !
                    resource_id=transaction_id,
                    details="Annulation transaction financière"
                )
            except Exception: pass'''
new = '''                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Transaction",
                    action_performed="CANCEL", # Action critique !
                    resource_id=transaction_id,
                    details="Annulation transaction financière"
                )
            except Exception:
                logger.exception("Échec de l'écriture d'audit")'''
assert old in content, "pattern introuvable"
content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/caisse_controller_base_2e.py")
git update-index --cacheinfo 100644,$BLOB,controller/caisse_controller.py
git diff --cached -- controller/caisse_controller.py
```

Vérifier que le diff ne contient que l'ajout du logger et ce hunk.

- [ ] **Step 6: Commit**

```bash
git add tests/test_audit_logging.py
git commit -m "fix(security): logger les echecs d'audit dans caisse_controller (OPS-01, 3/11)

except Exception: pass -> logger.exception(...) sur l'annulation de
transaction (CANCEL).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: `controller/medical_controller.py` (3 sites)

**Files:**
- Modify: `controller/medical_controller.py` (isolation requise, logger déjà présent via `self.logger`)
- Test: `tests/test_audit_logging.py` (étendu)

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter :

```python
def test_medical_controller_logs_when_audit_fails_on_delete(caplog):
    from controller.medical_controller import MedicalRecordController

    repo = MagicMock()
    repo.delete.return_value = True
    user = MagicMock()
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = MedicalRecordController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        result = ctrl.delete_record(record_id=1)

    assert result is True
    assert any("audit" in r.message.lower() for r in caplog.records)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_audit_logging.py::test_medical_controller_logs_when_audit_fails_on_delete -v
```

- [ ] **Step 3: Appliquer les correctifs dans la copie de travail (3 sites, `self.logger` déjà disponible)**

Remplacer (CREATE) :

```python
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="CREATE",
```
... jusqu'à son `except Exception: pass` correspondant, par la même structure avec `except Exception: self.logger.exception("Échec de l'écriture d'audit")`. Faire de même pour les blocs `UPDATE` et `DELETE`.

Concrètement, pour chacun des 3 blocs, remplacer la ligne :

```python
            except Exception: pass
```

(celle qui suit immédiatement un appel `self.audit_repo.log_user_action(...)`) par :

```python
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_audit_logging.py -v
```

- [ ] **Step 5: Isoler et stager**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:controller/medical_controller.py > "$SCRATCH/medical_controller_base_2e.py"
python - <<'PYEOF'
path = r"C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad/medical_controller_base_2e.py"
content = open(path, encoding="utf-8").read()

replacements = [
    (
        '''                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="CREATE",
                    resource_id=rec_id,
                    details=f"Patient ID: {pat_id}. Motif: {data.get('motif_code')}" # type: ignore
                )
            except Exception: pass''',
        '''                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="CREATE",
                    resource_id=rec_id,
                    details=f"Patient ID: {pat_id}. Motif: {data.get('motif_code')}" # type: ignore
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")'''
    ),
    (
        '''                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="UPDATE",
                    resource_id=record_id,
                    new_values=data # Log des champs modifiés
                )
            except Exception: pass''',
        '''                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="UPDATE",
                    resource_id=record_id,
                    new_values=data # Log des champs modifiés
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")'''
    ),
    (
        '''                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="DELETE",
                    resource_id=record_id
                )
            except Exception: pass''',
        '''                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="DELETE",
                    resource_id=record_id
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")'''
    ),
]
for old, new in replacements:
    assert old in content, f"pattern introuvable: {old[:60]}"
    content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/medical_controller_base_2e.py")
git update-index --cacheinfo 100644,$BLOB,controller/medical_controller.py
git diff --cached -- controller/medical_controller.py
```

Vérifier que le diff contient exactement 3 hunks.

- [ ] **Step 6: Commit**

```bash
git add tests/test_audit_logging.py
git commit -m "fix(security): logger les echecs d'audit dans medical_controller (OPS-01, 6/11)

except Exception: pass -> self.logger.exception(...) sur CREATE,
UPDATE, DELETE (dossier medical). Logger d'instance deja present,
reutilise.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: `controller/patient_controller.py` (1 site)

**Files:**
- Modify: `controller/patient_controller.py` (isolation requise, `self.logger` déjà présent)
- Test: `tests/test_audit_logging.py` (étendu)

- [ ] **Step 1: Écrire le test qui échoue**

```python
def test_patient_controller_logs_when_audit_fails_on_soft_delete(caplog):
    from controller.patient_controller import PatientController

    repo = MagicMock()
    repo.session = MagicMock()
    repo.delete_patient.return_value = True
    user = MagicMock()
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = PatientController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        result = ctrl.delete_patient(patient_id=1)

    assert result is True
    assert any("audit" in r.message.lower() for r in caplog.records)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_audit_logging.py::test_patient_controller_logs_when_audit_fails_on_soft_delete -v
```

- [ ] **Step 3: Appliquer le correctif dans la copie de travail**

Remplacer :

```python
                try:
                    self.audit_repo.log_user_action(
                        current_user=self.user,
                        resource_type="Patient",
                        action_performed="SOFT_DELETE",
                        resource_id=patient_id
                    )
                except Exception: pass
```

par :

```python
                try:
                    self.audit_repo.log_user_action(
                        current_user=self.user,
                        resource_type="Patient",
                        action_performed="SOFT_DELETE",
                        resource_id=patient_id
                    )
                except Exception:
                    self.logger.exception("Échec de l'écriture d'audit")
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_audit_logging.py -v
```

- [ ] **Step 5: Isoler et stager**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:controller/patient_controller.py > "$SCRATCH/patient_controller_base_2e.py"
python - <<'PYEOF'
path = r"C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad/patient_controller_base_2e.py"
content = open(path, encoding="utf-8").read()
old = '''            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Patient",
                    action_performed="SOFT_DELETE",
                    resource_id=patient_id
                )
            except Exception: pass'''
new = '''            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Patient",
                    action_performed="SOFT_DELETE",
                    resource_id=patient_id
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")'''
assert old in content, "pattern introuvable"
content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/patient_controller_base_2e.py")
git update-index --cacheinfo 100644,$BLOB,controller/patient_controller.py
git diff --cached -- controller/patient_controller.py
```

**Note :** l'indentation exacte du `try:`/`except` sur `HEAD` est à 12 espaces (pas 16 comme dans un extrait vu en copie de travail) — vérifier l'indentation réelle de `HEAD` via la commande `git show HEAD:controller/patient_controller.py | sed -n '125,140p'` avant de construire le remplacement si l'`assert` échoue, et ajuster le nombre d'espaces en conséquence.

- [ ] **Step 6: Commit**

```bash
git add tests/test_audit_logging.py
git commit -m "fix(security): logger l'echec d'audit dans patient_controller (OPS-01, 7/11)

except Exception: pass -> self.logger.exception(...) sur SOFT_DELETE.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: `controller/pharmacy_controller.py` (1 helper, 4 usages)

**Files:**
- Modify: `controller/pharmacy_controller.py` (isolation requise)
- Test: `tests/test_audit_logging.py` (étendu)

**Interfaces:**
- Consumes: rien
- Produces: rien — `_audit()` reste un détail d'implémentation privé du contrôleur

- [ ] **Step 1: Écrire le test qui échoue**

```python
def test_pharmacy_controller_logs_when_audit_helper_fails(caplog):
    from controller.pharmacy_controller import PharmacyController

    repo = MagicMock()
    user = MagicMock()
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = PharmacyController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        ctrl._audit(action="CREATE", resource_id=1)  # ne doit pas lever

    assert any("audit" in r.message.lower() for r in caplog.records)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_audit_logging.py::test_pharmacy_controller_logs_when_audit_helper_fails -v
```

- [ ] **Step 3: Appliquer le correctif dans la copie de travail**

Ajouter en tête de fichier :

```python
import logging

logger = logging.getLogger(__name__)
```

Remplacer :

```python
    def _audit(self, action, resource_id, details=None, new_values=None):
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="PharmacyProduct",
                    action_performed=action,
                    resource_id=resource_id,
                    details=details,
                    new_values=new_values
                )
            except Exception: pass
```

par :

```python
    def _audit(self, action, resource_id, details=None, new_values=None):
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="PharmacyProduct",
                    action_performed=action,
                    resource_id=resource_id,
                    details=details,
                    new_values=new_values
                )
            except Exception:
                logger.exception("Échec de l'écriture d'audit")
```

(Un seul correctif couvre les 4 appels à `_audit()` dans le fichier — c'est tout l'intérêt de ce helper.)

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_audit_logging.py -v
```

- [ ] **Step 5: Isoler et stager**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:controller/pharmacy_controller.py > "$SCRATCH/pharmacy_controller_base_2e.py"
python - <<'PYEOF'
path = r"C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad/pharmacy_controller_base_2e.py"
content = open(path, encoding="utf-8").read()

old_import = "from typing import Optional"
new_import = "from typing import Optional\n\nimport logging\n\nlogger = logging.getLogger(__name__)"
assert old_import in content, "ancre d'import introuvable"
content = content.replace(old_import, new_import)

old = '''    def _audit(self, action, resource_id, details=None, new_values=None):
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="PharmacyProduct",
                    action_performed=action,
                    resource_id=resource_id,
                    details=details,
                    new_values=new_values
                )
            except Exception:
                pass'''
new = '''    def _audit(self, action, resource_id, details=None, new_values=None):
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="PharmacyProduct",
                    action_performed=action,
                    resource_id=resource_id,
                    details=details,
                    new_values=new_values
                )
            except Exception:
                logger.exception("Échec de l'écriture d'audit")'''
assert old in content, "pattern introuvable"
content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/pharmacy_controller_base_2e.py")
git update-index --cacheinfo 100644,$BLOB,controller/pharmacy_controller.py
git diff --cached -- controller/pharmacy_controller.py
```

Vérifier que le diff ne contient que le logger et ce hunk.

- [ ] **Step 6: Commit**

```bash
git add tests/test_audit_logging.py
git commit -m "fix(security): logger l'echec d'audit dans pharmacy_controller (OPS-01, 8/11)

except Exception: pass -> logger.exception(...) dans le helper
_audit(), qui couvre 4 usages (CREATE/UPDATE/etc. sur les produits).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: `controller/prescription_controller.py` (3 sites)

**Files:**
- Modify: `controller/prescription_controller.py` (isolation requise, `self.logger` déjà présent)
- Test: `tests/test_audit_logging.py` (étendu)

- [ ] **Step 1: Écrire le test qui échoue**

```python
def test_prescription_controller_logs_when_audit_fails_on_delete(caplog):
    from controller.prescription_controller import PrescriptionController

    repo = MagicMock()
    repo.delete.return_value = True
    user = MagicMock()
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = PrescriptionController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        result = ctrl.delete_prescription(prescription_id=1)

    assert result is True
    assert any("audit" in r.message.lower() for r in caplog.records)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

```bash
pytest tests/test_audit_logging.py::test_prescription_controller_logs_when_audit_fails_on_delete -v
```

- [ ] **Step 3: Appliquer les correctifs dans la copie de travail (3 sites, `self.logger` déjà disponible)**

Pour chacun des 3 blocs `CREATE`/`UPDATE`/`DELETE`, remplacer la ligne `except Exception: pass` qui suit l'appel `self.audit_repo.log_user_action(...)` correspondant par :

```python
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

```bash
pytest tests/test_audit_logging.py -v
```

- [ ] **Step 5: Isoler et stager**

```bash
SCRATCH="C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad"
git show HEAD:controller/prescription_controller.py > "$SCRATCH/prescription_controller_base_2e.py"
python - <<'PYEOF'
path = r"C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/329f3fe0-ad57-4845-be0d-e2813f5c1356/scratchpad/prescription_controller_base_2e.py"
content = open(path, encoding="utf-8").read()

replacements = [
    (
        '''                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="CREATE",
                    resource_id=presc_id,
                    details=f"Patient: {data.get('patient_id')}. Médicament: {data.get('medication')}" # type: ignore
                )
            except Exception: pass''',
        '''                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="CREATE",
                    resource_id=presc_id,
                    details=f"Patient: {data.get('patient_id')}. Médicament: {data.get('medication')}" # type: ignore
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")'''
    ),
    (
        '''                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="UPDATE",
                    resource_id=prescription_id,
                    new_values=data
                )
            except Exception: pass''',
        '''                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="UPDATE",
                    resource_id=prescription_id,
                    new_values=data
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")'''
    ),
    (
        '''                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="DELETE",
                    resource_id=prescription_id
                )
            except Exception: pass''',
        '''                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="DELETE",
                    resource_id=prescription_id
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")'''
    ),
]
for old, new in replacements:
    assert old in content, f"pattern introuvable: {old[:60]}"
    content = content.replace(old, new)
open(path, "w", encoding="utf-8").write(content)
print("ok")
PYEOF
BLOB=$(git hash-object -w "$SCRATCH/prescription_controller_base_2e.py")
git update-index --cacheinfo 100644,$BLOB,controller/prescription_controller.py
git diff --cached -- controller/prescription_controller.py
```

Vérifier que le diff contient exactement 3 hunks.

- [ ] **Step 6: Commit**

```bash
git add tests/test_audit_logging.py
git commit -m "fix(security): logger les echecs d'audit dans prescription_controller (OPS-01, 11/11)

except Exception: pass -> self.logger.exception(...) sur CREATE,
UPDATE, DELETE (prescription). Dernier des 11 sites du chantier 2e.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: Vérification finale de bout en bout

**Files:** aucun (vérification uniquement)

- [ ] **Step 1: Suite de tests complète**

```bash
pytest tests/ -v
```

Attendu : tous les tests passent, y compris les 6 nouveaux (un par fichier). Les 4 échecs pré-existants et non liés (chantiers 0/1) restent identiques.

- [ ] **Step 2: Vérification exhaustive par grep — aucun `except: pass` restant adjacent à un appel d'audit**

```bash
for f in controller/auth_controller.py controller/caisse_controller.py controller/medical_controller.py controller/patient_controller.py controller/pharmacy_controller.py controller/prescription_controller.py; do
  echo "=== $f ==="
  grep -B8 "except Exception: pass\|except: pass" "$f" | grep -c "audit_repo\.log"
done
```

Attendu : `0` pour chacun des 6 fichiers (hors sites explicitement exclus dans `change_user_password`, qui n'existe que dans la copie de travail d'`auth_controller.py` et n'est pas concerné par ce chantier).

- [ ] **Step 3: Confirmer que le travail en cours de l'utilisateur est intact**

```bash
git status --porcelain | wc -l
```

Attendu : le même nombre de fichiers modifiés qu'avant ce chantier (aucune perte, seuls les hunks isolés sont passés en commit).

- [ ] **Step 4: Récapitulatif**

Confirmer un par un, les 11 sites :
- [ ] `auth_controller.py` : `LOGIN_SUCCESS`, `LOGIN_FAILURE`
- [ ] `caisse_controller.py` : `CANCEL`
- [ ] `medical_controller.py` : `CREATE`, `UPDATE`, `DELETE`
- [ ] `patient_controller.py` : `SOFT_DELETE`
- [ ] `pharmacy_controller.py` : helper `_audit()` (4 usages)
- [ ] `prescription_controller.py` : `CREATE`, `UPDATE`, `DELETE`
- [ ] Les 2 sites de `change_user_password()` restent non touchés (absents de `HEAD`)
