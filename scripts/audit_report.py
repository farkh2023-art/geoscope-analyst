#!/usr/bin/env python
"""
Script d'audit de véracité — appelle la chaîne complète (géocodage Géoplateforme +
Overpass + génération de rapport) sur une adresse réelle, en mode en ligne, et écrit
le résultat en Markdown dans audits/.

Force le mode en ligne (OFFLINE_MODE=false, GEOCODER=geoplateforme) quel que soit le
contenu de backend/.env, pour garantir que l'audit porte sur les vraies API et non sur
des données mockées.

Usage :
    python scripts/audit_report.py "<adresse>" [activité] [--radius 1500] [--mode full]

Exemple :
    python scripts/audit_report.py "78 Rue Montorgueil, Paris" boulangerie --radius 500
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Doit précéder tout import de app.* : Settings() est instancié à l'import de app.core.config.
os.environ["OFFLINE_MODE"] = "false"
os.environ["GEOCODER"] = "geoplateforme"
os.environ.setdefault("APP_ENV", "audit")

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND_DIR))

from app.models.schemas import Activity, AnalysisMode, AnalyzeResponse  # noqa: E402
from app.services.confidence_scoring import compute_confidence  # noqa: E402
from app.services.coordinate_parser import parse_coordinates  # noqa: E402
from app.services.geocoding.factory import get_geocoder  # noqa: E402
from app.services.input_detector import detect_input_type  # noqa: E402
from app.services.markdown_exporter import export_to_markdown  # noqa: E402
from app.services.overpass_client import fetch_infrastructures  # noqa: E402
from app.services.report_generator import generate_report  # noqa: E402


async def run_audit(address: str, activity: str | None, radius_m: int, mode: str) -> str:
    input_type = detect_input_type(address)
    coords = parse_coordinates(address)
    geocoder = get_geocoder()

    location = await geocoder.reverse(coords) if coords else await geocoder.search(address)
    location.input_type = input_type

    activity_enum = Activity(activity) if activity else None

    infrastructures = []
    if location.coordinates:
        infrastructures = await fetch_infrastructures(location.coordinates, radius_m, activity_enum)
    else:
        print(f"AVERTISSEMENT : géocodage sans coordonnées pour {address!r} — infrastructures non récupérées.", file=sys.stderr)

    confidence = compute_confidence(location, infrastructures)
    mode_enum = AnalysisMode(mode)
    report = generate_report(location, confidence, infrastructures, mode_enum, radius_m)
    sources = report.pop("sources", [])

    response = AnalyzeResponse(
        location=location,
        confidence=confidence,
        infrastructures=infrastructures,
        report=report,
        sources=sources,
        warnings=[],
    )
    return export_to_markdown(response)


def _slugify(text: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in text.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:60]


def main():
    parser = argparse.ArgumentParser(description="Audit de véracité GeoScope Analyst (mode en ligne).")
    parser.add_argument("address", help="Adresse réelle à analyser")
    parser.add_argument("activity", nargs="?", default=None, choices=[a.value for a in Activity], help="Activité analysée")
    parser.add_argument("--radius", type=int, default=1500)
    parser.add_argument("--mode", default="full", choices=[m.value for m in AnalysisMode])
    parser.add_argument("--out", default=None, help="Chemin de sortie (défaut : audits/<adresse-slugifiée>.md)")
    args = parser.parse_args()

    md = asyncio.run(run_audit(args.address, args.activity, args.radius, args.mode))

    out_dir = Path(__file__).resolve().parent.parent / "audits"
    out_dir.mkdir(exist_ok=True)
    out_path = Path(args.out) if args.out else out_dir / f"{_slugify(args.address)}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"Rapport écrit : {out_path}")


if __name__ == "__main__":
    main()
