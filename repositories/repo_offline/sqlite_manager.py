# repositories/repo_offline/sqlite_manager.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

class SQLiteManager:
    def __init__(self, db_path: str = "offline.db", echo: bool = False):
        # db_path peut être un chemin absolu
        uri = f"sqlite:///{os.path.abspath(db_path)}"
        self.engine = create_engine(uri, connect_args={"check_same_thread": False}, echo=echo)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.SessionLocal()

    def get_engine(self):
        return self.engine

    def close(self):
        """Ferme l'engine et ses connections."""
        if self.engine:
            self.engine.dispose()