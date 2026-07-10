from django.core.cache import cache


def is_rate_limited(key: str, limit: int = 5, window: int = 300) -> bool:
    """True si la limite est dépassée (brute-force).

    En cas d'échec cache (Redis down sur Render, etc.), on laisse passer
    plutôt que de renvoyer une erreur 500 au login.
    """
    try:
        count = cache.get(key)
        if count is None:
            cache.set(key, 1, window)
            return False
        if count >= limit:
            return True
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, window)
        return False
    except Exception:
        return False
