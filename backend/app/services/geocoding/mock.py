from app.models.schemas import Coordinates, InputType, LocationResult

_MOCK_RESPONSE = LocationResult(
    coordinates=Coordinates(lat=48.8566, lon=2.3522),
    country="France",
    region="Île-de-France",
    department="Paris",
    city="Paris",
    neighborhood="1er Arrondissement",
    display_name="Paris, Île-de-France, France",
    input_type=InputType.gps,
    postcode="75001",
    citycode="75101",
)


class MockGeocoder:
    async def search(self, query: str) -> LocationResult:
        result = _MOCK_RESPONSE.model_copy()
        result.display_name = query + " (mode hors-ligne)"
        result.input_type = InputType.place_name
        return result

    async def reverse(self, coords: Coordinates) -> LocationResult:
        result = _MOCK_RESPONSE.model_copy()
        result.coordinates = coords
        return result
