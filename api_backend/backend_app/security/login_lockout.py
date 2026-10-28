"""Verrouillage de compte apres echecs de mot de passe repetes (chantier 8, tache 5b).

Regles validees par le proprietaire (2026-10-28) :
- MAX_FAILURES echecs de mot de passe sur le meme identifiant dans WINDOW_SECONDS verrouillent
  ce compte pendant LOCK_SECONDS ;
- pendant le verrouillage, meme le bon mot de passe est refuse avec la reponse generique habituelle ;
- une connexion reussie remet le compteur a zero ;
- un admin peut deverrouiller (unlock).

Le centre est derriere UNE seule adresse publique (NAT) : la limite par IP (LOGIN_IP_LIMIT) ne sert
qu'a l'anti-abus large ; le vrai anti-bruteforce est ce verrouillage par compte.

Stockage : Redis (REDIS_URL) partage entre les workers, avec repli en memoire (dict a expiration,
thread-safe) si REDIS_URL est absent ou si Redis est injoignable. Ouvert par defaut : si Redis tombe,
le controle de verrouillage ne bloque jamais un login (un avertissement est journalise une fois).
"""
import logging
import os
import threading
import time
from typing import Callable, Iterable, Optional

logger = logging.getLogger(__name__)

MAX_FAILURES = 5          # echecs tolerés avant verrouillage
WINDOW_SECONDS = 600      # fenetre de comptage des echecs (TTL du compteur)
LOCK_SECONDS = 600        # duree du verrouillage
LOGIN_IP_LIMIT = "60/minute"  # anti-abus par adresse IP sur POST /auth/login

_FAIL_PREFIX = "login:fail:"
_LOCK_PREFIX = "login:lock:"


MAX_KEY_LENGTH = 100


def normalize_username(username) -> str:
    """Meme cle pour 'Admin', 'admin ' et 'ADMIN' : la casse ne permet pas de contourner le compteur.
    Longueur plafonnee (le champ du formulaire n'est pas borne)."""
    return str(username or "").strip().lower()[:MAX_KEY_LENGTH]


