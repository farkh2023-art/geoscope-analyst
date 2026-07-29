from app.models.schemas import Coordinates
from app.services.geocoding.mock import MockGeocoder


async def test_mock_reverse_returns_coordinates_as_given():
    geocoder = MockGeocoder()
    coords = Coordinates(lat=45.75, lon=4.85)
    result = await geocoder.reverse(coords)
    assert result.coordinates == coords
    assert result.country == "France"


async def test_mock_search_returns_a_result():
    geocoder = MockGeocoder()
    result = await geocoder.search("Bordeaux")
    assert result.coordinates is not None
    assert "hors-ligne" in result.display_name
