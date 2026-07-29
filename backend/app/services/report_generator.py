from app.models.schemas import (
    AnalysisMode,
    ConfidenceResult,
    Infrastructure,
    LocationResult,
)
from app.services.infrastructure_classifier import classify_by_category
from app.services.overpass_client import OVERPASS_ELEMENT_CAP

# Catégories à vocation économique (commerce, service, bureau) — exclut transport et
# stationnement, qui sont des générateurs de flux plutôt que des activités économiques.
_ECONOMIC_CATEGORIES = {
    "commerce_alimentaire", "restauration", "services_personne",
    "commerce_non_alimentaire", "sante", "bureaux", "loisirs_culture", "hebergement",
}


def generate_report(
    location: LocationResult,
    confidence: ConfidenceResult,
    infrastructures: list[Infrastructure],
    mode: AnalysisMode,
    radius_m: int,
) -> dict:
    # Les comptages narratifs (résumé, connectivité, économie...) portent toujours sur la
    # liste complète, jamais sur un sous-ensemble tronqué : en mode flash, seul l'AFFICHAGE
    # détaillé des infrastructures est limité, avec mention explicite de la troncature.
    grouped = classify_by_category(infrastructures)
    n_total = len(infrastructures)

    display_infrastructures = infrastructures
    truncation_note = None
    if mode == AnalysisMode.flash and n_total > 5:
        display_infrastructures = infrastructures[:5]
        truncation_note = (
            f"Mode flash : 5 infrastructures affichées ci-dessous sur {n_total} recensées au total."
        )
    display_grouped = classify_by_category(display_infrastructures)

    coords_str = (
        f"{location.coordinates.lat}, {location.coordinates.lon}"
        if location.coordinates
        else "Non disponibles"
    )

    limits = _build_limits(location, infrastructures)
    if truncation_note:
        limits.append(truncation_note)

    report: dict = {
        "resume_executif": _build_summary(location, confidence, infrastructures, radius_m),
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
        "description_zone": _describe_zone(grouped, n_total),
        "infrastructures": {cat: [_format_infra(i) for i in items] for cat, items in display_grouped.items() if items},
        "niveau_confiance": {
            "score": confidence.score,
            "label": confidence.label,
            "justification": confidence.justification,
        },
        "limites_analyse": limits,
        "sources": _list_sources(location),
    }

    if mode in (AnalysisMode.analyst, AnalysisMode.full):
        report["connectivite"] = _describe_connectivity(grouped)
        report["activites_economiques_probables"] = _infer_economy(grouped)

    if mode == AnalysisMode.full:
        report["contexte_territorial"] = _territorial_context(location, infrastructures)

    return report


def _format_infra(infra: Infrastructure) -> str:
    if infra.distance_m is not None:
        return f"{infra.name} — {infra.distance_m} m"
    return f"{infra.name} — position non cartographiée"


def _nearest(infrastructures: list[Infrastructure]) -> Infrastructure | None:
    located = [i for i in infrastructures if i.distance_m is not None]
    return min(located, key=lambda i: i.distance_m) if located else None


def _build_summary(
    loc: LocationResult,
    conf: ConfidenceResult,
    infrastructures: list[Infrastructure],
    radius_m: int,
) -> str:
    place = loc.display_name or loc.city or loc.country or "Zone inconnue"
    n_total = len(infrastructures)
    n_concurrents = sum(1 for i in infrastructures if i.role == "concurrent")
    nearest = _nearest(infrastructures)
    nearest_part = (
        f" Établissement le plus proche : {nearest.name} ({nearest.distance_m} m)."
        if nearest else ""
    )
    return (
        f"Analyse de {place} sur un rayon de {radius_m} m. "
        f"{n_total} établissement(s) recensé(s), dont {n_concurrents} concurrent(s) direct(s) identifié(s)."
        f"{nearest_part} "
        f"Niveau de confiance : {conf.label} ({conf.score}/100)."
    )


def _describe_zone(grouped: dict, n_total: int) -> str:
    if n_total == 0:
        return "0 infrastructure recensée dans le rayon d'analyse."
    counts = sorted(
        ((cat, len(items)) for cat, items in grouped.items() if items),
        key=lambda x: -x[1],
    )
    breakdown = ", ".join(f"{cat} ({n})" for cat, n in counts)
    return f"{n_total} infrastructure(s) recensée(s) dans le rayon d'analyse. Répartition par catégorie : {breakdown}."


def _describe_connectivity(grouped: dict) -> str:
    transport = sorted(
        (i for i in grouped.get("transport", []) if i.distance_m is not None),
        key=lambda i: i.distance_m,
    )
    if not transport:
        return "0 infrastructure de transport recensée dans le rayon d'analyse."
    shown = ", ".join(f"{i.name} ({i.distance_m} m)" for i in transport[:5])
    extra = f" (+{len(transport) - 5} autre(s))" if len(transport) > 5 else ""
    return f"{len(transport)} infrastructure(s) de transport recensée(s) : {shown}{extra}."


def _infer_economy(grouped: dict) -> str:
    counts = sorted(
        ((cat, len(items)) for cat, items in grouped.items() if items and cat in _ECONOMIC_CATEGORIES),
        key=lambda x: -x[1],
    )
    if not counts:
        return "0 établissement à vocation économique recensé dans le rayon d'analyse."
    total = sum(n for _, n in counts)
    breakdown = ", ".join(f"{cat} : {n}" for cat, n in counts)
    return f"{total} établissement(s) à vocation économique recensé(s) : {breakdown}."


def _territorial_context(loc: LocationResult, infrastructures: list[Infrastructure]) -> str:
    admin = ", ".join(p for p in (loc.city, loc.department, loc.region) if p) or "zone non identifiée administrativement"
    nearest = _nearest(infrastructures)
    if nearest:
        nearest_part = f"L'infrastructure la plus proche du point analysé est {nearest.name} ({nearest.category}), à {nearest.distance_m} m."
    else:
        nearest_part = "0 infrastructure localisée n'a été recensée dans le rayon d'analyse."
    return f"Localisation administrative : {admin}. {nearest_part}"


def _build_limits(loc: LocationResult, infrastructures: list[Infrastructure]) -> list[str]:
    limits = []
    if loc.coordinates is None:
        limits.append("Aucune coordonnée GPS : localisation basée sur le géocodage textuel, moins précise.")
    if len(infrastructures) < 3:
        limits.append(f"{len(infrastructures)} infrastructure(s) détectée(s) : couverture OSM potentiellement incomplète dans cette zone.")
    if len(infrastructures) >= OVERPASS_ELEMENT_CAP:
        limits.append(
            f"Plafond de réponse Overpass atteint ({OVERPASS_ELEMENT_CAP} éléments) : le rayon "
            "demandé est probablement plus dense que ce plafond ne peut représenter — le nombre "
            "réel d'infrastructures et de concurrents peut être supérieur à celui affiché."
        )
    limits.append("Données issues de sources publiques ouvertes uniquement (OSM, Nominatim/Géoplateforme).")
    limits.append(
        "La taxonomie commerce actuelle ne collecte pas de données sur l'occupation du sol ni les "
        "sensibilités environnementales (waterway, leisure=park, power ne sont pas interrogés)."
    )
    limits.append("Les éléments déduits ou probables sont à vérifier sur le terrain.")
    return limits


def _list_sources(loc: LocationResult) -> list[str]:
    sources = ["OpenStreetMap / Nominatim — https://nominatim.openstreetmap.org"]
    if loc.coordinates:
        sources.append("Overpass API — https://overpass-api.de")
    return sources
