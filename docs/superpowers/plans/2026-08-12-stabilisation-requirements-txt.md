# Stabilisation de `requirements.txt` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer le `requirements.txt` committé sur `HEAD` (liste courte périmée) par une liste organisée en sections, dérivée des imports réels du code, avec les versions réellement installées et vérifiées — débloque le chantier 2c.

**Architecture:** Réécriture d'un seul fichier texte. Aucun code applicatif touché. Le contenu exact (paquets, versions, sections, exclusions) est déjà entièrement déterminé par la spec — cette tâche est de la transcription vérifiée, pas de la conception.

**Tech Stack:** `pip`, scan AST Python (stdlib `ast`), pytest.

## Global Constraints

- Le fichier remplacé est `requirements.txt` à la racine du dépôt (fichier committé sur `HEAD`, pas le `pip freeze` de travail en cours de l'utilisateur — hors dépôt, jamais touché par cette tâche).
- Versions exactes à utiliser, toutes vérifiées via `pip show` pendant le cadrage (voir spec, section "Portée", point 1) — copier-coller le bloc de contenu ci-dessous verbatim, ne pas re-deviner de versions.
- Ne pas pinner individuellement les dépendances transitives profondes (`idna`, `certifi`, `click`, `h11`, `anyio`, `numpy`, `six`, `typing_extensions`, etc.) — `pip` les résout automatiquement à partir des paquets directs listés.
- Paquets explicitement exclus (voir spec pour la justification complète de chacun) : `pandas`, `pygame`, `customtkinter`, `tkcalendar`, `pydantic-settings`, `sqlite-utils`, `loguru`, `bandit`, `locust`, `pytest-cov`/`coverage`.
- Aucun fichier de code applicatif n'est modifié par ce plan.

---

### Task 1: Réécrire `requirements.txt`

**Files:**
- Modify: `requirements.txt` (remplacement intégral du contenu)

**Interfaces:**
- Consumes: rien
- Produces: rien (fichier de configuration, pas de code consommé par une autre tâche)

- [ ] **Step 1: Lire le contenu actuel de `requirements.txt` sur `HEAD`**

Confirmer l'état de départ avant modification :

Run: `git show HEAD:requirements.txt`

Expected: la version courte actuelle (sections `Backend API`, `Validation & Config`, `Synchronisation Offline`, `Logging`, `Tests`, `Rate limiting`, `Génération PDF factures`, `Hash code`, `Traitement images`, `Upload de fichiers` — issue du chantier 2b).

- [ ] **Step 2: Remplacer intégralement le contenu de `requirements.txt` par le bloc suivant**

```
# === Backend API ===
fastapi==0.116.1
uvicorn[standard]==0.35.0
SQLAlchemy==2.0.41
psycopg2-binary==2.9.10
alembic==1.18.5
passlib[bcrypt]==1.7.4
python-jose==3.5.0
email-validator==2.3.0
requests==2.32.5
pydantic==2.13.4
python-dotenv==1.1.1
starlette==0.47.3
slowapi==0.1.9
limits==5.8.0
Deprecated==1.3.1
fpdf2==2.8.3
Pillow==12.2.0
python-multipart==0.0.20
bcrypt==4.3.0

# === Desktop (PyQt6) ===
PyQt6==6.9.1
PyQt6-Qt6==6.9.1
PyQt6_sip==13.10.2
matplotlib==3.10.3
reportlab==4.4.2
openpyxl==3.1.5

# === Tests ===
pytest==8.4.2
httpx==0.28.1

# === Async / travail en cours (non committé sur HEAD) ===
celery==5.6.0
redis==6.4.0
Flask-Login==0.6.3
Jinja2==3.1.6
weasyprint==68.1
supabase==2.25.0
```

Aucune autre modification du fichier — c'est un remplacement complet, pas un patch incrémental.

- [ ] **Step 3: Ré-exécuter le scan AST pour confirmer qu'aucun import réel du code ne manque à la nouvelle liste**

Ce script scanne tous les fichiers `.py` du dépôt (hors bibliothèque standard, hors modules internes du projet) et liste chaque paquet tiers importé quelque part — la sortie doit être un sous-ensemble de ce qui est maintenant dans `requirements.txt` (à l'exception des dépendances transitives volontairement non pinnées, ex. `numpy`, `six`, `dotenv`→`python-dotenv`, `jose`→`python-jose`, `PIL`→`Pillow`, `fpdf`→`fpdf2`).

Run (depuis la racine du dépôt) :
```bash
python << 'EOF'
import ast, os

roots = ["api_backend", "controller", "repositories", "models", "utils", "tasks",
         "tests", "view_pyqt6", "managers", "gateway", "repo_offline",
         "Offline_access", "alembic", "service", "migrations"]

collected = {}

def scan_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            tree = ast.parse(f.read(), filename=path)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                collected.setdefault(alias.name.split(".")[0], set()).add(path)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            if node.module:
                collected.setdefault(node.module.split(".")[0], set()).add(path)

for root in roots:
    if not os.path.isdir(root):
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                scan_file(os.path.join(dirpath, fn))

for fn in os.listdir("."):
    if fn.endswith(".py"):
        scan_file(fn)

stdlib = {"__future__","argparse","calendar","configparser","csv","datetime","decimal","enum",
"functools","getpass","glob","inspect","io","json","logging","math","os","pathlib","random",
"re","secrets","shutil","sqlite3","subprocess","sys","threading","time","traceback","types",
"typing","unittest","uuid","winsound","tkinter","copy","collections","abc","base64","hashlib",
"hmac","warnings","asyncio","contextlib","dataclasses","itertools"}
internal = {"api_backend","app","controller","models","repositories","tasks","tests","utils",
"managers","view","view_pyqt6","config_local","celery_app","config"}

third_party = sorted(m for m in collected if m not in stdlib and m not in internal)
print("\n".join(third_party))
EOF
```

Expected: la sortie ne contient aucun paquet absent de `requirements.txt` (en tenant compte des correspondances nom-de-module → nom-de-paquet-PyPI ci-dessus, et des dépendances transitives volontairement non pinnées : `starlette`/`anyio`/`numpy` etc. peuvent apparaître dans la sortie du scan sans que ce soit un problème, puisqu'ils sont déjà tirés automatiquement par les paquets directs — seul un paquet **directement importé nulle part couvert** serait un vrai problème). Si un paquet manque réellement, l'ajouter à la section appropriée avec sa version installée (`pip show <paquet>`), puis reprendre ce Step.

- [ ] **Step 4: Vérifier que `pip` peut résoudre le fichier sans erreur**

Run: `pip install -r requirements.txt --dry-run 2>&1 | tail -30`

Expected: aucune erreur de résolution de dépendances (des avertissements de version de `pip` lui-même sont normaux et sans rapport).

- [ ] **Step 5: Exécuter la suite de tests complète pour confirmer l'absence de régression**

Run: `python -m pytest tests/ -q`

Expected: même résultat que l'état actuel documenté au chantier 2b (118 passed, 10 failed — couplage avec le travail en cours déjà documenté dans `docs/superpowers/SUIVI-AVANCEMENT.md`, 2 xfailed). Si un nombre différent de tests échoue, investiguer avant de continuer — ce plan ne doit introduire aucune régression, aucun fichier de code applicatif n'étant modifié.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt
git commit -m "chore: stabilize requirements.txt from verified imports, not raw pip freeze

Remplace la liste courte de HEAD (jamais reinstallee ni testee, cf.
finding G6 chantier 2b) par une liste derivee d'un scan AST des imports
reels du code, versions verifiees via pip show. Exclut pandas/pygame
(pollution d'environnement - dependances d'autres projets sans rapport,
whisperx/pyannote-*), customtkinter/tkcalendar (stack UI view/ confirmee
obsolete), pydantic-settings/sqlite-utils/loguru (plus importes nulle
part), bandit/locust/pytest-cov (outils CLI jamais invoques). Debloque
le chantier 2c (registre B4). Aucun code applicatif touche."
```
