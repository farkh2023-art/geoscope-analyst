import httpx
import pytest

from app.services.http_resilience import RateLimiter, request_with_retry


class _Resp:
    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error", request=httpx.Request("GET", "https://example.test"), response=self
            )


async def test_429_retries_once_then_degrades():
    calls = []

    class _Client:
        async def request(self, method, url, **kwargs):
            calls.append(1)
            return _Resp(429, headers={"Retry-After": "0"})

    limiter = RateLimiter(1000)  # débit élevé pour ne pas ralentir le test

    with pytest.raises(httpx.HTTPStatusError):
        await request_with_retry(_Client(), "GET", "https://example.test", limiter=limiter)

    assert len(calls) == 2, "Un seul retry attendu après un 429 (2 tentatives au total)"


async def test_success_on_first_attempt_no_retry():
    calls = []

    class _Client:
        async def request(self, method, url, **kwargs):
            calls.append(1)
            return _Resp(200)

    limiter = RateLimiter(1000)
    resp = await request_with_retry(_Client(), "GET", "https://example.test", limiter=limiter)

    assert resp.status_code == 200
    assert len(calls) == 1


async def test_connection_errors_retry_up_to_max_attempts():
    calls = []

    class _Client:
        async def request(self, method, url, **kwargs):
            calls.append(1)
            raise httpx.ConnectError("Connexion refusée")

    limiter = RateLimiter(1000)

    with pytest.raises(httpx.ConnectError):
        await request_with_retry(_Client(), "GET", "https://example.test", limiter=limiter, max_attempts=3)

    assert len(calls) == 3
