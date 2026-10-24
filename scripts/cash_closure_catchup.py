# scripts/cash_closure_catchup.py
"""Rattrapage des clotures de caisse automatiques (a lancer par cron, par ex. 23:05 Africa/Douala).

    python scripts/cash_closure_catchup.py

Appelle CashClosureController.auto_close_overdue(now UTC) dans une session SessionLocal, sans
utilisateur (l'audit est saute, la cloture elle-meme fait foi). Idempotent : relance, il ne cree
rien de plus. Code de sortie 0 en cas de succes (y compris rien a faire), 1 sur toute erreur.
"""
import logging
import os
import sys
from datetime import datetime, timezone

if __package__ in (None, ""):  # lance comme fichier : la racine du projet dans le chemin d'import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = logging.getLogger("cash_closure_catchup")


def _default_factory():
    from api_backend.backend_app.database import SessionLocal
    return SessionLocal()


def main(session_factory=None, now=None) -> int:
    session = None
    try:
        # now None : heure de la base (clock_timestamp()), comme les ecrivains d'argent
        if now is not None and now.tzinfo is None:
            raise ValueError("now doit avoir un fuseau.")
        from controller.cash_closure_controller import get_cash_closure_controller

        session = (session_factory or _default_factory)()
        ctrl = get_cash_closure_controller(session, None)
        # Le verrou consultatif est de transaction et reentrant dans la meme session : le prendre
        # ici permet de dire qu'une autre cloture est en cours au lieu d'un resultat vide muet.
        if not ctrl.repo.try_lock():
            session.rollback()
            log.warning("Verrou de cloture occupe : rattrapage peut-etre saute, il sera refait au prochain passage.")
            return 0
        created = ctrl.catch_up(now)
        if not created:
            log.info("Aucune cloture automatique a creer.")
        for c in created:
            log.info("Cloture automatique creee : id=%s date=%s attendu especes=%s",
                     c["id"], c["business_date"], c["expected_cash"])
        return 0
    except Exception:
        log.exception("Echec du rattrapage des clotures de caisse")
        if session is not None:
            try:
                session.rollback()
            except Exception:
                pass
        return 1
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.exit(main())
