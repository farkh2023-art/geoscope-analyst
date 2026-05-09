from app.models.schemas import (
    AnalysisMode,
    ConfidenceResult,
    Infrastructure,
    LocationResult,
)
from app.services.infrastructure_classifier import classify_by_category, summarize_categories


def generate_report(
    location: LocationResult,
    confidence: ConfidenceResult,
    infrastructures: list[Infrastructure],
    mode: AnalysisMode,
    radius_m: int,
) -> dict:
    grouped = classify_by_category(infrastructures)
    present_categories = summarize_categories(infrastructures)

    coords_str = (
        f"{location.coordinates.lat}, {location.coordinates.lon}"
        if location.coordinates
        else "Non disponibles"
    )

    zone_type = _infer_zone_type(grouped)

    report: dict = {
        "resume_executif": _build_summary(location, confidence, zone_type, len(infrastructures)),
        "identification_administrative": {
            "pays": location.country or "Inconnu",
            "region": location.region or "Inconnue",
            "departement": location.department or "Inconnu",
            "ville": location.city or "Inconnue",
            "quartier": location.neighborhood or "Inconnu",
            "adresse_complete": location.display_name or "Non disponible",
        },
        "coordonnees_et_rayon": {
            "coordonnees": coords_str,
            "rayon_analyse_m": radius_m,
        },
        "description_zone": _describe_zone(zone_type, present_categories),
        "infrastructures": {cat: [i.name for i in items] for cat, items in grouped.items() if items},
        "niveau_confiance": {
            "score": confidence.score,
            "label": confidence.label,
            "justification": confidence.justification,
        },
        "limites_analyse": _build_limits(location, infrastructures),
        "sources": _list_sources(location),
    }

    if mode in (AnalysisMode.analyst, AnalysisMode.full):
        report["connectivite"] = _describe_connectivity(grouped)
        report["activites_economiques_probables"] = _infer_economy(grouped)

    if mode == AnalysisMode.full:
        report["occupation_du_sol_estimee"] = _estimate_land_use(grouped, zone_type)
        report["sensibilites_environnementales"] = _environmental_notes(grouped)
        report["contexte_territorial"] = _territorial_context(location, zone_type)

    return report


def _build_summary(loc: LocationResult, conf: ConfidenceResult, zone_type: str, n_infra: int) -> str:
    place = loc.display_name or loc.city or loc.country or "Zone inconnue"
    return (
        f"Analyse géospatiale de {place}. "
        f"Zone identifiée comme {zone_type}. "
        f"{n_infra} infrastructure(s) détectée(s). "
        f"Niveau de confiance : {conf.label} ({conf.score}/100)."
    )


def _describe_zone(zone_type: str, categories: list[str]) -> str:
    desc = f"Zone à dominante {zone_type}."
    if categories:
        desc += f" Secteurs présents : {', '.join(categories)}."
    return desc


def _infer_zone_type(grouped: dict) -> str:
    if grouped.get("industrie"):
        return "industrielle"
    if grouped.get("transport") and grouped.get("administratif"):
        return "urbaine dense"
    if grouped.get("environnement") and not grouped.get("transport"):
        return "naturelle / rurale"
    if grouped.get("santé") or grouped.get("éducation"):
        return "urbaine résidentielle"
    return "mixte"


def _describe_connectivity(grouped: dict) -> str:
    transport = grouped.get("transport", [])
    if not transport:
        return "Connectivité faible ou non détectée."
    types = {i.type for i in transport}
    parts = []
    if any("railway" in t or "station" in t for t in types):
        parts.append("réseau ferroviaire")
    if any("highway" in t or "motorway" in t or "primary" in t for t in types):
        parts.append("axes routiers principaux")
    if any("airport" in t or "aerodrome" in t for t in types):
        parts.append("infrastructure aéroportuaire")
    return "Bonne connectivité via " + ", ".join(parts) + "." if parts else "Réseau de transport présent."


def _infer_economy(grouped: dict) -> str:
    clues = []
    if grouped.get("industrie"):
        clues.append("activité industrielle et logistique")
    if grouped.get("éducation"):
        clues.append("services d'enseignement")
    if grouped.get("santé"):
        clues.append("services de santé")
    if grouped.get("transport"):
        clues.append("économie liée aux flux et mobilités")
    return ", ".join(clues).capitalize() + "." if clues else "Activités économiques non déterminées avec les données disponibles."


def _estimate_land_use(grouped: dict, zone_type: str) -> str:
    if zone_type == "industrielle":
        return "Majorité bâti industriel, zones logistiques, faible couverture végétale."
    if zone_type == "naturelle / rurale":
        return "Dominance végétation / agriculture, faible densité bâtie."
    return "Usage mixte : résidentiel, tertiaire, espaces publics."


def _environmental_notes(grouped: dict) -> str:
    notes = []
    if grouped.get("eau"):
        notes.append("Présence de cours d'eau ou zones humides — risques d'inondation possibles")
    if grouped.get("environnement"):
        notes.append("Espaces naturels protégés ou parcs identifiés")
    if grouped.get("énergie"):
        notes.append("Infrastructures énergétiques présentes — zones de sensibilité industrielle")
    return "; ".join(notes) + "." if notes else "Aucune sensibilité environnementale majeure identifiée."


def _territorial_context(loc: LocationResult, zone_type: str) -> str:
    city = loc.city or "la zone"
    return (
        f"{city} se présente comme une zone {zone_type} "
        f"au sein de {loc.region or loc.country or 'la région'}. "
        "Les données publiques disponibles suggèrent une centralité locale modérée à forte."
    )


def _build_limits(loc: LocationResult, infrastructures: list[Infrastructure]) -> list[str]:
    limits = []
    if loc.coordinates is None:
        limits.append("Aucune coordonnée GPS : localisation basée sur le géocodage textuel, moins précise.")
    if len(infrastructures) < 3:
        limits.append("Peu d'infrastructures détectées : couverture OSM peut être incomplète dans cette zone.")
    limits.append("Données issues de sources publiques ouvertes uniquement (OSM, Nominatim).")
    limits.append("Les éléments déduits ou probables sont à vérifier sur le terrain.")
    return limits


def _list_sources(loc: LocationResult) -> list[str]:
    sources = ["OpenStreetMap / Nominatim — https://nominatim.openstreetmap.org"]
    if loc.coordinates:
        sources.append("Overpass API — https://overpass-api.de")
    return sources
