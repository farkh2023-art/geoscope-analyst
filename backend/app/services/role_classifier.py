from app.models.schemas import Activity

# Catégories qui génèrent du flux (transport, écoles, bureaux) quelle que soit l'activité analysée.
_FLUX_CATEGORIES = {"transport", "education", "bureaux"}

# Catégories de service de proximité : ni concurrent, ni générateur de flux structurant.
_SERVICE_CATEGORIES = {"sante", "services_personne", "hebergement", "stationnement", "loisirs_culture"}

# Table de correspondance explicite activité → tags qui désignent un concurrent direct.
_CONCURRENT_TAGS: dict[Activity, list[tuple[str, set[str]]]] = {
    Activity.restaurant: [("amenity", {"restaurant", "fast_food"})],
    Activity.boulangerie: [("shop", {"bakery", "pastry"})],
    Activity.coiffure: [("shop", {"hairdresser"})],
    Activity.boutique: [("shop", {"clothes", "shoes", "jewelry", "bags"})],
    Activity.pharmacie: [("amenity", {"pharmacy"})],
    Activity.cabinet: [("office", {"lawyer", "accountant", "estate_agent", "insurance", "therapist", "consulting"})],
    Activity.autre: [],
}


def infer_role(tags: dict, category: str, activity: Activity | None) -> str:
    if category in _FLUX_CATEGORIES:
        return "flux"

    if activity is not None:
        for tag_key, values in _CONCURRENT_TAGS.get(activity, []):
            if tags.get(tag_key) in values:
                return "concurrent"

    if category in _SERVICE_CATEGORIES:
        return "service"

    return "autre"
