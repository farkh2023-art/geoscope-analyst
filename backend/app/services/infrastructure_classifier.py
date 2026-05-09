from app.models.schemas import Infrastructure

CATEGORIES = [
    "transport",
    "santé",
    "éducation",
    "énergie",
    "eau",
    "industrie",
    "administratif",
    "environnement",
    "autre",
]


def classify_by_category(infrastructures: list[Infrastructure]) -> dict[str, list[Infrastructure]]:
    grouped: dict[str, list[Infrastructure]] = {cat: [] for cat in CATEGORIES}
    for infra in infrastructures:
        cat = infra.category if infra.category in grouped else "autre"
        grouped[cat].append(infra)
    return grouped


def summarize_categories(infrastructures: list[Infrastructure]) -> list[str]:
    """Return list of present categories (non-empty)."""
    grouped = classify_by_category(infrastructures)
    return [cat for cat, items in grouped.items() if items]
