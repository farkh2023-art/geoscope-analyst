from app.models.schemas import AnalyzeResponse


def export_to_markdown(data: AnalyzeResponse) -> str:
    r = data.report
    loc = data.location
    conf = data.confidence
    lines: list[str] = []

    lines.append("# Rapport GeoScope Analyst\n")

    lines.append("## 1. Résumé exécutif")
    lines.append(r.get("resume_executif", "") + "\n")

    admin = r.get("identification_administrative", {})
    lines.append("## 2. Identification administrative")
    for k, v in admin.items():
        lines.append(f"- **{k.replace('_', ' ').capitalize()}** : {v}")
    lines.append("")

    coords_info = r.get("coordonnees_et_rayon", {})
    lines.append("## 3. Coordonnées et rayon d'analyse")
    lines.append(f"- Coordonnées : {coords_info.get('coordonnees', 'N/A')}")
    lines.append(f"- Rayon d'analyse : {coords_info.get('rayon_analyse_m', 'N/A')} m\n")

    lines.append("## 4. Description de la zone")
    lines.append(r.get("description_zone", "") + "\n")

    infra_dict = r.get("infrastructures", {})
    if infra_dict:
        lines.append("## 5. Infrastructures détectées")
        for cat, items in infra_dict.items():
            lines.append(f"### {cat.capitalize()}")
            for item in items:
                lines.append(f"- {item}")
        lines.append("")

    if "connectivite" in r:
        lines.append("## 6. Connectivité")
        lines.append(r["connectivite"] + "\n")

    if "activites_economiques_probables" in r:
        lines.append("## 7. Activités économiques probables")
        lines.append(r["activites_economiques_probables"] + "\n")

    if "contexte_territorial" in r:
        lines.append("## 8. Contexte territorial")
        lines.append(r["contexte_territorial"] + "\n")

    lines.append("## 9. Niveau de confiance")
    lines.append(f"- Score : **{conf.score}/100** ({conf.label})")
    lines.append(f"- Justification : {conf.justification}\n")

    limits = r.get("limites_analyse", [])
    if limits:
        lines.append("## 10. Limites de l'analyse")
        for lim in limits:
            lines.append(f"- {lim}")
        lines.append("")

    sources = r.get("sources", data.sources)
    if sources:
        lines.append("## 11. Sources publiques")
        for src in sources:
            lines.append(f"- {src}")
        lines.append("")

    if data.warnings:
        lines.append("## ⚠ Avertissements")
        for w in data.warnings:
            lines.append(f"- {w}")

    return "\n".join(lines)
