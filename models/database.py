#database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class DatabaseManager:
    def __init__(self, connection_string):
        """
        Exemples de connection_string:
        - SQLite: 'sqlite:///hospital.db'
        - PostgreSQL: 'postgresql://user:password@localhost:5432/hospital'
        """
        self.engine = create_engine(connection_string)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Test la connexion immédiatement
        self._test_connection()

    def _test_connection(self):
        try:
            with self.engine.connect() as conn:
                print("✅ Connexion à la DB réussie")
        except Exception as e:
            print(f"❌ Erreur de connexion: {str(e)}")
            raise

    def get_session(self):
        """Pour les opérations ORM (SQLAlchemy)"""
        return self.SessionLocal()

    def get_connection(self):
        """Pour l'exécution directe de SQL/procédures stockées"""
        return self.engine.connect()

    def create_tables(self):
        """Crée toutes les tables définies dans les models"""
        Base.metadata.create_all(self.engine)
        print("Tables créées avec succès")