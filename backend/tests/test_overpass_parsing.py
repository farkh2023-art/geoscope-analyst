from app.models.schemas import Coordinates
from app.services.overpass_client import _infer_category, _parse_elements, fetch_infrastructures


def test_node_way_and_missing_coords():
    elements = [
        {"type": "node", "lat": 48.8600, "lon": 2.3500, "tags": {"amenity": "hospital", "name": "Hôpital A"}},
        {"type": "way", "center": {"lat": 48.8610, "lon": 2.3510}, "tags": {"amenity": "school", "name": "École B"}},
        {"type": "node", "tags": {"amenity": "school", "name": "Sans coordonnées"}},
    ]

    results = _parse_elements(elements)

    assert len(results) == 2
    names = {r.name for r in results}
    assert names == {"Hôpital A", "École B"}

    hopital = next(r for r in results if r.name == "Hôpital A")
    assert hopital.lat == 48.8600
    assert hopital.lon == 2.3500

    ecole = next(r for r in results if r.name == "École B")
    assert ecole.lat == 48.8610
    assert ecole.lon == 2.3510


def test_relation_uses_center():
    elements = [
        {"type": "relation", "center": {"lat": 48.8470, "lon": 2.3440}, "tags": {"amenity": "university", "name": "Université X"}},
    ]

    results = _parse_elements(elements)

    assert len(results) == 1
    assert results[0].lat == 48.8470
    assert results[0].lon == 2.3440


async def test_fetch_infrastructures_sorted_by_distance():
    result = await fetch_infrastructures(Coordinates(lat=48.8566, lon=2.3522), 1500)

    assert len(result) > 1
    distances = [i.distance_m for i in result]
    assert distances == sorted(distances)
    assert all(d <= 1500 for d in distances)


def test_way_with_shop_bakery_is_commerce_alimentaire():
    elements = [
        {"type": "way", "center": {"lat": 48.8600, "lon": 2.3500}, "tags": {"shop": "bakery", "name": "Boulangerie Test"}},
    ]

    results = _parse_elements(elements)

    assert len(results) == 1
    assert results[0].category == "commerce_alimentaire"


def test_unknown_tag_defaults_to_autre_without_exception():
    category = _infer_category({"shop": "some_never_seen_shop_type"})
    assert category == "commerce_non_alimentaire"

    category = _infer_category({"amenity": "some_never_seen_amenity"})
    assert category == "autre"

    category = _infer_category({})
    assert category == "autre"
