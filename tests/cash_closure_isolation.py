# tests/cash_closure_isolation.py
"""Etat de caisse isole pour les tests de cloture, DANS la transaction du test (annulee en fin
de test) : la base de dev peut contenir le vrai depart, de vraies clotures, des corrections et
des modes modifies par l'admin.

session_replication_role = replica desactive les triggers d'immuabilite (et les FK) pour la
transaction en cours seulement ; il est remis a origin aussitot, et le rollback final restaure
tout. Le commit ne fait que relacher la SAVEPOINT de la fixture db_session, pour qu'un rollback
du controleur ne ressuscite pas les lignes effacees.
"""
import pytest
from sqlalchemy import text

OFFICIAL = (("especes", "Especes", 1), ("orange_money", "Orange Money", 2),
            ("mtn_money", "MTN Money", 3), ("autre_mobile", "Autre mobile", 4))


def reset_register(db):
    db.execute(text("SET LOCAL session_replication_role = replica"))
    try:
        for table in ("cash_closure_corrections", "cash_closure_lines", "cash_closures",
                      "cash_closure_start"):
            db.execute(text(f"DELETE FROM {table}"))
    finally:
        db.execute(text("SET LOCAL session_replication_role = origin"))
    for code, label, order in OFFICIAL:
        db.execute(text("UPDATE payment_modes SET label=:l, is_active=true, sort_order=:o "
                        "WHERE code=:c"), {"c": code, "l": label, "o": order})
    db.execute(text("UPDATE payment_modes SET is_active=false WHERE code NOT IN "
                    "('especes','orange_money','mtn_money','autre_mobile')"))
    db.commit()


@pytest.fixture
def clean_register(db_session):
    reset_register(db_session)
    return db_session
