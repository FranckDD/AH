import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def build_limiter(redis_url=None):
    """Limiteur slowapi. Avec redis_url, les compteurs sont partages entre les workers
    gunicorn et survivent aux redemarrages (limite par poste, pas par worker). Si Redis
    tombe, repli en memoire plutot qu'une erreur 500 sur le login. Sans redis_url :
    memoire (developpement, tests)."""
    if redis_url:
        return Limiter(
            key_func=get_remote_address,
            storage_uri=redis_url,
            in_memory_fallback_enabled=True,
        )
    return Limiter(key_func=get_remote_address, storage_uri="memory://")


limiter = build_limiter(os.getenv("REDIS_URL") or None)
