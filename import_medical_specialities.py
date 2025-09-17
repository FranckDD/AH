# import_medical_specialties.py
"""
Copie medical_specialties depuis Postgres -> SQLite.
Usage:
  python import_medical_specialties.py \
    --pg "postgresql://user:pass@host/dbname" \
    --sqlite "sqlite:///offline.db"
Si tu ne passes pas d'args, il prendra les valeurs par défaut.
"""

import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DEFAULT_PG = "postgresql://postgres:Admin_2025@localhost/AH2"
DEFAULT_SQLITE = "sqlite:///offline.db"

def main(pg_url: str, sqlite_url: str):
    pg_engine = create_engine(pg_url)
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    # 1) Crée la table medical_specialties si elle n'existe pas (surtout utile si tu n'as pas modifié le schema)
    create_sql = """
    CREATE TABLE IF NOT EXISTS medical_specialties (
        specialty_id INTEGER PRIMARY KEY,
        name         TEXT NOT NULL UNIQUE
    );
    """
    try:
        with sqlite_engine.begin() as conn:
            conn.execute(text(create_sql))
    except SQLAlchemyError as e:
        print("Erreur création table sur sqlite:", e)
        raise

    # 2) Lire depuis Postgres
    try:
        with pg_engine.connect() as pg_conn:
            rows = pg_conn.execute(text("SELECT specialty_id, name FROM medical_specialties")).mappings().all()
    except SQLAlchemyError as e:
        print("Erreur lecture Postgres:", e)
        return

    if not rows:
        print("Aucune spécialité trouvée dans Postgres.")
    else:
        print(f"Found {len(rows)} specialties in Postgres — importing to SQLite...")

    # 3) Inserer dans sqlite (INSERT OR IGNORE pour éviter doublons)
    try:
        with sqlite_engine.begin() as sqlite_conn:
            for r in rows:
                sqlite_conn.execute(
                    text("INSERT OR IGNORE INTO medical_specialties (specialty_id, name) VALUES (:id, :name)"),
                    {"id": int(r["specialty_id"]), "name": r["name"]}
                )
        print("Import terminé.")
    except SQLAlchemyError as e:
        print("Erreur insertion SQLite:", e)
        raise

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pg", default=DEFAULT_PG, help="Postgres connection string")
    p.add_argument("--sqlite", default=DEFAULT_SQLITE, help="SQLite connection string (SQLAlchemy style)")
    args = p.parse_args()
    main(args.pg, args.sqlite)
