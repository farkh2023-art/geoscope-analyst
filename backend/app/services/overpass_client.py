import logging

import httpx
from app.core.config import settings
from app.models.schemas import Activity, Coordinates, Infrastructure
from app.services.geo_utils import haversine_m
from app.services.role_classifier import infer_role

logger = logging.getLogger(__name__)

# Coordonnées réelles vérifiées via Nominatim/Overpass, toutes à moins de 1 500 m
# du centre mock (48.8566, 2.3522 — Hôtel de Ville / Île de la Cité, Paris).
# Chaque entrée correspond à un tag effectivement interrogé par _OVERPASS_QUERY_TEMPLATE.
_MOCK_INFRASTRUCTURES = [
    Infrastructure(name="Station de métro Hôtel de Ville", type="subway_entrance", category="transport", osm_tags={"railway": "subway_entrance"}, lat=48.8575406, lon=2.3515397),
    Infrastructure(name="Arrêt de bus Châtelet", type="bus_stop", category="transport", osm_tags={"highway": "bus_stop"}, lat=48.8577247, lon=2.3480784),
    Infrastructure(name="Lycée Charlemagne", type="school", category="education", osm_tags={"amenity": "school"}, lat=48.8544752, lon=2.3607483),
    Infrastructure(name="Université Paris 1 Panthéon-Sorbonne", type="university", category="education", osm_tags={"amenity": "university"}, lat=48.8470242, lon=2.3440467),
    Infrastructure(name="Boulangerie Beaubourg", type="bakery", category="commerce_alimentaire", osm_tags={"shop": "bakery"}, lat=48.8618726, lon=2.3516408),
    Infrastructure(name="McDonald's", type="fast_food", category="restauration", osm_tags={"amenity": "fast_food"}, lat=48.8579329, lon=2.3514870),
    Infrastructure(name="Chez Marianne", type="restaurant", category="restauration", osm_tags={"amenity": "restaurant"}, lat=48.8577309, lon=2.3586364),
    Infrastructure(name="Jean Claude Aubry Academy", type="hairdresser", category="services_personne", osm_tags={"shop": "hairdresser"}, lat=48.8610844, lon=2.3443462),
    Infrastructure(name="BNP Paribas", type="bank", category="services_personne", osm_tags={"amenity": "bank"}, lat=48.8530223, lon=2.3434038),
    Infrastructure(name="Pharmacie du Louvre", type="pharmacy", category="sante", osm_tags={"amenity": "pharmacy"}, lat=48.8621947, lon=2.3416613),
    Infrastructure(name="LePantalon Marais", type="clothes", category="commerce_non_alimentaire", osm_tags={"shop": "clothes"}, lat=48.8565503, lon=2.3573564),
    Infrastructure(name="Daniel Féau", type="estate_agent", category="bureaux", osm_tags={"office": "estate_agent"}, lat=48.8549424, lon=2.3624242),
    Infrastructure(name="MK2 Beaubourg", type="cinema", category="loisirs_culture", osm_tags={"amenity": "cinema"}, lat=48.8615738, lon=2.3524143),
    Infrastructure(name="Hôtel du Loiret", type="hotel", category="hebergement", osm_tags={"tourism": "hotel"}, lat=48.8569202, lon=2.3552931),
    Infrastructure(name="Parking Hôtel de Ville", type="parking", category="stationnement", osm_tags={"amenity": "parking"}, lat=48.8569481, lon=2.3497138),
]

# nwr (node/way/relation) : couvre aussi les commerces et équipements cartographiés en polygone.
# out center 200 : plafond documenté — une zone urbaine dense (centre de Paris) sature déjà
# cette limite avec shop=* seul ; au-delà, les résultats les plus éloignés dans l'ordre de
# réponse Overpass sont simplement absents (pas de troncature par distance côté serveur).
_OVERPASS_QUERY_TEMPLATE = """
[out:json][timeout:25];
(
  nwr["shop"](around:{radius},{lat},{lon});
  nwr["amenity"~"restaurant|fast_food|cafe|bar|pub|pharmacy|bank|post_office|cinema|library|school|kindergarten|college|university|parking|bus_station"](around:{radius},{lat},{lon});
  nwr["office"](around:{radius},{lat},{lon});
  nwr["leisure"~"fitness_centre|sports_centre"](around:{radius},{lat},{lon});
  nwr["tourism"~"hotel|guest_house"](around:{radius},{lat},{lon});
  nwr["highway"="bus_stop"](around:{radius},{lat},{lon});
  nwr["railway"~"station|subway_entrance|tram_stop"](around:{radius},{lat},{lon});
);
out center 200;
"""

_OSM_TAG_KEYS = ("shop", "amenity", "office", "leisure", "tourism", "highway", "railway")

_FOOD_SHOPS = {
    "bakery", "pastry", "butcher", "greengrocer", "convenience", "supermarket",
    "cheese", "seafood", "deli", "wine", "alcohol", "confectionery", "chocolate",
    "farm", "coffee", "tea",
}
_PERSONAL_SERVICE_SHOPS = {
    "hairdresser", "beauty", "massage", "tattoo", "dry_cleaning", "laundry",
    "tailor", "funeral_directors", "optician",
}


async def fetch_infrastructures(
    coords: Coordinates,
    radius_m: int,
    activity: Activity | None = None,
) -> list[Infrastructure]:
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

    return _finalize(candidates, coords, radius_m, activity)


def _finalize(
    infrastructures: list[Infrastructure],
    coords: Coordinates,
    radius_m: int,
    activity: Activity | None,
) -> list[Infrastructure]:
    results: list[Infrastructure] = []
    for infra in infrastructures:
        if infra.lat is None or infra.lon is None:
            continue
        distance = round(haversine_m(coords.lat, coords.lon, infra.lat, infra.lon))
        if distance > radius_m:
            continue
        role = infer_role(infra.osm_tags, infra.category, activity)
        results.append(infra.model_copy(update={"distance_m": distance, "role": role}))
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
            osm_tags={k: v for k, v in tags.items() if k in _OSM_TAG_KEYS},
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
    for key in _OSM_TAG_KEYS:
        if key in tags:
            return tags[key]
    return "unknown"


def _infer_category(tags: dict) -> str:
    shop = tags.get("shop")
    amenity = tags.get("amenity")
    office = tags.get("office")
    leisure = tags.get("leisure")
    tourism = tags.get("tourism")
    highway = tags.get("highway")
    railway = tags.get("railway")

    if shop:
        if shop in _FOOD_SHOPS:
            return "commerce_alimentaire"
        if shop in _PERSONAL_SERVICE_SHOPS:
            return "services_personne"
        return "commerce_non_alimentaire"
    if amenity in ("restaurant", "fast_food", "cafe", "bar", "pub"):
        return "restauration"
    if amenity in ("bank", "post_office"):
        return "services_personne"
    if amenity == "pharmacy":
        return "sante"
    if amenity in ("school", "kindergarten", "college", "university"):
        return "education"
    if amenity in ("cinema", "library"):
        return "loisirs_culture"
    if amenity == "parking":
        return "stationnement"
    if amenity == "bus_station":
        return "transport"
    if office:
        return "bureaux"
    if leisure in ("fitness_centre", "sports_centre"):
        return "loisirs_culture"
    if tourism in ("hotel", "guest_house"):
        return "hebergement"
    if highway == "bus_stop":
        return "transport"
    if railway in ("station", "subway_entrance", "tram_stop"):
        return "transport"
    return "autre"
