# Stabilisation de `requirements.txt`

**Date :** 2026-08-12
**Statut :** validé, prêt pour plan d'implémentation
**Référence :** débloque le chantier 2c (split `requirements-api.txt`/`requirements-desktop.txt`), actuellement `⛔ Bloqué` faute de base commune entre `HEAD` et le travail en cours (registre `B4`)

## Contexte

`requirements.txt` diverge complètement entre `HEAD` (liste courte et organisée par sections, ~40 lignes) et le travail en cours de l'utilisateur (`pip freeze` brut, 147 lignes, triées alphabétiquement, sans commentaires). Cette divergence bloque le chantier 2c : aucune base commune sur laquelle faire un split propre.

## Découvertes pendant le cadrage

**L'environnement Python local n'est pas un venv dédié à AH2.** Deux paquets présents dans le freeze de 147 lignes n'ont aucun rapport avec ce projet :
- `pandas` — confirmé via `pip show pandas` comme dépendance transitive de `pyannote-core`, `pyannote-database`, `pyannote-metrics`, `whisperx` (outils de transcription/diarisation audio, sans lien avec AH2).
- `pygame` — `pip show pygame` confirme qu'aucun paquet n'en dépend, et aucun fichier `.py` du dépôt ne l'importe (recherché explicitly).

Conséquence directe : le freeze brut ne peut pas servir de base de confiance telle quelle. La liste finale est construite à partir d'un scan AST des imports réels sur l'ensemble du code Python du dépôt (`api_backend/`, `controller/`, `repositories/`, `models/`, `utils/`, `tasks/`, `tests/`, `alembic/`, `managers/`, `view_pyqt6/`, `view/`) — le freeze sert uniquement à récupérer la version installée de chaque paquet dont l'usage a été confirmé par le scan, vérifiée individuellement via `pip show` (source la plus à jour : le freeze lui-même s'est révélé légèrement périmé par rapport à l'environnement réellement installé sur plusieurs paquets, ex. `pydantic` 2.11.7 dans le freeze contre 2.13.4 réellement installé).

**Deux stacks UI desktop coexistent dans le code** : `view_pyqt6/` (PyQt6, 41 fichiers, actif) et du code mort isolé qui importe encore `customtkinter` directement — `hopital_sih.py` et `models/App.py` (ce dernier est littéralement le tutoriel de démonstration upstream de customtkinter, copié tel quel). Le dossier `view/` évoqué dans une version antérieure de ce constat n'existe pas dans ce dépôt (`git ls-files "view/"` ne retourne rien) ; c'est `hopital_sih.py` et `models/App.py`, tous deux trackés et référencés par aucun autre fichier du dépôt, qui sont la stack obsolète à exclure de `requirements.txt`.

**Paquets présents sur `HEAD` ou dans le freeze mais jamais réellement importés nulle part dans le code actuel** (recherché explicitement, zéro occurrence) :
- `pydantic-settings`, `sqlite-utils`, `loguru` — présents sur `HEAD` aujourd'hui, plus utilisés par le code actuel.
- `bandit`, `pytest-cov`/`coverage` — outils CLI (scan de sécurité, couverture), jamais importés par le code applicatif ou les tests, et aucune configuration du dépôt (`pytest.ini`, `.github/workflows/ci.yml`) ne les invoque.
- `locust` — contrairement aux trois précédents, `locust` EST importé (`locustfile.py:1`, `from locust import HttpUser, TaskSet, task, between`) ; il est exclu non pas parce qu'il n'est jamais importé, mais parce que c'est un outil de test de charge dev-only, invoqué manuellement en CLI, non nécessaire à l'exécution de l'application ou de sa suite de tests.

## Portée

Réécrire `requirements.txt` (le fichier committé sur `HEAD`, remplaçant sa version courte actuelle — pas le freeze de travail en cours, qui reste dans l'historique de session de l'utilisateur, hors dépôt) avec :

1. **Contenu** : uniquement les paquets dont l'import est confirmé par le scan AST. Organisé en sections commentées, structure identique à celle déjà en place sur `HEAD`, étendue :

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

Les dépendances transitives profondes (`idna`, `certifi`, `click`, `h11`, `anyio`, `numpy`, `six`, `typing_extensions`, etc. — une centaine d'entrées dans le freeze brut) ne sont **pas** pinnées individuellement : `pip` les résout automatiquement à partir des paquets directs ci-dessus, comme le fait déjà `HEAD` aujourd'hui pour ses ~25 paquets actuels. Choix délibéré : cohérent avec la convention déjà établie sur ce fichier, garde le fichier lisible et maintenable, prépare directement le split du chantier 2c (chaque section devient un fichier).

2. **Versions** : celles réellement installées et vérifiées (`pip show`), pas les anciennes pins de `HEAD` (jamais installées ni testées — c'était le finding `G6` de la revue finale du chantier 2b) ni le freeze brut de l'utilisateur (partiellement périmé par rapport à l'environnement réel).

3. **Exclus** (raison ci-dessus) : `pandas`, `pygame`, `customtkinter`, `tkcalendar`, `pydantic-settings`, `sqlite-utils`, `loguru`, `bandit`, `locust`, `pytest-cov`/`coverage`.

## Vérification

- Après réécriture, ré-exécuter le scan AST et confirmer qu'aucun import top-level du code (hors bibliothèque standard et modules internes du dépôt) ne manque à la liste.
- `pip install -r requirements.txt --dry-run` (ou équivalent) ne signale aucune erreur de résolution.
- Suite de tests complète (`pytest tests/ -v`) inchangée par rapport à l'état actuel (même 118 passed / 10 failed couplage WIP / 2 xfailed déjà documenté — ce chantier ne touche aucun code applicatif).

## Hors périmètre

- Le split effectif en `requirements-api.txt`/`requirements-desktop.txt` — c'est le chantier 2c lui-même, qui devient faisable une fois ce fichier stabilisé, mais reste un chantier séparé.
- La suppression de `hopital_sih.py` et `models/App.py` (code mort confirmé, stack customtkinter obsolète) — signalé pour information, pas traité ici.
- Un futur `requirements-dev.txt` pour `bandit`/`locust`/`pytest-cov` si l'utilisateur souhaite les garder disponibles pour un usage manuel — non demandé, non ajouté.
- Toute modification du code applicatif — ce chantier ne touche que `requirements.txt`.
