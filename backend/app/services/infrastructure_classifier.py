from app.models.schemas import Infrastructure

CATEGORIES = [
    "commerce_alimentaire",
    "restauration",
    "services_personne",
    "commerce_non_alimentaire",
    "sante",
    "education",
    "transport",
    "bureaux",
    "loisirs_culture",
    "hebergement",
    "stationnement",
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
