from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.safety import check_input_safety
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ExportRequest,
    InputType,
    LocationResult,
    MapDataResponse,
)
from app.services.confidence_scoring import compute_confidence
from app.services.coordinate_parser import parse_coordinates
from app.services.input_detector import detect_input_type
from app.services.markdown_exporter import export_to_markdown
from app.services.nominatim_client import geocode_place, reverse_geocode
from app.services.overpass_client import fetch_infrastructures
from app.services.report_generator import generate_report

_EXTERNAL_ERRORS = (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, OSError)

_VERSION = "0.3.0"

app = FastAPI(
    title="GeoScope Analyst",
    description="Super agent géospatial — analyse territoriale publique",
    version=_VERSION,
)

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=(_STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": _VERSION,
        "offline_mode": settings.offline_mode,
        "env": settings.app_env,
        "map_tile_url": settings.map_tile_url,
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    warnings = check_input_safety(req.input)

    input_type = detect_input_type(req.input)
    coords     = parse_coordinates(req.input)

    # Geocoding — dégradation gracieuse si service indisponible
    try:
        location = await reverse_geocode(coords) if coords else await geocode_place(req.input)
    except Exception:
        location = LocationResult(
            coordinates=coords,
            display_name=req.input,
            input_type=input_type,
        )
        warnings.append("Service de géocodage indisponible — localisation partielle.")

    location.input_type = input_type

    if req.activity is None:
        warnings.append(
            "Aucune activité sélectionnée : les concurrents ne peuvent pas être identifiés "
            "(rôle « concurrent » jamais attribué)."
        )

    # Infrastructures — dégradation gracieuse si service indisponible
    if location.coordinates:
        try:
            infrastructures = await fetch_infrastructures(location.coordinates, req.radius_m, req.activity)
        except Exception:
            infrastructures = []
            warnings.append("Service Overpass indisponible — infrastructures non récupérées.")
    else:
        infrastructures = []
        warnings.append("Impossible de récupérer les infrastructures sans coordonnées.")

    confidence = compute_confidence(location, infrastructures)

    if req.mode.value == "flash":
        infrastructures = infrastructures[:5]

    report  = generate_report(location, confidence, infrastructures, req.mode, req.radius_m)
    sources = report.pop("sources", [])

    return AnalyzeResponse(
        location=location,
        confidence=confidence,
        infrastructures=infrastructures,
        report=report,
        sources=sources,
        warnings=warnings,
    )


@app.post("/api/map-data", response_model=MapDataResponse)
async def map_data(req: AnalyzeRequest):
    """Retourne les données prêtes pour la carte (GeoJSON-compatible)."""
    input_type = detect_input_type(req.input)
    coords     = parse_coordinates(req.input)

    location = await reverse_geocode(coords) if coords else await geocode_place(req.input)
    location.input_type = input_type

    infrastructures = []
    if location.coordinates:
        infrastructures = await fetch_infrastructures(location.coordinates, req.radius_m, req.activity)

    features = []
    if location.coordinates:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [location.coordinates.lon, location.coordinates.lat]},
            "properties": {
                "name": location.display_name or location.city or "Localisation",
                "marker_type": "location",
                "city": location.city,
                "country": location.country,
            },
        })
    for infra in infrastructures:
        if infra.lat is None or infra.lon is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [infra.lon, infra.lat]},
            "properties": {
                "name": infra.name,
                "type": infra.type,
                "category": infra.category,
                "role": infra.role,
                "source": infra.source,
                "marker_type": "infrastructure",
                "distance_m": infra.distance_m,
            },
        })

    return MapDataResponse(
        geojson={"type": "FeatureCollection", "features": features},
        center=location.coordinates,
        radius_m=req.radius_m,
        tile_url=settings.map_tile_url,
    )


@app.post("/api/export/markdown", response_class=PlainTextResponse)
async def export_markdown(req: ExportRequest):
    md = export_to_markdown(AnalyzeResponse(
        location=req.location,
        confidence=req.confidence,
        infrastructures=req.infrastructures,
        report=req.report,
        sources=req.sources,
        warnings=req.warnings,
    ))
    return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")
