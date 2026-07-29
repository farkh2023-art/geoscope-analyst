from app.services.report_generator import generate_report
from app.models.schemas import (
    AnalysisMode,
    ConfidenceResult,
    Coordinates,
    Infrastructure,
    InputType,
    LocationResult,
)


def _loc():
    return LocationResult(
        coordinates=Coordinates(lat=48.8566, lon=2.3522),
        country="France",
        region="Île-de-France",
        department="Paris",
        city="Paris",
        display_name="Paris, France",
        input_type=InputType.gps,
    )


def _conf():
    return ConfidenceResult(score=85, label="élevé", justification="test")


def _infras():
    return [
        Infrastructure(name="Gare du Nord", type="station", category="transport", distance_m=200, role="flux"),
        Infrastructure(name="Hôpital X", type="hospital", category="sante", distance_m=450, role="service"),
    ]


def test_flash_report_has_required_keys():
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.flash, 1500)
    assert "resume_executif" in r
    assert "identification_administrative" in r
    assert "niveau_confiance" in r
    assert "limites_analyse" in r


def test_analyst_report_has_extra_keys():
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.analyst, 1500)
    assert "connectivite" in r
    assert "activites_economiques_probables" in r


def test_full_report_has_contexte_territorial():
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.full, 1500)
    assert "contexte_territorial" in r


def test_fabricated_sections_removed():
    """
    occupation_du_sol_estimee et sensibilites_environnementales produisaient des phrases
    figées indépendantes des données (audit de véracité, Étape 4) — supprimées car la
    taxonomie commerce ne collecte plus les tags nécessaires (landuse, waterway, power).
    """
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.full, 1500)
    assert "occupation_du_sol_estimee" not in r
    assert "sensibilites_environnementales" not in r


def test_administrative_fields():
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.analyst, 1500)
    admin = r["identification_administrative"]
    assert admin["pays"] == "France"
    assert admin["ville"] == "Paris"


def test_limits_is_list():
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.flash, 1500)
    assert isinstance(r["limites_analyse"], list)
    assert len(r["limites_analyse"]) > 0


def test_summary_cites_real_counts_and_nearest():
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.analyst, 1500)
    summary = r["resume_executif"]
    assert "2 établissement(s)" in summary
    assert "Gare du Nord" in summary
    assert "200 m" in summary


def test_summary_counts_concurrents():
    infras = [
        Infrastructure(name="Boulangerie A", type="bakery", category="commerce_alimentaire", distance_m=100, role="concurrent"),
        Infrastructure(name="Pharmacie B", type="pharmacy", category="sante", distance_m=300, role="service"),
    ]
    r = generate_report(_loc(), _conf(), infras, AnalysisMode.analyst, 1500)
    assert "1 concurrent(s)" in r["resume_executif"]


def test_flash_mode_truncates_display_but_not_counts():
    infras = [
        Infrastructure(name=f"Infra {i}", type="shop", category="commerce_non_alimentaire", distance_m=i * 10, role="autre")
        for i in range(8)
    ]
    r = generate_report(_loc(), _conf(), infras, AnalysisMode.flash, 1500)
    # Le résumé et la répartition portent sur les 8 infrastructures réelles...
    assert "8 établissement(s)" in r["resume_executif"]
    assert "8 infrastructure(s) recensée(s)" in r["description_zone"]
    # ...mais l'affichage détaillé est limité à 5, avec mention explicite.
    displayed = sum(len(v) for v in r["infrastructures"].values())
    assert displayed == 5
    assert any("5 infrastructures affichées" in lim and "8 recensées" in lim for lim in r["limites_analyse"])
