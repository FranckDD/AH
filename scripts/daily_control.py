# scripts/daily_control.py
"""Controle quotidien des Rapports (a lancer par cron vers 23:30 Africa/Douala).

    python scripts/daily_control.py

Appelle ReportsController.catch_up(now UTC) dans une session SessionLocal, sans utilisateur
(pas d'audit, l'instantane fait foi) : rattrape les jours manques jusqu'a hier (30 jours au
plus), et aujourd'hui a partir de 23:30. Idempotent : relance, il ne cree ni instantane ni
notification de plus. Code 0 en cas de succes (y compris rien a faire et verrou occupe),
1 sur toute erreur.
"""
import logging
import os
import sys
from datetime import datetime, timezone

if __package__ in (None, ""):  # lance comme fichier : la racine du projet dans le chemin d'import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = logging.getLogger("daily_control")


def _default_factory():
    from api_backend.backend_app.database import SessionLocal
    return SessionLocal()


def main(session_factory=None, now=None) -> int:
    session = None
    locked = False
    try:
        if now is not None and now.tzinfo is None:
            raise ValueError("now doit avoir un fuseau.")
        from controller.reports_controller import get_reports_controller

        session = (session_factory or _default_factory)()
        ctrl = get_reports_controller(session, None)
        # Verrou de session reentrant : le prendre ici distingue "verrou occupe" de "rien a faire".
        if not ctrl.dc_repo.try_lock():
            session.rollback()
            log.warning("Verrou du controle quotidien occupe : passage saute, il sera refait au prochain.")
            return 0
        locked = True
        done = ctrl.catch_up(now if now is not None else datetime.now(timezone.utc))
        if not done:
            log.info("Aucun controle quotidien a faire.")
        for r in done:
            log.info("Controle du %s : new=%s open=%s notified=%s", r["day"], r["new"], r["open"],
                     r["notified"])
        return 0
    except Exception:
        log.exception("Echec du controle quotidien")
        if session is not None:
            try:
                session.rollback()
            except Exception:
                pass
        return 1
    finally:
        if session is not None:
            if locked:
                try:
                    ctrl.dc_repo.unlock()
                    session.commit()
                except Exception:
                    try:
                        session.rollback()
                    except Exception:
                        pass
            try:
                session.close()
            except Exception:
                pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.exit(main())
