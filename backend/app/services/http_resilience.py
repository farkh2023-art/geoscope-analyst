import asyncio
import time

import httpx


class RateLimiter:
    """Limiteur simple côté client : au plus `rate` requêtes par seconde."""

    def __init__(self, rate: float):
        self._min_interval = 1.0 / rate if rate > 0 else 0.0
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = self._last_call + self._min_interval - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_call = time.monotonic()


def _parse_retry_after(value: str | None) -> float:
    if not value:
        return 1.0
    try:
        return max(0.0, float(value))
    except ValueError:
        return 1.0


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    limiter: RateLimiter,
    max_attempts: int = 3,
    **kwargs,
) -> httpx.Response:
    """
    Requête HTTP avec limiteur de débit, un retry unique sur HTTP 429
    (respectant Retry-After), et jusqu'à `max_attempts` tentatives pour les
    erreurs réseau (timeout, connexion). Toute erreur restante est levée pour
    que l'appelant applique sa dégradation gracieuse existante.
    """
    last_exc: Exception | None = None
    for _ in range(max_attempts):
        await limiter.wait()
        try:
            resp = await client.request(method, url, **kwargs)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            last_exc = exc
            continue

        if resp.status_code == 429:
            await asyncio.sleep(_parse_retry_after(resp.headers.get("Retry-After")))
            await limiter.wait()
            resp = await client.request(method, url, **kwargs)

        resp.raise_for_status()
        return resp

    raise last_exc
