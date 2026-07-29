"""
Audit de véracité (Étape 4) — garde-fou structurel.

Règle : toute phrase narrative du rapport doit porter au moins un chiffre issu des
données (comptage, distance, score), jamais une affirmation qualitative qui serait
identique quelle que soit l'adresse analysée. Ce test échoue si une formulation de la
liste noire (identifiée lors de l'audit comme indépendante des données) réapparaît, ou
si une section narrative ne contient aucun chiffre.
"""
from app.models.schemas import (
    AnalysisMode,
    Coordinates,
    ConfidenceResult,
    Infrastructure,
    InputType,
    LocationResult,
)
from app.services.report_generator import generate_report

# Formulations identifiées lors de l'audit comme vraies pour n'importe quelle adresse
# (donc jamais dérivées des données) — leur réapparition est un régression de véracité.
_BLACKLIST = [
    "modérée à forte",
    "centralité locale",
    "usage mixte",
    "Usage mixte",
    "non déterminées avec les données disponibles",
    "Bonne connectivité",
    "Connectivité faible ou non détectée",
    "Concentration de commerces, bureaux et transports",
    "Présence de services de santé et/ou d'éducation",
    "Aucune sensibilité environnementale majeure identifiée",
    "Zone à dominante",
    "se présente comme une zone",
]

# Sections narratives censées porter un jugement sur LE LIEU analysé : chacune doit
# contenir un chiffre (comptage, distance, score) issu des données de la requête.
_NUMERIC_SECTIONS = [
    "resume_executif",
    "description_zone",
    "connectivite",
    "activites_economiques_probables",
    "contexte_territorial",
]


def _loc():
    return LocationResult(
        coordinates=Coordinates(lat=44.8378, lon=-0.5792),
        country="France",
        region="Nouvelle-Aquitaine",
        department="Gironde",
        city="Bordeaux",
        display_name="Bordeaux, Gironde, France",
        input_type=InputType.gps,
    )


def _realistic_infras():
    return [
        Infrastructure(name="Boulangerie Sainte-Catherine", type="bakery", category="commerce_alimentaire", distance_m=80, role="concurrent"),
        Infrastructure(name="Tram Sainte-Catherine", type="tram_stop", category="transport", distance_m=120, role="flux"),
        Infrastructure(name="Pharmacie Centrale", type="pharmacy", category="sante", distance_m=200, role="service"),
        Infrastructure(name="Cabinet Notarial", type="lawyer", category="bureaux", distance_m=250, role="flux"),
        Infrastructure(name="Restaurant Le Chapon", type="restaurant", category="restauration", distance_m=310, role="autre"),
    ]


def _collect_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out = []
        for v in value.values():
            out.extend(_collect_strings(v))
        return out
    if isinstance(value, list):
        out = []
        for v in value:
            out.extend(_collect_strings(v))
        return out
    return []


def _generate(mode: AnalysisMode, infras: list[Infrastructure]) -> dict:
    conf = ConfidenceResult(score=78, label="élevé", justification="test")
    return generate_report(_loc(), conf, infras, mode, 1500)


def test_no_blacklisted_phrases_full_mode():
    report = _generate(AnalysisMode.full, _realistic_infras())
    all_text = " | ".join(_collect_strings(report))
    for phrase in _BLACKLIST:
        assert phrase not in all_text, f"Formulation indépendante des données détectée : {phrase!r}"


def test_no_blacklisted_phrases_empty_infrastructures():
    """Le cas dégénéré (aucune infrastructure) est le plus à risque de retomber sur un cliché."""
    report = _generate(AnalysisMode.full, [])
    all_text = " | ".join(_collect_strings(report))
    for phrase in _BLACKLIST:
        assert phrase not in all_text, f"Formulation indépendante des données détectée (cas vide) : {phrase!r}"


def test_narrative_sections_contain_a_digit():
    report = _generate(AnalysisMode.full, _realistic_infras())
    for key in _NUMERIC_SECTIONS:
        assert key in report, f"Section attendue absente : {key}"
        text = report[key]
        assert any(c.isdigit() for c in text), f"Section {key!r} ne contient aucun chiffre : {text!r}"


def test_narrative_sections_contain_a_digit_even_when_empty():
    report = _generate(AnalysisMode.full, [])
    for key in _NUMERIC_SECTIONS:
        text = report[key]
        assert any(c.isdigit() for c in text), f"Section {key!r} (cas vide) ne contient aucun chiffre : {text!r}"
