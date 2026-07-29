import httpx

from app.core.config import settings
from app.models.schemas import Coordinates, InputType, LocationResult
from app.services.http_resilience import RateLimiter, request_with_retry
from app.services.ttl_cache import TTLCache

# Champs confirmés par appel réel à data.geopf.fr/geocodage/{search,reverse} et par
# components/schemas/AddressProperties du openapi.yaml du service (aucun champ deviné).
# `context` est une chaîne "depcode, département, région" (ex: "75, Paris, Île-de-France") ;
# il n'existe pas de champ région/département séparé dans l'API — on le découpe explicitement.
# `x`/`y` sont en projection Lambert93 (mètres) : les coordonnées WGS84 viennent uniquement
# de geometry.coordinates ([lon, lat]).


class GeoplateformeGeocoder:
    def __init__(self):
        self._limiter = RateLimiter(settings.rate_limit_per_second)
        self._cache = TTLCache(settings.cache_ttl_seconds)

    async def search(self, query: str) -> LocationResult:
        cache_key = ("search", query.strip().lower())
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached.model_copy()

        url = f"{settings.geopf_base_url}/search"
        params = {"q": query, "limit": 1}
        headers = {"User-Agent": settings.nominatim_user_agent}

        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
            resp = await request_with_retry(client, "GET", url, limiter=self._limiter, params=params, headers=headers)
            data = resp.json()

        features = data.get("features", [])
        if not features:
            return LocationResult(display_name=query, input_type=InputType.place_name)

        result = self._to_location_result(features[0], InputType.place_name, fallback_display=query)
        self._cache.set(cache_key, result)
        return result.model_copy()

    async def reverse(self, coords: Coordinates) -> LocationResult:
        cache_key = ("reverse", round(coords.lat, 5), round(coords.lon, 5))
        cached = self._cache.get(cache_key)
        if cached is not None:
            result = cached.model_copy()
            result.coordinates = coords
            return result

        url = f"{settings.geopf_base_url}/reverse"
        params = {"lon": coords.lon, "lat": coords.lat}
        headers = {"User-Agent": settings.nominatim_user_agent}

        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
            resp = await request_with_retry(client, "GET", url, limiter=self._limiter, params=params, headers=headers)
            data = resp.json()

        features = data.get("features", [])
        if not features:
            return LocationResult(coordinates=coords, input_type=InputType.gps)

        result = self._to_location_result(features[0], InputType.gps)
        result.coordinates = coords
        self._cache.set(cache_key, result)
        return result.model_copy()

    @staticmethod
    def _to_location_result(feature: dict, input_type: InputType, fallback_display: str = "") -> LocationResult:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords_raw = geom.get("coordinates")
        coordinates = None
        if coords_raw and len(coords_raw) == 2:
            coordinates = Coordinates(lat=coords_raw[1], lon=coords_raw[0])

        context = props.get("context", "")
        context_parts = [p.strip() for p in context.split(",")] if context else []
        department = context_parts[1] if len(context_parts) >= 2 else ""
        region = context_parts[2] if len(context_parts) >= 3 else ""

        return LocationResult(
            coordinates=coordinates,
            # data.geopf.fr ne géocode que des adresses françaises (BAN/BD TOPO/Parcellaire
            # Express) : "France" est une constante structurelle du service, pas une déduction.
            country="France",
            region=region,
            department=department,
            city=props.get("city", ""),
            neighborhood=props.get("district", ""),
            display_name=props.get("label", fallback_display),
            input_type=input_type,
            postcode=props.get("postcode", ""),
            citycode=props.get("citycode", ""),
        )
