from app.models.schemas import ConfidenceResult, LocationResult, InputType
from app.models.schemas import Infrastructure


def compute_confidence(
    location: LocationResult,
    infrastructures: list[Infrastructure],
) -> ConfidenceResult:
    score = 0
    reasons: list[str] = []

    if location.coordinates is not None:
        score += 40
        reasons.append("coordonnées GPS présentes (+40)")

    if location.display_name and location.country:
        score += 25
        reasons.append("géocodage réussi (+25)")
    elif location.display_name:
        score += 10
        reasons.append("géocodage partiel (+10)")

    if len(infrastructures) >= 5:
        score += 15
        reasons.append(f"{len(infrastructures)} infrastructures trouvées (+15)")
    elif infrastructures:
        score += 8
        reasons.append(f"{len(infrastructures)} infrastructure(s) trouvée(s) (+8)")

    if location.country and location.region and location.city:
        score += 10
        reasons.append("cohérence administrative complète (+10)")
    elif location.country:
        score += 5
        reasons.append("cohérence administrative partielle (+5)")

    if location.input_type == InputType.free_text:
        score = max(0, score - 10)
        reasons.append("entrée texte libre (−10)")

    score = min(100, score)

    if score >= 70:
        label = "élevé"
    elif score >= 40:
        label = "moyen"
    else:
        label = "faible"

    return ConfidenceResult(
        score=score,
        label=label,
        justification=" | ".join(reasons) if reasons else "Aucune donnée suffisante",
    )
