"""Verifie deploy/scheduler/crontab (lu par supercronic dans le conteneur scheduler)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRONTAB = ROOT / "deploy" / "scheduler" / "crontab"

FIELD_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]  # min heure jour mois jour-semaine


def _jobs():
    lines = CRONTAB.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def _valid_field(field, lo, hi):
    for part in field.split(","):
        m = re.fullmatch(r"(\*|\d+(?:-\d+)?)(?:/(\d+))?", part)
        if not m:
            return False
        base, step = m.groups()
        if step is not None and int(step) < 1:
            return False
        if base != "*":
            bounds = [int(x) for x in base.split("-")]
            if any(b < lo or b > hi for b in bounds) or bounds != sorted(bounds):
                return False
    return True


def test_crontab_exists_and_has_jobs():
    assert CRONTAB.is_file()
    assert _jobs()


def test_every_job_has_five_valid_fields_and_a_command():
    for job in _jobs():
        parts = job.split(None, 5)
        assert len(parts) == 6, f"ligne invalide: {job!r}"
        for field, (lo, hi) in zip(parts[:5], FIELD_RANGES):
            assert _valid_field(field, lo, hi), f"champ cron invalide {field!r} dans {job!r}"
        assert parts[5].strip()


def test_spec_commands_present():
    jobs = _jobs()
    assert "5 * * * * python scripts/cash_closure_catchup.py" in jobs
    assert "30 23 * * * python scripts/daily_control.py" in jobs
    assert "*/10 * * * * python -m deploy.alerts.run_checks" in jobs


def test_referenced_scripts_exist():
    for job in _jobs():
        command = job.split(None, 5)[5]
        for token in command.split():
            if token.endswith(".py"):
                assert (ROOT / token).is_file(), f"script introuvable: {token}"
