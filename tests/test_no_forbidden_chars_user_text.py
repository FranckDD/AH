"""Garde-fou : pas de caracteres "typographiques" dans les textes visibles par l'utilisateur
(tiret long/demi-cadratin, points de suspension, point median, fleches, puce).

Portee : chaines litterales du code serveur (hors docstrings et commentaires) et
modeles HTML des PDF. Le code desktop retire et les modes hors ligne PyQt sont exclus.
"""
import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORBIDDEN = "—–…·→←↔⇒•"

PY_DIRS = ["controller", "repositories", "service", "utils", "tasks", "api_backend/backend_app"]
SKIP_PARTS = {"controller_offline", "repo_offline", "__pycache__", "tests"}
TEMPLATE_DIR = ROOT / "api_backend" / "backend_app" / "utils" / "templates"


def _python_files():
    for d in PY_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if SKIP_PARTS & set(p.parts):
                continue
            yield p


def _docstring_nodes(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                ids.add(id(body[0].value))
    return ids


def test_server_string_literals_have_no_forbidden_chars():
    offenders = []
    for p in _python_files():
        try:
            tree = ast.parse(p.read_text(encoding="utf8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        docs = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                if any(c in node.value for c in FORBIDDEN):
                    offenders.append(f"{p.relative_to(ROOT)}:{node.lineno}: {node.value[:60]!r}")
    assert not offenders, "\n".join(offenders)


def test_pdf_templates_have_no_forbidden_chars():
    offenders = []
    for p in TEMPLATE_DIR.glob("*.html"):
        for i, line in enumerate(p.read_text(encoding="utf8").splitlines(), 1):
            if any(c in line for c in FORBIDDEN):
                offenders.append(f"{p.name}:{i}: {line.strip()[:60]}")
    assert not offenders, "\n".join(offenders)
