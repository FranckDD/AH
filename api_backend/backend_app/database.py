from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool  # ← Nouveau : Pool optimisé
from .config import DATABASE_URL

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not set. Please check your .env files.")

# Config pool pour Supabase (évite saturation)
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,  # ← Pool queue (gère better connexions)
    pool_size=5,          # ← Max connex simult (réduis si gratuit ; 5 safe pour dev)
    max_overflow=10,      # ← Extra temp (total ~15, match Supabase gratuit)
    pool_pre_ping=True,   # ← Ping avant use (détecte connex mortes)
    pool_recycle=300,     # ← Recycle every 5min (évite idle timeout)
    echo=False            # ← Logs off en prod (set True pour debug)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # ← Crucial : Force close (libère pool)