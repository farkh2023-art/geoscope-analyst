import httpx
from app.core.config import settings
from app.models.schemas import Coordinates, Infrastructure

_MOCK_INFRASTRUCTURES = [
    Infrastructure(name="Route Nationale 1", type="highway", category="transport", osm_tags={"highway": "primary"}),
    Infrastructure(name="Gare du Nord", type="railway_station", category="transport", osm_tags={"railway": "station"}),
    Infrastructure(name="Hôpital Lariboisière", type="hospital", category="santé", osm_tags={"amenity": "hospital"}),
    Infrastructure(name="Lycée Jules Ferry", type="school", category="éducation", osm_tags={"amenity": "school"}),
    Infrastructure(name="Zone Industrielle Nord", type="industrial", category="industrie", osm_tags={"landuse": "industrial"}),
    Infrastructure(name="Parc des Buttes-Chaumont", type="park", category="environnement", osm_tags={"leisure": "park"}),
    Infrastructure(name="Canal Saint-Martin", type="waterway", category="eau", osm_tags={"waterway": "canal"}),
    Infrastructure(name="Centrale EDF Landy", type="power_plant", category="énergie", osm_tags={"power": "plant"}),
    Infrastructure(name="Mairie du 10e", type="public_building", category="administratif", osm_tags={"amenity": "townhall"}),
    Infrastructure(name="Université Paris-Diderot", type="university", category="éducation", osm_tags={"amenity": "university"}),
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
        return _MOCK_INFRASTRUCTURES

    query = _OVERPASS_QUERY_TEMPLATE.format(
        radius=radius_m, lat=coords.lat, lon=coords.lon
    )
    headers = {"User-Agent": settings.nominatim_user_agent, "Accept": "*/*"}
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
            resp = await client.post(settings.overpass_base_url, data={"data": query})
            resp.raise_for_status()
            data = resp.json()
        return _parse_elements(data.get("elements", []))
    except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError):
        return []


def _parse_elements(elements: list[dict]) -> list[Infrastructure]:
    results: list[Infrastructure] = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", tags.get("ref", "Sans nom"))
        infra_type = _infer_type(tags)
        category = _infer_category(tags)
        results.append(Infrastructure(
            name=name,
            type=infra_type,
            category=category,
            osm_tags={k: v for k, v in tags.items() if k in ("highway", "railway", "amenity", "landuse", "leisure", "waterway", "power", "aeroway")},
        ))
    return results


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
