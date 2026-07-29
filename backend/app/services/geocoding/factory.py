from app.core.config import settings
from app.services.geocoding.base import Geocoder
from app.services.geocoding.geoplateforme import GeoplateformeGeocoder
from app.services.geocoding.mock import MockGeocoder
from app.services.geocoding.nominatim import NominatimGeocoder

_instances: dict[str, Geocoder] = {}


def get_geocoder() -> Geocoder:
    """Un seul geocoder instancié par nom, réutilisé entre requêtes (cache/limiteur persistants)."""
    name = settings.geocoder
    if name not in _instances:
        if name == "mock":
            _instances[name] = MockGeocoder()
        elif name == "nominatim":
            _instances[name] = NominatimGeocoder()
        else:
            _instances[name] = GeoplateformeGeocoder()
    return _instances[name]
