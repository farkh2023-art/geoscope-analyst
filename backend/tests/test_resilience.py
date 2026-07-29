"""
Resilience tests — 100 % offline, aucune connexion Internet.
Tous les appels HTTP sont interceptés par des mocks unittest.mock.
"""
import httpx
import pytest
from unittest.mock import patch

from app.models.schemas import Coordinates
from app.services.geocoding.nominatim import NominatimGeocoder
from app.services.overpass_client import fetch_infrastructures


# ── Helpers ────────────────────────────────────────────────────────────────

class _MockNominatimResponse:
    """Réponse HTTP minimale simulant Nominatim."""
    status_code = 200
    def raise_for_status(self): pass
    def json(self): return {"address": {}, "display_name": "Lieu simulé"}


def _timeout_client_post():
    """Simule un client Overpass qui lève TimeoutException sur .request()."""
    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *_): pass
        async def request(self, method, url, **kwargs):
            raise httpx.TimeoutException("Timeout simulé")
    return _Client()


# ── Test 1 ─────────────────────────────────────────────────────────────────

async def test_overpass_timeout_does_not_crash():
    """
    Un timeout Overpass doit retourner [] sans lever d'exception.
    Garantit la dégradation gracieuse côté infrastructure.
    """
    with (
        patch("app.services.overpass_client.settings") as ms,
        patch("app.services.overpass_client.httpx.AsyncClient", return_value=_timeout_client_post()),
    ):
        ms.offline_mode = False
        ms.overpass_base_url = "https://overpass-api.de/api/interpreter"
        ms.request_timeout_seconds = 1

        result = await fetch_infrastructures(Coordinates(lat=48.8566, lon=2.3522), 1500)

    assert isinstance(result, list), "Le résultat doit être une liste"
    assert len(result) == 0, "La liste doit être vide après un timeout"


# ── Test 2 ─────────────────────────────────────────────────────────────────

async def test_user_agent_header_is_sent():
    """
    Chaque requête Nominatim doit inclure le header User-Agent configuré.
    Vérifie la conformité avec les exigences de l'API Nominatim.
    """
    captured: dict = {}

    class _CapturingClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *_): pass
        async def request(self, method, url, params=None, headers=None, **kwargs):
            captured["headers"] = headers or {}
            return _MockNominatimResponse()

    geocoder = NominatimGeocoder()

    with (
        patch("app.services.geocoding.nominatim.settings") as ms,
        patch("app.services.geocoding.nominatim.httpx.AsyncClient", return_value=_CapturingClient()),
    ):
        ms.nominatim_base_url = "https://nominatim.openstreetmap.org"
        ms.nominatim_user_agent = "GeoScopeAnalyst/0.2.0 local-test"
        ms.request_timeout_seconds = 10

        await geocoder.reverse(Coordinates(lat=48.8566, lon=2.3522))

    assert "User-Agent" in captured["headers"], "Le header User-Agent doit être présent"
    assert "GeoScopeAnalyst" in captured["headers"]["User-Agent"], (
        f"User-Agent attendu : GeoScopeAnalyst/... — reçu : {captured['headers'].get('User-Agent')}"
    )
    assert "0.2.0" in captured["headers"]["User-Agent"], "Le header doit contenir la version 0.2.0"


# ── Test 3 ─────────────────────────────────────────────────────────────────

async def test_analyze_online_external_failure_returns_200():
    """
    L'endpoint /api/analyze doit retourner HTTP 200 même quand
    le service de géocodage est indisponible.
    Garantit que l'application ne renvoie jamais de 500 sur panne externe.
    """
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    class _FailingGeocoder:
        async def search(self, query):
            raise httpx.ConnectError("Connexion refusée")
        async def reverse(self, coords):
            raise httpx.ConnectError("Connexion refusée")

    with patch("app.main.get_geocoder", return_value=_FailingGeocoder()):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/analyze",
                json={"input": "48.8566, 2.3522", "radius_m": 1500, "mode": "analyst"},
            )

    assert resp.status_code == 200, (
        f"Attendu 200, reçu {resp.status_code} — body : {resp.text[:200]}"
    )
    body = resp.json()
    assert "warnings" in body, "La réponse doit contenir un champ 'warnings'"
    warning_text = " ".join(body["warnings"]).lower()
    assert "géocodage" in warning_text or "indisponible" in warning_text, (
        f"Les warnings doivent mentionner la panne — reçu : {body['warnings']}"
    )
