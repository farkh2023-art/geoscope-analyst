from app.models.schemas import Activity
from app.services.overpass_client import _infer_category
from app.services.role_classifier import infer_role


def test_boulangerie_bakery_is_concurrent():
    tags = {"shop": "bakery"}
    category = _infer_category(tags)
    assert infer_role(tags, category, Activity.boulangerie) == "concurrent"


def test_boulangerie_railway_station_is_flux():
    tags = {"railway": "station"}
    category = _infer_category(tags)
    assert infer_role(tags, category, Activity.boulangerie) == "flux"


def test_boulangerie_restaurant_is_autre():
    tags = {"amenity": "restaurant"}
    category = _infer_category(tags)
    assert infer_role(tags, category, Activity.boulangerie) == "autre"


def test_no_activity_never_yields_concurrent():
    samples = [
        {"shop": "bakery"},
        {"shop": "hairdresser"},
        {"amenity": "restaurant"},
        {"amenity": "pharmacy"},
    ]
    for tags in samples:
        category = _infer_category(tags)
        assert infer_role(tags, category, None) != "concurrent"
