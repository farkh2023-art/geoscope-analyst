"""
Mapping Géoplateforme — basé sur un payload réel capturé via curl sur
data.geopf.fr/geocodage/search (voir fixtures/geoplateforme_search_sample.json).
Aucun nom de champ deviné : structure confirmée par appel direct + openapi.yaml du service.
"""
import json
from pathlib import Path
from unittest.mock import patch

from app.models.schemas import Coordinates
from app.services.geocoding.geoplateforme import GeoplateformeGeocoder

_FIXTURE = Path(__file__).parent / "fixtures" / "geoplateforme_search_sample.json"


class _Resp:
    status_code = 200
    def __init__(self, data):
        self._data = data
    def raise_for_status(self): pass
    def json(self):
        return self._data


def _client_returning(data):
    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *_): pass
        async def request(self, method, url, **kwargs):
            return _Resp(data)
    return _Client()


async def test_search_maps_real_geoplateforme_payload():
    with open(_FIXTURE, encoding="utf-8") as f:
        payload = json.load(f)

    geocoder = GeoplateformeGeocoder()

    with patch("app.services.geocoding.geoplateforme.httpx.AsyncClient", return_value=_client_returning(payload)):
        result = await geocoder.search("8 boulevard du palais paris")

    assert result.display_name == "8 Boulevard du Palais 75001 Paris"
    assert result.city == "Paris"
    assert result.neighborhood == "Paris 1er Arrondissement"
    assert result.postcode == "75001"
    assert result.citycode == "75101"
    assert result.department == "Paris"
    assert result.region == "Île-de-France"
    assert result.country == "France"
    assert result.coordinates == Coordinates(lat=48.854843, lon=2.345141)
