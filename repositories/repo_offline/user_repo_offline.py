# repositories/repo_offline/user_repo_offline.py
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy import Table, Column, Integer, String, MetaData, select, text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
import logging

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
metadata = MetaData()

# Tables SQLite offline (schéma simplifié)
users_table = Table(
    "users", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("uuid", String),
    Column("username", String, nullable=False, unique=True),
    Column("password_hash", String, nullable=False),
    Column("postgres_role", String),
    Column("is_active", Integer, default=1),
    Column("specialty_id", Integer),
    Column("role_id", Integer),   # FK to application_roles.role_id
    Column("full_name", String),
    Column("created_at", String),
    Column("updated_at", String),
    Column("last_modified", String),
    Column("revision", Integer),
    Column("sync_status", String)
)

application_roles_table = Table(
    "application_roles", metadata,
    Column("role_id", Integer, primary_key=True),
    Column("role_name", String, nullable=False, unique=True)
)


class OfflineRole:
    def __init__(self, role_id: Optional[int], role_name: Optional[str]):
        self.role_id = role_id
        self.role_name = (role_name or "unknown")

    def __repr__(self):
        return f"OfflineRole(role_id={self.role_id}, role_name='{self.role_name}')"


class OfflineUser:
    def __init__(
        self,
        user_id: Optional[int],
        username: str,
        password_hash: str,
        role_id: Optional[int] = None,
        postgres_role: Optional[str] = None,
        full_name: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        application_role: Optional[OfflineRole] = None,
        is_active: bool = True
    ):
        self.user_id = user_id
        self.username = username or ""
        self.password_hash = password_hash or ""
        self.role_id = role_id
        self.postgres_role = postgres_role or ""
        self.full_name = full_name or ""
        self.created_at = created_at or ""
        self.updated_at = updated_at or ""
        self.is_active = is_active

        # application_role est un objet OfflineRole (ou None)
        self.application_role: Optional[OfflineRole] = application_role
        # roles: liste pour compatibilité (controllers qui lisent user.roles)
        self.roles: List[OfflineRole] = [application_role] if application_role else []

    def check_password(self, password: str) -> bool:
        try:
            return pwd_context.verify(password, str(self.password_hash))
        except Exception:
            return False

    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)

    def __repr__(self):
        return f"OfflineUser(id={self.user_id}, username='{self.username}', role={self.application_role})"


