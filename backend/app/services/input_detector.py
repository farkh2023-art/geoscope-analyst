import re
from app.models.schemas import InputType

_GPS_PATTERN = re.compile(
    r"^[+-]?\d{1,3}\.\d+\s*[,;]\s*[+-]?\d{1,3}\.\d+"
)
_GPS_LABELED = re.compile(
    r"lat[:\s]+([+-]?\d+\.\d+).*?lon[:\s]+([+-]?\d+\.\d+)", re.IGNORECASE
)
_GMAPS_URL = re.compile(r"google\.com/maps")
_GMAPS_AT = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
_GMAPS_Q = re.compile(r"[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)")
_OSM_URL = re.compile(r"openstreetmap\.org")
_IMAGE_EXTENSIONS = re.compile(r"\.(png|jpg|jpeg|webp|tiff|bmp)$", re.IGNORECASE)


def detect_input_type(raw: str) -> InputType:
    raw = raw.strip()

    if _IMAGE_EXTENSIONS.search(raw):
        return InputType.image

    if _GMAPS_URL.search(raw):
        return InputType.google_maps_url

    if _OSM_URL.search(raw):
        return InputType.osm_url

    if _GPS_PATTERN.match(raw) or _GPS_LABELED.search(raw):
        return InputType.gps

    return InputType.place_name
