import httpx

from app.core.config import settings
from app.models.schemas import Coordinates, InputType, LocationResult
from app.services.http_resilience import RateLimiter, request_with_retry
from app.services.ttl_cache import TTLCache


class NominatimGeocoder:
    def __init__(self):
        self._limiter = RateLimiter(settings.rate_limit_per_second)
        self._cache = TTLCache(settings.cache_ttl_seconds)

    async def reverse(self, coords: Coordinates) -> LocationResult:
        cache_key = ("reverse", round(coords.lat, 5), round(coords.lon, 5))
        cached = self._cache.get(cache_key)
        if cached is not None:
            result = cached.model_copy()
            result.coordinates = coords
            return result

        url = f"{settings.nominatim_base_url}/reverse"
        params = {"lat": coords.lat, "lon": coords.lon, "format": "jsonv2", "addressdetails": 1, "zoom": 14}
        headers = {"User-Agent": settings.nominatim_user_agent}

        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
            resp = await request_with_retry(client, "GET", url, limiter=self._limiter, params=params, headers=headers)
            data = resp.json()

        addr = data.get("address", {})
        result = LocationResult(
            coordinates=coords,
            country=addr.get("country", ""),
            region=addr.get("state", addr.get("region", "")),
            department=addr.get("county", addr.get("state_district", "")),
            city=addr.get("city", addr.get("town", addr.get("village", ""))),
            neighborhood=addr.get("suburb", addr.get("neighbourhood", addr.get("quarter", ""))),
            display_name=data.get("display_name", ""),
            input_type=InputType.gps,
            postcode=addr.get("postcode", ""),
        )
        self._cache.set(cache_key, result)
        return result.model_copy()

    async def search(self, query: str) -> LocationResult:
        cache_key = ("search", query.strip().lower())
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached.model_copy()

        url = f"{settings.nominatim_base_url}/search"
        params = {"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 1}
        headers = {"User-Agent": settings.nominatim_user_agent}

        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
            resp = await request_with_retry(client, "GET", url, limiter=self._limiter, params=params, headers=headers)
            results = resp.json()

        if not results:
            return LocationResult(display_name=query, input_type=InputType.place_name)

        item = results[0]
        addr = item.get("address", {})
        coords = Coordinates(lat=float(item["lat"]), lon=float(item["lon"]))
        result = LocationResult(
            coordinates=coords,
            country=addr.get("country", ""),
            region=addr.get("state", ""),
            department=addr.get("county", ""),
            city=addr.get("city", addr.get("town", addr.get("village", ""))),
            neighborhood=addr.get("suburb", ""),
            display_name=item.get("display_name", query),
            input_type=InputType.place_name,
            postcode=addr.get("postcode", ""),
        )
        self._cache.set(cache_key, result)
        return result.model_copy()
