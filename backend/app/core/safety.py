"""Guardrails: only public data, no secrets, no personal identification."""

BLOCKED_KEYWORDS = [
    "données personnelles",
    "tracking",
    "surveillance individuelle",
    "identification de personne",
]


def check_input_safety(text: str) -> list[str]:
    """Return list of warning messages if input raises safety concerns."""
    warnings: list[str] = []
    lower = text.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in lower:
            warnings.append(f"Entrée potentiellement sensible détectée : « {kw} »")
    return warnings


def redact_secrets(data: dict) -> dict:
    """Remove any key that looks like a secret before logging or returning."""
    sensitive_keys = {"api_key", "secret", "token", "password", "key"}
    return {k: "***" if k.lower() in sensitive_keys else v for k, v in data.items()}
