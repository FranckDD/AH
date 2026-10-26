# scripts/migrate_toxico_consents.py
"""Deplace les consentements toxico de l'ancien dossier public /static vers le stockage protege.

    python scripts/migrate_toxico_consents.py

Pour chaque dossier dont consent_file vaut /static/uploads/toxico_consents/<nom> : le fichier est
deplace vers CONSENT_STORAGE_DIR (defaut storage/toxico_consents) sous un nom uuid aleatoire (extension
d'apres le contenu reel), et la colonne recoit ce nouvel identifiant. Idempotent : une ligne deja
migree ou dont le fichier est introuvable est laissee telle quelle (et signalee). Les fichiers de
l'ancien dossier sans ligne en base sont aussi deplaces (renommes) pour ne plus rien exposer.
Code 0 en cas de succes, 1 sur erreur.
"""
import os
import shutil
import sys

if __package__ in (None, ""):  # lance comme fichier : la racine du projet dans le chemin d'import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_backend.backend_app.utils.file_storage import (  # noqa: E402
    LEGACY_CONSENT_DIR, LEGACY_CONSENT_URL_PREFIX, consent_storage_dir,
    detect_consent_extension, new_consent_id,
)
from models.toxico import ToxicoDossier  # noqa: E402


def _move(src: str, storage_dir: str) -> str:
    with open(src, "rb") as fh:
        ext = detect_consent_extension(fh.read(16)) or ".pdf"
    new_id = new_consent_id(ext)
    os.makedirs(storage_dir, exist_ok=True)
    shutil.move(src, os.path.join(storage_dir, new_id))
    return new_id


def migrate(session, legacy_dir=None, storage_dir=None):
    """Retourne la liste des (ancien_nom, nouvel_identifiant) deplaces. Ne commit pas."""
    legacy_dir = legacy_dir or LEGACY_CONSENT_DIR
    storage_dir = storage_dir or consent_storage_dir()
    moved = []
    rows = session.query(ToxicoDossier).filter(ToxicoDossier.consent_file.like(LEGACY_CONSENT_URL_PREFIX + "%")).all()
    for d in rows:
        name = os.path.basename(d.consent_file)
        src = os.path.join(legacy_dir, name)
        if not os.path.isfile(src):
            print(f"  ABSENT  dossier {d.id}: {name} (ligne laissee telle quelle)")
            continue
        new_id = _move(src, storage_dir)
        d.consent_file = new_id
        moved.append((name, new_id))
        print(f"  DEPLACE dossier {d.id}: {name} -> {new_id}")
    session.flush()
    # Fichiers orphelins de l'ancien dossier (aucune ligne ne les reference) : ne plus les exposer.
    if os.path.isdir(legacy_dir):
        for name in sorted(os.listdir(legacy_dir)):
            src = os.path.join(legacy_dir, name)
            if os.path.isfile(src) and not name.startswith("."):
                new_id = _move(src, storage_dir)
                moved.append((name, new_id))
                print(f"  ORPHELIN {name} -> {new_id} (aucune ligne en base)")
    return moved


def main() -> int:
    from api_backend.backend_app.database import SessionLocal
    session = SessionLocal()
    try:
        moved = migrate(session)
        session.commit()
        print(f"{len(moved)} fichier(s) deplace(s) vers {consent_storage_dir()}")
        return 0
    except Exception as e:  # noqa: BLE001
        session.rollback()
        print(f"ERREUR: {e}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
