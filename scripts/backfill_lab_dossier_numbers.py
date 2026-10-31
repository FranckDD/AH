# scripts/backfill_lab_dossier_numbers.py
"""Attribue un numero de dossier aux resultats de laboratoire qui n'en ont pas (anciens resultats).

    python scripts/backfill_lab_dossier_numbers.py            # simulation (rien n'est ecrit)
    python scripts/backfill_lab_dossier_numbers.py --apply    # ecrit

Les lignes sans numero sont groupees par reception (batch_id, sinon le resultat seul) ; chaque groupe recoit UN
numero (meme regles que la reception : utils/lab_dossier.assign_missing_dossier, jour = plus ancien test_date du
groupe, heure de Douala). Les groupes sont traites du plus ancien au plus recent, pour que les compteurs suivent
l'ordre des jours. Ne touche JAMAIS une ligne qui a deja un numero ; idempotent. Code de sortie 0 / 1.
"""
import logging
import os
import sys

if __package__ in (None, ""):  # lance comme fichier : la racine du projet dans le chemin d'import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

log = logging.getLogger("backfill_lab_dossier_numbers")


def _count_missing(session) -> int:
    return session.execute(text("SELECT count(*) FROM lab_results WHERE dossier_year IS NULL")).scalar()


def backfill(session, apply: bool = False) -> dict:
    """Retourne {"missing_before", "groups", "assigned_rows", "missing_after"}. Sans `apply`, tout est annule."""
    from models.lab import LabResult
    from utils.lab_dossier import assign_missing_dossier

    missing_before = _count_missing(session)
    savepoint = session.begin_nested()  # la simulation annule uniquement ce qu'elle a fait
    reps = session.execute(text(
        "SELECT MIN(result_id) AS rid FROM lab_results WHERE dossier_year IS NULL "
        "GROUP BY COALESCE(batch_id::text, 'r' || result_id::text) "
        "ORDER BY MIN(test_date) NULLS LAST, MIN(result_id)")).all()
    groups = 0
    for (rid,) in reps:
        result = session.get(LabResult, rid)
        if result is None or result.dossier_year is not None:
            continue
        assign_missing_dossier(session, result)
        groups += 1
    session.flush()
    missing_after = _count_missing(session)
    report = {"missing_before": missing_before, "groups": groups,
              "assigned_rows": missing_before - missing_after, "missing_after": missing_after}
    if apply:
        savepoint.commit()
        session.commit()
    else:
        savepoint.rollback()
    return report


def main(argv=None, session_factory=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    apply = "--apply" in argv
    session = None
    try:
        if session_factory is None:
            from api_backend.backend_app.database import SessionLocal as session_factory
        session = session_factory()
        report = backfill(session, apply=apply)
        print(("APPLIQUE" if apply else "SIMULATION (rien n'est ecrit)"), report)
        return 0
    except Exception:
        log.exception("Echec de l'attribution des numeros de dossier")
        if session is not None:
            session.rollback()
        return 1
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