class UserRepositoryOffline:
    def __init__(self, session):
        self.session = session
        self.logger = logging.getLogger(__name__)

    def _resolve_role_row(self, role_id: Optional[int]):
        """Retourne la row (role_id, role_name) depuis application_roles ou None."""
        if role_id is None:
            return None
        try:
            row = self.session.execute(
                text("SELECT role_id, role_name FROM application_roles WHERE role_id = :rid"),
                {"rid": role_id}
            ).mappings().first()
            return row
        except Exception:
            self.logger.exception("Erreur _resolve_role_row sqlite")
            return None

    def _normalize_role_name(self, raw: Optional[str]) -> Optional[str]:
        """Transforme role technique en nom métier attendu par le UI (ex: 'app_medical' -> 'medecin')."""
        if not raw:
            return None
        r = raw.strip().lower()

        # Si le rôle stocké est déjà un nom métier (medecin, secretaire, admin...), renvoie direct.
        simple_allowed = {"medecin", "secretaire", "admin", "infirmier", "laborantin", "pharmacien", "nurse", "doctor"}
        if r in simple_allowed:
            return r

        # Map explicite pour valeurs 'app_*' ou autres identifiants techniques
        mapping = {
            "app_medical": "medecin",
            "app_medecin": "medecin",
            "app_nurse": "infirmier",
            "app_infirmier": "infirmier",
            "app_secretaire": "secretaire",
            "app_pharmacy": "pharmacien",
            "app_lab": "laborantin",
            "app_admin": "admin",
            "app_med": "medecin",
        }
        # si exactement dans mapping
        if r in mapping:
            return mapping[r]

        # si commence par 'app_' -> enlève préfixe
        if r.startswith("app_"):
            candidate = r[4:]
            # si candidate ressemblant -> retourne candidate sinon fallback
            if candidate in simple_allowed:
                return candidate
            # french english handling
            if candidate == "medical":
                return "medecin"
            if candidate in ("medecin", "med"):
                return "medecin"

        # heuristiques simples sur contenu
        if "med" in r:
            return "medecin"
        if "secr" in r:
            return "secretaire"
        if "pharm" in r:
            return "pharmacien"
        if "lab" in r:
            return "laborantin"
        if "nurs" in r or "infirm" in r:
            return "infirmier"

        # fallback: renvoyer la chaîne brute (mais lowercased)
        return r

    def _effective_role(self, role_id: Optional[int], postgres_role: Optional[str]) -> OfflineRole:
        """
        Retourne un OfflineRole avec role_name normalisé.
        Priorité: application_roles (si présent) -> postgres_role -> fallback 'user'.
        """
        # 1) si application_roles existe, utilise-le mais normalise son role_name
        row = self._resolve_role_row(role_id)
        if row:
            raw_name = row.get("role_name")
            norm = self._normalize_role_name(raw_name)
            self.logger.debug("Role resolved from application_roles: raw=%s norm=%s", raw_name, norm)
            return OfflineRole(role_id=int(row["role_id"]), role_name=norm)

        # 2) sinon utilise postgres_role (peut contenir plusieurs tokens séparés par ,)
        if postgres_role:
            # si postgres_role contient plusieurs marqueurs, prends le premier normalisé
            tokens = [t.strip() for t in (postgres_role or "").split(",") if t.strip()]
            for tok in tokens:
                norm = self._normalize_role_name(tok)
                if norm:
                    self.logger.debug("Role derived from postgres_role token=%s norm=%s", tok, norm)
                    return OfflineRole(role_id=role_id, role_name=norm)
            # si tokens vides -> fallback simple
            norm = self._normalize_role_name(postgres_role)
            self.logger.debug("Role derived from postgres_role (fallback)=%s", norm)
            return OfflineRole(role_id=role_id, role_name=norm)

        # 3) dernier recours
        return OfflineRole(role_id=role_id, role_name="user")

    def get_user_by_username(self, username: str) -> Optional[OfflineUser]:
        try:
            q = select(users_table).where(users_table.c.username == username)
            row = self.session.execute(q).mappings().first()
            if not row:
                return None
            role_obj = self._effective_role(row.get("role_id"), row.get("postgres_role"))
            self.logger.debug("get_user_by_username: username=%s db_role_id=%s db_postgres_role=%s resolved=%s",
                              username, row.get("role_id"), row.get("postgres_role"), role_obj)
            return OfflineUser(
                user_id=int(row["user_id"]) if row.get("user_id") is not None else None,
                username=row["username"],
                password_hash=row["password_hash"],
                role_id=row.get("role_id"),
                postgres_role=row.get("postgres_role"),
                full_name=row.get("full_name"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                application_role=role_obj,
                is_active=(row.get("is_active", 1) == 1)
            )
        except SQLAlchemyError:
            self.logger.exception("get_user_by_username sqlite error")
            raise

    def get_user_by_id(self, user_id: int) -> Optional[OfflineUser]:
        try:
            q = select(users_table).where(users_table.c.user_id == user_id)
            row = self.session.execute(q).mappings().first()
            if not row:
                return None
            role_obj = self._effective_role(row.get("role_id"), row.get("postgres_role"))
            self.logger.debug("get_user_by_id: id=%s resolved=%s", user_id, role_obj)
            return OfflineUser(
                user_id=int(row["user_id"]) if row.get("user_id") is not None else None,
                username=row["username"],
                password_hash=row["password_hash"],
                role_id=row.get("role_id"),
                postgres_role=row.get("postgres_role"),
                full_name=row.get("full_name"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                application_role=role_obj,
                is_active=(row.get("is_active", 1) == 1)
            )
        except SQLAlchemyError:
            self.logger.exception("get_user_by_id sqlite error")
            raise

    def create_user(self, username: str, password: str, full_name: Optional[str] = None,
                    role_id: Optional[int] = None, postgres_role: Optional[str] = None) -> OfflineUser:
        now = datetime.utcnow().isoformat()
        hashed = pwd_context.hash(password)
        ins = users_table.insert().values(
            username=username,
            password_hash=hashed,
            role_id=role_id,
            postgres_role=postgres_role,
            full_name=full_name,
            created_at=now,
            updated_at=now,
            is_active=1
        )
        try:
            res = self.session.execute(ins)
            self.session.commit()
            # récupère le nouvel id de façon sûre:
            row = self.session.execute(
                select(users_table.c.user_id).where(users_table.c.username == username)
            ).mappings().first()
            new_id = int(row["user_id"]) if row and row.get("user_id") is not None else None

            role_obj = self._effective_role(role_id, postgres_role)
            return OfflineUser(
                user_id=new_id,
                username=username,
                password_hash=hashed,
                role_id=role_id,
                postgres_role=postgres_role,
                full_name=full_name,
                created_at=now,
                updated_at=now,
                application_role=role_obj,
                is_active=True
            )
        except SQLAlchemyError:
            self.session.rollback()
            self.logger.exception("create_user sqlite error")
            raise

    def delete_user(self, user_id: int) -> bool:
        try:
            d = users_table.delete().where(users_table.c.user_id == user_id)
            res = self.session.execute(d)
            self.session.commit()
            return (res.rowcount if hasattr(res, "rowcount") else 0) > 0
        except SQLAlchemyError:
            self.session.rollback()
            self.logger.exception("delete_user sqlite error")
            raise

    def list_users(self) -> List[OfflineUser]:
        q = select(users_table)
        rows = self.session.execute(q).mappings().all()
        users: List[OfflineUser] = []
        for r in rows:
            role_obj = self._effective_role(r.get("role_id"), r.get("postgres_role"))
            users.append(OfflineUser(
                user_id=int(r["user_id"]) if r.get("user_id") is not None else None,
                username=r["username"],
                password_hash=r["password_hash"],
                role_id=r.get("role_id"),
                postgres_role=r.get("postgres_role"),
                full_name=r.get("full_name"),
                created_at=r.get("created_at"),
                updated_at=r.get("updated_at"),
                application_role=role_obj,
                is_active=(r.get("is_active", 1) == 1)
            ))
        return users

    def search_users(self, query: str) -> List[OfflineUser]:
        q = query.strip()
        users: List[OfflineUser] = []

        try:
            sel = text("SELECT * FROM users WHERE username LIKE :p OR full_name LIKE :p")
            rows = self.session.execute(sel, {"p": f"%{q}%"}).mappings().all()
            for r in rows:
                role_obj = self._effective_role(r.get("role_id"), r.get("postgres_role"))
                users.append(OfflineUser(
                    user_id=int(r["user_id"]) if r.get("user_id") is not None else None,
                    username=r["username"],
                    password_hash=r["password_hash"],
                    role_id=r.get("role_id"),
                    postgres_role=r.get("postgres_role"),
                    full_name=r.get("full_name"),
                    created_at=r.get("created_at"),
                    updated_at=r.get("updated_at"),
                    application_role=role_obj,
                    is_active=(r.get("is_active", 1) == 1)
                ))

            # recherche par role_name (application_roles)
            role_row = self.session.execute(
                text("SELECT role_id FROM application_roles WHERE role_name LIKE :p"),
                {"p": f"%{q}%"}
            ).fetchone()
            if role_row:
                rid = int(role_row[0])
                sel2 = select(users_table).where(users_table.c.role_id == rid)
                rows2 = self.session.execute(sel2).mappings().all()
                for r in rows2:
                    role_obj = self._effective_role(r.get("role_id"), r.get("postgres_role"))
                    if not any(u.user_id == r["user_id"] for u in users):
                        users.append(OfflineUser(
                            user_id=int(r["user_id"]) if r.get("user_id") is not None else None,
                            username=r["username"],
                            password_hash=r["password_hash"],
                            role_id=r.get("role_id"),
                            postgres_role=r.get("postgres_role"),
                            full_name=r.get("full_name"),
                            created_at=r.get("created_at"),
                            updated_at=r.get("updated_at"),
                            application_role=role_obj,
                            is_active=(r.get("is_active", 1) == 1)
                        ))
            return users
        except SQLAlchemyError:
            self.logger.exception("search_users sqlite error")
            raise
