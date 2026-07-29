from unittest.mock import patch

from app.services.geocoding.geoplateforme import GeoplateformeGeocoder


class _Resp:
    status_code = 200
    def raise_for_status(self): pass
    def json(self):
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [2.3522, 48.8566]},
                "properties": {"label": "Paris", "city": "Paris", "context": "75, Paris, Île-de-France"},
            }],
        }


async def test_identical_search_calls_hit_http_once():
    call_count = 0

    class _Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *_): pass
        async def request(self, method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            return _Resp()

    geocoder = GeoplateformeGeocoder()

    with patch("app.services.geocoding.geoplateforme.httpx.AsyncClient", return_value=_Client()):
        await geocoder.search("Paris")
        await geocoder.search("Paris")

    assert call_count == 1, "Le second appel identique doit être servi depuis le cache"
