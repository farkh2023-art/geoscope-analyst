from httpx import AsyncClient, ASGITransport

from app.main import app


async def test_no_activity_warns_and_never_yields_concurrent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze",
            json={"input": "48.8566, 2.3522", "radius_m": 1500, "mode": "analyst"},
        )

    assert resp.status_code == 200
    body = resp.json()

    warning_text = " ".join(body["warnings"]).lower()
    assert "activité" in warning_text

    roles = {i["role"] for i in body["infrastructures"]}
    assert "concurrent" not in roles


async def test_activity_boulangerie_yields_a_concurrent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze",
            json={"input": "48.8566, 2.3522", "radius_m": 1500, "mode": "analyst", "activity": "boulangerie"},
        )

    assert resp.status_code == 200
    body = resp.json()

    roles = {i["role"] for i in body["infrastructures"]}
    assert "concurrent" in roles
