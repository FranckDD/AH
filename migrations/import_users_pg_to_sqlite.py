# migrations/import_users_pg_to_sqlite.py
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Assure que le dossier projet (un niveau au-dessus de migrations) est dans sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from repositories.repo_offline.sqlite_manager import SQLiteManager  # now works

# Remplace par ta chaîne Postgres
PG_CONN = "postgresql://postgres:Admin_2025@localhost/AH2"

def import_users(pg_conn=PG_CONN, sqlite_path="offline.db"):
    # Postgres session
    pg_engine = create_engine(pg_conn)
    PgSession = sessionmaker(bind=pg_engine)
    pg = PgSession()

    # Sqlite session (SQLAlchemy session from your SQLiteManager)
    sqlite_mgr = SQLiteManager(db_path=sqlite_path)
    s = sqlite_mgr.get_session()

    try:
        # Récupère users dans Postgres
        rows = pg.execute(text(
            "SELECT user_id, username, password_hash, full_name, postgres_role, is_active FROM users"
        )).mappings().all()

        for r in rows:
            # skip si username existe déjà
            exists = s.execute(text("SELECT 1 FROM users WHERE username = :u"), {"u": r["username"]}).fetchone()
            if exists:
                print(f"skip existing {r['username']}")
                continue

            role_name = r.get("postgres_role") or None
            role_id = None
            if role_name:
                # Cherche role dans sqlite
                row_role = s.execute(text("SELECT role_id FROM application_roles WHERE role_name = :rn"), {"rn": role_name}).fetchone()
                if row_role is None:
                    # insert et commit pour être sûr que l'ID est accessible ensuite
                    s.execute(text("INSERT INTO application_roles (role_name) VALUES (:rn)"), {"rn": role_name})
                    s.commit()
                    row_role = s.execute(text("SELECT role_id FROM application_roles WHERE role_name = :rn"), {"rn": role_name}).fetchone()
                if row_role:
                    role_id = row_role[0]

            # Prépare is_active (sqlite stocke souvent 0/1)
            is_active = 1 if r.get("is_active") else 0

            # Insert user avec role_id (peut être NULL)
            s.execute(text(
                "INSERT INTO users (username, password_hash, role_id, postgres_role, full_name, created_at, updated_at, is_active) "
                "VALUES (:username, :password_hash, :role_id, :postgres_role, :full_name, datetime('now'), datetime('now'), :is_active)"
            ), {
                "username": r["username"],
                "password_hash": r["password_hash"],
                "role_id": role_id,
                "postgres_role": role_name,
                "full_name": r.get("full_name"),
                "is_active": is_active
            })

        s.commit()
        print("Import terminé.")
    except Exception as e:
        s.rollback()
        print("Erreur import:", e)
        raise
    finally:
        pg.close()
        s.close()


if __name__ == "__main__":
    import_users()
