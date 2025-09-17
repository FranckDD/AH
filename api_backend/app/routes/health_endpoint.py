from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..database import get_db

router = APIRouter()

@router.get("/health", tags=["System"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"success": True, "status": "ok", "database": "connected"}
    except Exception as e:
        return {"success": False, "status": "error", "database": f"disconnected ({str(e)})"}
