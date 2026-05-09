import re
from app.models.schemas import Coordinates

_PLAIN = re.compile(r"^([+-]?\d{1,3}\.\d+)\s*[,;]\s*([+-]?\d{1,3}\.\d+)$")
_LABELED = re.compile(
    r"lat[:\s]+([+-]?\d+\.\d+).*?lon[:\s]+([+-]?\d+\.\d+)", re.IGNORECASE
)
_GMAPS_AT = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
_GMAPS_Q = re.compile(r"[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)")


def parse_coordinates(raw: str) -> Coordinates | None:
    raw = raw.strip()

    m = _PLAIN.match(raw)
    if m:
        return _make(m.group(1), m.group(2))

    m = _LABELED.search(raw)
    if m:
        return _make(m.group(1), m.group(2))

    m = _GMAPS_AT.search(raw)
    if m:
        return _make(m.group(1), m.group(2))

    m = _GMAPS_Q.search(raw)
    if m:
        return _make(m.group(1), m.group(2))

    return None


def _make(lat_str: str, lon_str: str) -> Coordinates | None:
    try:
        lat, lon = float(lat_str), float(lon_str)
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return Coordinates(lat=lat, lon=lon)
    except ValueError:
        pass
    return None