class MemoryBackend:
    """Dict a expiration, protege par un verrou. `clock` injectable pour les tests."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._data = {}  # key -> (value, expires_at)

    def _alive(self, key):
        item = self._data.get(key)
        if item is None:
            return None
        if item[1] <= self._clock():
            self._data.pop(key, None)
            return None
        return item

    def incr(self, key: str, ttl: int) -> int:
        with self._lock:
            item = self._alive(key)
            if item is None:
                self._data[key] = (1, self._clock() + ttl)
                return 1
            self._data[key] = (item[0] + 1, item[1])
            return item[0] + 1

    def set_nx(self, key: str, ttl: int) -> bool:
        with self._lock:
            if self._alive(key) is not None:
                return False
            self._data[key] = (1, self._clock() + ttl)
            return True

    def exists(self, key: str) -> bool:
        with self._lock:
            return self._alive(key) is not None

    def exists_many(self, keys) -> list:
        with self._lock:
            return [self._alive(k) is not None for k in keys]

    def delete(self, *keys: str) -> None:
        with self._lock:
            for key in keys:
                self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


# INCR + EXPIRE en UNE operation atomique cote serveur : le compteur ne peut jamais exister sans TTL.
# Auto-reparation : un compteur existant sans TTL (TTL == -1) recoit son TTL.
_INCR_SCRIPT = (
    "local v = redis.call('INCR', KEYS[1]) "
    "if v == 1 or redis.call('TTL', KEYS[1]) < 0 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end "
    "return v"
)


class RedisBackend:
    def __init__(self, client, fast_client=None):
        self._r = client
        self._fast = fast_client if fast_client is not None else client  # timeouts courts (liste)

    def incr(self, key: str, ttl: int) -> int:
        return int(self._r.eval(_INCR_SCRIPT, 1, key, int(ttl)))

    def exists_many(self, keys) -> list:
        keys = list(keys)
        if not keys:
            return []
        pipe = self._fast.pipeline(transaction=False)
        for key in keys:
            pipe.exists(key)
        return [bool(v) for v in pipe.execute()]

    def set_nx(self, key: str, ttl: int) -> bool:
        return bool(self._r.set(key, "1", nx=True, ex=ttl))

    def exists(self, key: str) -> bool:
        return bool(self._r.exists(key))

    def delete(self, *keys: str) -> None:
        if keys:
            self._r.delete(*keys)

    def clear(self) -> None:
        keys = list(self._r.scan_iter(match="login:*"))
        if keys:
            self._r.delete(*keys)


class LoginLockout:
    """Verrouillage par compte. Toutes les methodes acceptent l'identifiant tel que saisi."""

    def __init__(self, backend=None, fallback: Optional[MemoryBackend] = None):
        self._backend = backend if backend is not None else MemoryBackend()
        self._fallback = fallback if fallback is not None else MemoryBackend()
        self._warned = False

    def _run(self, op: str, *args):
        """Execute sur Redis ; si Redis echoue, bascule sur la memoire (avertissement unique)."""
        try:
            return getattr(self._backend, op)(*args)
        except Exception as exc:  # Redis injoignable : ne jamais casser le login
            if not self._warned:
                self._warned = True
                logger.warning("Verrouillage de compte : Redis injoignable (%s), repli en memoire", exc)
            return getattr(self._fallback, op)(*args)

    def is_locked(self, username) -> bool:
        key = _LOCK_PREFIX + normalize_username(username)
        try:
            return bool(self._backend.exists(key)) or bool(self._fallback.exists(key))
        except Exception as exc:
            if not self._warned:
                self._warned = True
                logger.warning("Verrouillage de compte : Redis injoignable (%s), controle ignore", exc)
            return bool(self._fallback.exists(key))

    def register_failure(self, username) -> bool:
        """Compte un echec. Renvoie True si CET echec vient de declencher le verrouillage."""
        name = normalize_username(username)
        count = self._run("incr", _FAIL_PREFIX + name, WINDOW_SECONDS)
        if count < MAX_FAILURES:
            return False
        triggered = self._run("set_nx", _LOCK_PREFIX + name, LOCK_SECONDS)
        # Compteur remis a zero dans les deux cas : un echec arrive pendant le verrou
        # (rafale parallele) ne doit pas re-verrouiller des l'expiration.
        self._run("delete", _FAIL_PREFIX + name)
        return bool(triggered)

    def reset(self, username) -> None:
        """Connexion reussie : remet le compteur d'echecs a zero (ne leve jamais)."""
        try:
            self._run("delete", _FAIL_PREFIX + normalize_username(username))
        except Exception:
            logger.exception("Verrouillage de compte : reset impossible")

    def unlock(self, username) -> None:
        """Deverrouillage par un admin : supprime le verrou ET le compteur."""
        name = normalize_username(username)
        self._fallback.delete(_LOCK_PREFIX + name, _FAIL_PREFIX + name)
        # Une panne du stockage principal n'est PAS avalee : l'appelant doit le savoir.
        self._backend.delete(_LOCK_PREFIX + name, _FAIL_PREFIX + name)

    def locked_usernames(self, usernames: Iterable[str]) -> set:
        """Comptes verrouilles parmi `usernames`, en UN seul appel au stockage. Ouvert en cas d'erreur."""
        names = list(usernames)
        keys = [_LOCK_PREFIX + normalize_username(u) for u in names]
        try:
            flags = self._backend.exists_many(keys)
        except Exception as exc:
            if not self._warned:
                self._warned = True
                logger.warning("Verrouillage de compte : Redis injoignable (%s), liste sans etat", exc)
            flags = [False] * len(keys)
        mem = self._fallback.exists_many(keys)
        return {u for u, a, b in zip(names, flags, mem) if a or b}

    def clear_all(self) -> None:
        """Usage tests : vide tout l'etat de verrouillage."""
        for backend in (self._backend, self._fallback):
            try:
                backend.clear()
            except Exception:
                pass


_store: Optional[LoginLockout] = None
_store_lock = threading.Lock()


def build_store(redis_url: Optional[str] = None) -> LoginLockout:
    if redis_url:
        try:
            import redis
            client = redis.Redis.from_url(redis_url, decode_responses=True,
                                          socket_connect_timeout=1, socket_timeout=1)
            fast = redis.Redis.from_url(redis_url, decode_responses=True,
                                        socket_connect_timeout=0.3, socket_timeout=0.3)
            return LoginLockout(RedisBackend(client, fast))
        except Exception:
            logger.warning("Verrouillage de compte : Redis indisponible, repli en memoire")
    return LoginLockout(MemoryBackend())


def get_store() -> LoginLockout:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = build_store(os.getenv("REDIS_URL") or None)
    return _store
