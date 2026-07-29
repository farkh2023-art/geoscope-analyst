import time


class TTLCache:
    """Cache mémoire simple (dict + horodatage), sans dépendance externe."""

    def __init__(self, ttl_seconds: int):
        self._ttl = ttl_seconds
        self._store: dict[object, tuple[float, object]] = {}

    def get(self, key: object) -> object | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: object, value: object) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)
