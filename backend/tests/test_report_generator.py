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
        Infrastructure(name="Gare du Nord", type="station", category="transport"),
        Infrastructure(name="Hôpital X", type="hospital", category="sante"),
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


def test_full_report_has_all_sections():
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.full, 1500)
    assert "occupation_du_sol_estimee" in r
    assert "sensibilites_environnementales" in r
    assert "contexte_territorial" in r


def test_administrative_fields():
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.analyst, 1500)
    admin = r["identification_administrative"]
    assert admin["pays"] == "France"
    assert admin["ville"] == "Paris"


def test_limits_is_list():
    r = generate_report(_loc(), _conf(), _infras(), AnalysisMode.flash, 1500)
    assert isinstance(r["limites_analyse"], list)
    assert len(r["limites_analyse"]) > 0
