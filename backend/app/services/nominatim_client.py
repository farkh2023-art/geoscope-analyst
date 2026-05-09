import httpx
from app.core.config import settings
from app.models.schemas import Coordinates, LocationResult, InputType

_MOCK_RESPONSE = LocationResult(
    coordinates=Coordinates(lat=48.8566, lon=2.3522),
    country="France",
    region="Île-de-France",
    department="Paris",
    city="Paris",
    neighborhood="1er Arrondissement",
    display_name="Paris, Île-de-France, France",
    input_type=InputType.gps,
)

_NOMINATIM_ERRORS = (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError)


async def reverse_geocode(coords: Coordinates) -> LocationResult:
    if settings.offline_mode:
        result = _MOCK_RESPONSE.model_copy()
        result.coordinates = coords
        return result

    url = f"{settings.nominatim_base_url}/reverse"
    params = {
        "lat": coords.lat,
        "lon": coords.lon,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 14,
    }
    headers = {"User-Agent": settings.nominatim_user_agent}

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except _NOMINATIM_ERRORS:
        return LocationResult(coordinates=coords, input_type=InputType.gps)

    addr = data.get("address", {})
    return LocationResult(
        coordinates=coords,
        country=addr.get("country", ""),
        region=addr.get("state", addr.get("region", "")),
        department=addr.get("county", addr.get("state_district", "")),
        city=addr.get("city", addr.get("town", addr.get("village", ""))),
        neighborhood=addr.get("suburb", addr.get("neighbourhood", addr.get("quarter", ""))),
        display_name=data.get("display_name", ""),
        input_type=InputType.gps,
    )


async def geocode_place(place_name: str) -> LocationResult:
    """Forward geocoding: place name → coordinates + admin data."""
    if settings.offline_mode:
        result = _MOCK_RESPONSE.model_copy()
        result.display_name = place_name + " (mode hors-ligne)"
        result.input_type = InputType.place_name
        return result

    url = f"{settings.nominatim_base_url}/search"
    params = {"q": place_name, "format": "jsonv2", "addressdetails": 1, "limit": 1}
    headers = {"User-Agent": settings.nominatim_user_agent}

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            results = resp.json()
    except _NOMINATIM_ERRORS:
        return LocationResult(display_name=place_name, input_type=InputType.place_name)

    if not results:
        return LocationResult(display_name=place_name, input_type=InputType.place_name)

    item = results[0]
    addr = item.get("address", {})
    coords = Coordinates(lat=float(item["lat"]), lon=float(item["lon"]))
    return LocationResult(
        coordinates=coords,
        country=addr.get("country", ""),
        region=addr.get("state", ""),
        department=addr.get("county", ""),
        city=addr.get("city", addr.get("town", addr.get("village", ""))),
        neighborhood=addr.get("suburb", ""),
        display_name=item.get("display_name", place_name),
        input_type=InputType.place_name,
    )
