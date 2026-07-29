from app.services.infrastructure_classifier import classify_by_category, summarize_categories
from app.models.schemas import Infrastructure


def _make(cat: str) -> Infrastructure:
    return Infrastructure(name="test", type="test", category=cat)


def test_classify_groups_correctly():
    infras = [_make("transport"), _make("transport"), _make("sante"), _make("bureaux")]
    grouped = classify_by_category(infras)
    assert len(grouped["transport"]) == 2
    assert len(grouped["sante"]) == 1
    assert len(grouped["bureaux"]) == 1
    assert len(grouped["education"]) == 0


def test_unknown_category_goes_to_autre():
    infras = [_make("catégorie_inexistante")]
    grouped = classify_by_category(infras)
    assert len(grouped["autre"]) == 1


def test_summarize_returns_only_present():
    infras = [_make("transport"), _make("bureaux")]
    present = summarize_categories(infras)
    assert "transport" in present
    assert "bureaux" in present
    assert "sante" not in present


def test_empty_input():
    grouped = classify_by_category([])
    assert all(len(v) == 0 for v in grouped.values())
    assert summarize_categories([]) == []
