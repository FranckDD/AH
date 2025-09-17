# controllers/auth_controller_factory.py
from typing import Optional, Tuple, Any
import logging
import os

from controller.auth_factory import get_user_repo_backend
from controller.auth_controller import AuthController as AuthControllerOnline
from controller.controller_offline.auth_controller_offline import AuthControllerOffline
from repositories.repo_offline.sqlite_manager import SQLiteManager

logger = logging.getLogger(__name__)


# controllers/auth_controller_factory.py

def get_auth_controller(mode: str = "auto",
                        pg_conn_string: Optional[str] = None,
                        sqlite_path: Optional[str] = "offline.db",
                        patient_repo_class: Optional[type] = None,
                        medical_repo_class: Optional[type] = None,
                        prescription_repo_class: Optional[type] = None,
                        appointment_repo_class: Optional[type] = None
                        ) -> Tuple[object, str]:
    """
    Retourne (auth_controller_instance, backend_str)
    """
    # Définir une chaîne de connexion par défaut si aucune n'est fournie
    if pg_conn_string is None:
        pg_conn_string = os.environ.get("DATABASE_URL", "postgresql://postgres:Admin_2025@localhost/A")
        logger.info(f"Utilisation de la chaîne de connexion PostgreSQL: {pg_conn_string}")
    
    try:
        user_repo, backend, session_or_mgr = get_user_repo_backend(
            mode=mode,
            pg_conn_string=pg_conn_string,
            sqlite_path=sqlite_path
        )
    except Exception as e:
        logger.exception(f"Erreur détection backend: {e}. Bascule en offline.")
        backend = "offline"
        session_or_mgr = None

    if backend == "online":
        # Pour AuthControllerOnline, on doit avoir une session SQLAlchemy Postgres
        if session_or_mgr is None:
            logger.warning("Session is None for online mode, falling back to offline")
            backend = "offline"
        else:
            try:
                auth_ctrl = AuthControllerOnline(db_session=session_or_mgr)
                logger.info("AuthController ONLINE instancié")
                return auth_ctrl, "online"
            except Exception as e:
                logger.exception(f"Erreur instanciation AuthControllerOnline: {e}. Fallback offline.")
                backend = "offline"
                session_or_mgr = None

    # --- OFFLINE branch ---
    sqlite_mgr: Optional[SQLiteManager] = None
    sqlite_session = None

    if session_or_mgr is not None:
        # Use isinstance check instead of hasattr for better type safety
        if isinstance(session_or_mgr, SQLiteManager):
            sqlite_mgr = session_or_mgr
            sqlite_session = sqlite_mgr.get_session()
        elif hasattr(session_or_mgr, 'execute'):  # Check if it's a SQLAlchemy session
            sqlite_session = session_or_mgr

    # Provide a default value if sqlite_path is None
    actual_sqlite_path = sqlite_path or "offline.db"

    auth_ctrl = AuthControllerOffline(
        session=sqlite_session,
        sqlite_manager=sqlite_mgr,
        db_path=(actual_sqlite_path if (sqlite_mgr is None and sqlite_session is None) else None),
        patient_repo_class=patient_repo_class,
        medical_repo_class=medical_repo_class,
        prescription_repo_class=prescription_repo_class,
        appointment_repo_class=appointment_repo_class
    )
    logger.info("AuthController OFFLINE instancié")
    return auth_ctrl, "offline"