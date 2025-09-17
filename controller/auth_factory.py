# controller/auth_factory.py
from typing import Optional, Tuple, Any
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# Repos (online/offline)
from repositories.user_repo import UserRepository as UserRepositoryOnline
from repositories.repo_offline.user_repo_offline import UserRepositoryOffline
from repositories.repo_offline.sqlite_manager import SQLiteManager

logger = logging.getLogger(__name__)




# controller/auth_factory.py
def get_user_repo_backend(mode: str = "auto",
                          pg_conn_string: Optional[str] = None,
                          sqlite_path: Optional[str] = "offline.db"
                          ) -> Tuple[Any, str, Optional[Any]]:
    """
    Détermine et retourne:
      (user_repo_instance, backend_str, session_or_manager)
    """
    mode = (mode or "auto").lower()

    # 1) Mode FORCE offline
    if mode == "offline":
        # Provide a default value if sqlite_path is None
        actual_sqlite_path = sqlite_path or "offline.db"
        sqlite_mgr = SQLiteManager(db_path=actual_sqlite_path)
        repo = UserRepositoryOffline(sqlite_mgr.get_session())
        return repo, "offline", sqlite_mgr

    # 2) Mode FORCE online
    if mode == "online":
        if not pg_conn_string:
            raise ValueError("pg_conn_string requis pour mode='online'")
        session = _try_postgres_session(pg_conn_string)
        if session is None:
            raise ConnectionError("Impossible de se connecter à Postgres en mode 'online'")
        repo = UserRepositoryOnline(session)
        return repo, "online", session  # ← Retourne Session SQLAlchemy

     # 3) Mode AUTO: essaie Postgres, sinon offline
    if mode == "auto":
        if pg_conn_string:
            session = _try_postgres_session(pg_conn_string)
            if session:
                # création du repo Postgres et renvoi
                repo = UserRepositoryOnline(session)
                return repo, "online", session

        # fallback SQLite - FIX: Provide default if sqlite_path is None
        actual_sqlite_path = sqlite_path or "offline.db"
        sqlite_mgr = SQLiteManager(db_path=actual_sqlite_path)
        repo_off = UserRepositoryOffline(sqlite_mgr.get_session())
        return repo_off, "offline", sqlite_mgr

    raise ValueError(f"Mode inconnu: {mode}")


def _try_postgres_session(pg_conn_string: str, timeout_sec: int = 3) -> Optional[Session]:
    """
    Tente d'ouvrir une session SQLAlchemy Postgres et d'exécuter un SELECT 1.
    Retourne la Session si OK, None sinon.
    """
    try:
        engine = create_engine(pg_conn_string, connect_args={"connect_timeout": timeout_sec})
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        # ping minimal — exécute une requête simple
        session.execute(text("SELECT 1"))
        logger.info("Ping Postgres OK")
        return session
    except OperationalError as e:
        logger.warning("Impossible de joindre Postgres: %s", e)
        return None
    except SQLAlchemyError as e:
        logger.exception("Erreur SQLAlchemy lors du test Postgres: %s", e)
        return None