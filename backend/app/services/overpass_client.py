import logging

import httpx
from app.core.config import settings
from app.models.schemas import Coordinates, Infrastructure
from app.services.geo_utils import haversine_m

logger = logging.getLogger(__name__)

# Coordonnées réelles vérifiées via Nominatim/Overpass, toutes à moins de 1 500 m
# du centre mock (48.8566, 2.3522 — Hôtel de Ville / Île de la Cité, Paris).
_MOCK_INFRASTRUCTURES = [
    Infrastructure(name="Station de métro Hôtel de Ville", type="station", category="transport", osm_tags={"railway": "station"}, lat=48.8575406, lon=2.3515397),
    Infrastructure(name="Station de métro Châtelet", type="station", category="transport", osm_tags={"railway": "station"}, lat=48.8587782, lon=2.3474106),
    Infrastructure(name="Châtelet – Les Halles (gare)", type="station", category="transport", osm_tags={"railway": "station"}, lat=48.8616374, lon=2.3470441),
    Infrastructure(name="Préfecture de Police de Paris", type="police", category="administratif", osm_tags={"amenity": "police"}, lat=48.8571057, lon=2.3486990),
    Infrastructure(name="Hôtel-Dieu de Paris", type="hospital", category="santé", osm_tags={"amenity": "hospital"}, lat=48.8546261, lon=2.3488485),
    Infrastructure(name="Lycée Charlemagne", type="school", category="éducation", osm_tags={"amenity": "school"}, lat=48.8544752, lon=2.3607483),
    Infrastructure(name="Université Paris 1 Panthéon-Sorbonne", type="university", category="éducation", osm_tags={"amenity": "university"}, lat=48.8470242, lon=2.3440467),
    Infrastructure(name="Cathédrale Notre-Dame de Paris", type="place_of_worship", category="autre", osm_tags={"amenity": "place_of_worship"}, lat=48.8529371, lon=2.3500501),
    Infrastructure(name="Square Jean XXIII", type="park", category="environnement", osm_tags={"leisure": "park"}, lat=48.8523474, lon=2.3512693),
    Infrastructure(name="La Seine", type="river", category="eau", osm_tags={"waterway": "river"}, lat=48.8558089, lon=2.3490362),
]

_OVERPASS_QUERY_TEMPLATE = """
[out:json][timeout:25];
(
  node["amenity"~"hospital|clinic|school|university|college|townhall|fire_station|police"](around:{radius},{lat},{lon});
  node["railway"~"station|halt|tram_stop"](around:{radius},{lat},{lon});
  node["aeroway"~"aerodrome|airport"](around:{radius},{lat},{lon});
  node["power"~"plant|generator|substation"](around:{radius},{lat},{lon});
  way["landuse"~"industrial|military|commercial"](around:{radius},{lat},{lon});
  way["leisure"~"park|nature_reserve|garden"](around:{radius},{lat},{lon});
  way["waterway"~"river|canal"](around:{radius},{lat},{lon});
);
out center 40;
"""


async def fetch_infrastructures(coords: Coordinates, radius_m: int) -> list[Infrastructure]:
    if settings.offline_mode:
        candidates = list(_MOCK_INFRASTRUCTURES)
    else:
        query = _OVERPASS_QUERY_TEMPLATE.format(
            radius=radius_m, lat=coords.lat, lon=coords.lon
        )
        headers = {"User-Agent": settings.nominatim_user_agent, "Accept": "*/*"}
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
                resp = await client.post(settings.overpass_base_url, data={"data": query})
                resp.raise_for_status()
                data = resp.json()
            candidates = _parse_elements(data.get("elements", []))
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError):
            return []

    return _with_distances(candidates, coords, radius_m)


def _with_distances(infrastructures: list[Infrastructure], coords: Coordinates, radius_m: int) -> list[Infrastructure]:
    results: list[Infrastructure] = []
    for infra in infrastructures:
        if infra.lat is None or infra.lon is None:
            continue
        distance = round(haversine_m(coords.lat, coords.lon, infra.lat, infra.lon))
        if distance > radius_m:
            continue
        results.append(infra.model_copy(update={"distance_m": distance}))
    results.sort(key=lambda i: i.distance_m)
    return results


def _parse_elements(elements: list[dict]) -> list[Infrastructure]:
    results: list[Infrastructure] = []
    skipped = 0
    for el in elements:
        lat, lon = _extract_coords(el)
        if lat is None or lon is None:
            skipped += 1
            continue

        tags = el.get("tags", {})
        name = tags.get("name", tags.get("ref", "Sans nom"))
        infra_type = _infer_type(tags)
        category = _infer_category(tags)
        results.append(Infrastructure(
            name=name,
            type=infra_type,
            category=category,
            osm_tags={k: v for k, v in tags.items() if k in ("highway", "railway", "amenity", "landuse", "leisure", "waterway", "power", "aeroway")},
            lat=lat,
            lon=lon,
        ))

    if skipped:
        logger.warning("%d élément(s) Overpass écarté(s) faute de coordonnées exploitables", skipped)

    return results


def _extract_coords(el: dict) -> tuple[float | None, float | None]:
    if el.get("type") == "node":
        return el.get("lat"), el.get("lon")
    center = el.get("center")
    if center:
        return center.get("lat"), center.get("lon")
    return None, None


def _infer_type(tags: dict) -> str:
    for key in ("amenity", "highway", "railway", "landuse", "leisure", "waterway", "power", "aeroway"):
        if key in tags:
            return tags[key]
    return "unknown"


def _infer_category(tags: dict) -> str:
    amenity = tags.get("amenity", "")
    if amenity in ("hospital", "clinic", "doctors"):
        return "santé"
    if amenity in ("school", "university", "college"):
        return "éducation"
    if amenity in ("townhall", "police", "fire_station", "courthouse"):
        return "administratif"
    if "railway" in tags or tags.get("highway") in ("motorway", "trunk", "primary", "secondary"):
        return "transport"
    if "aeroway" in tags:
        return "transport"
    if tags.get("landuse") == "industrial":
        return "industrie"
    if "leisure" in tags:
        return "environnement"
    if "waterway" in tags:
        return "eau"
    if "power" in tags:
        return "énergie"
    return "autre"
