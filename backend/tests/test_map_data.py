from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.schemas import Coordinates
from app.services.overpass_client import fetch_infrastructures


async def test_map_data_infrastructure_coordinates_match_source():
    expected = await fetch_infrastructures(Coordinates(lat=48.8566, lon=2.3522), 1500)
    expected_by_name = {i.name: (i.lat, i.lon) for i in expected}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/map-data",
            json={"input": "48.8566, 2.3522", "radius_m": 1500, "mode": "analyst"},
        )

    assert resp.status_code == 200
    body = resp.json()

    infra_features = [
        f for f in body["geojson"]["features"]
        if f["properties"]["marker_type"] == "infrastructure"
    ]
    assert len(infra_features) == len(expected_by_name)

    for feature in infra_features:
        name = feature["properties"]["name"]
        lon, lat = feature["geometry"]["coordinates"]
        exp_lat, exp_lon = expected_by_name[name]
        # Aucun décalage : les coordonnées de la feature doivent être exactement
        # celles de l'objet source, jamais une position dérivée du nom (ancien bug du hash).
        assert lat == exp_lat
        assert lon == exp_lon
