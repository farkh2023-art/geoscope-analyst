from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AnalysisMode(str, Enum):
    flash = "flash"
    analyst = "analyst"
    full = "full"


class InputType(str, Enum):
    gps = "gps"
    google_maps_url = "google_maps_url"
    osm_url = "osm_url"
    place_name = "place_name"
    free_text = "free_text"
    image = "image"
    unknown = "unknown"


class AnalyzeRequest(BaseModel):
    input: str = Field(..., description="GPS coords, URL, place name or free text")
    radius_m: int = Field(default=1500, ge=100, le=50000)
    mode: AnalysisMode = AnalysisMode.analyst


class Coordinates(BaseModel):
    lat: float
    lon: float


class LocationResult(BaseModel):
    coordinates: Coordinates | None = None
    country: str = ""
    region: str = ""
    department: str = ""
    city: str = ""
    neighborhood: str = ""
    display_name: str = ""
    input_type: InputType = InputType.unknown


class ConfidenceResult(BaseModel):
    score: int = Field(ge=0, le=100)
    label: str  # faible / moyen / élevé
    justification: str


class Infrastructure(BaseModel):
    name: str
    type: str
    category: str
    osm_tags: dict[str, str] = {}
    source: str = "OpenStreetMap"
    lat: float | None = None
    lon: float | None = None
    distance_m: int | None = None


class ReportSection(BaseModel):
    title: str
    content: str


class AnalyzeResponse(BaseModel):
    location: LocationResult
    confidence: ConfidenceResult
    infrastructures: list[Infrastructure]
    report: dict[str, Any]
    sources: list[str]
    warnings: list[str]


class ExportRequest(BaseModel):
    location: LocationResult
    confidence: ConfidenceResult
    infrastructures: list[Infrastructure]
    report: dict[str, Any]
    sources: list[str]
    warnings: list[str]


class MapDataResponse(BaseModel):
    geojson: dict[str, Any]
    center: Coordinates | None = None
    radius_m: int
    tile_url: str
