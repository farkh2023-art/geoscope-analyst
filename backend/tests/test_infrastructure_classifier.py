from app.services.infrastructure_classifier import classify_by_category, summarize_categories
from app.models.schemas import Infrastructure


def _make(cat: str) -> Infrastructure:
    return Infrastructure(name="test", type="test", category=cat)


def test_classify_groups_correctly():
    infras = [_make("transport"), _make("transport"), _make("santé"), _make("eau")]
    grouped = classify_by_category(infras)
    assert len(grouped["transport"]) == 2
    assert len(grouped["santé"]) == 1
    assert len(grouped["eau"]) == 1
    assert len(grouped["éducation"]) == 0


def test_unknown_category_goes_to_autre():
    infras = [_make("catégorie_inexistante")]
    grouped = classify_by_category(infras)
    assert len(grouped["autre"]) == 1


def test_summarize_returns_only_present():
    infras = [_make("transport"), _make("énergie")]
    present = summarize_categories(infras)
    assert "transport" in present
    assert "énergie" in present
    assert "santé" not in present


def test_empty_input():
    grouped = classify_by_category([])
    assert all(len(v) == 0 for v in grouped.values())
    assert summarize_categories([]) == []
