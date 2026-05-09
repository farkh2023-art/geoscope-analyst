from app.services.confidence_scoring import compute_confidence
from app.models.schemas import Coordinates, Infrastructure, InputType, LocationResult


def _loc(coords=True, country="France", region="IDF", city="Paris"):
    return LocationResult(
        coordinates=Coordinates(lat=48.85, lon=2.35) if coords else None,
        country=country,
        region=region,
        city=city,
        display_name=f"{city}, {country}",
        input_type=InputType.gps if coords else InputType.place_name,
    )


def _infras(n: int) -> list[Infrastructure]:
    return [
        Infrastructure(name=f"Infra {i}", type="road", category="transport")
        for i in range(n)
    ]


def test_full_data_high_confidence():
    result = compute_confidence(_loc(), _infras(7))
    assert result.score >= 70
    assert result.label == "élevé"


def test_no_coords_lower_score():
    result_with = compute_confidence(_loc(coords=True), _infras(5))
    result_without = compute_confidence(_loc(coords=False), _infras(5))
    assert result_with.score > result_without.score


def test_no_infra_lower_score():
    result_with = compute_confidence(_loc(), _infras(5))
    result_without = compute_confidence(_loc(), _infras(0))
    assert result_with.score > result_without.score


def test_score_capped_at_100():
    result = compute_confidence(_loc(), _infras(20))
    assert result.score <= 100


def test_score_not_negative():
    result = compute_confidence(
        LocationResult(input_type=InputType.free_text),
        [],
    )
    assert result.score >= 0


def test_label_values():
    result = compute_confidence(_loc(), _infras(7))
    assert result.label in ("faible", "moyen", "élevé")


def test_justification_not_empty():
    result = compute_confidence(_loc(), _infras(3))
    assert len(result.justification) > 0
