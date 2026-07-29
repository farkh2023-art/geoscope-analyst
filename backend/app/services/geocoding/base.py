from typing import Protocol

from app.models.schemas import Coordinates, LocationResult


class Geocoder(Protocol):
    async def search(self, query: str) -> LocationResult: ...
    async def reverse(self, coords: Coordinates) -> LocationResult: ...
