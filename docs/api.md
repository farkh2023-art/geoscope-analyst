# API Reference — GeoScope Analyst

Base URL : `http://localhost:8000`

---

## GET /api/health

Retourne l'état du service.

**Réponse**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "offline_mode": true,
  "env": "development"
}
```

---

## POST /api/analyze

Lance une analyse géospatiale.

**Corps de la requête**
```json
{
  "input": "48.8566, 2.3522",
  "radius_m": 1500,
  "mode": "analyst"
}
```

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `input` | string | requis | GPS / URL / nom de lieu |
| `radius_m` | int | 1500 | Rayon en mètres (100–50000) |
| `mode` | enum | `analyst` | `flash` / `analyst` / `full` |

**Réponse**
```json
{
  "location": {
    "coordinates": {"lat": 48.8566, "lon": 2.3522},
    "country": "France",
    "region": "Île-de-France",
    "department": "Paris",
    "city": "Paris",
    "neighborhood": "1er Arrondissement",
    "display_name": "Paris, Île-de-France, France",
    "input_type": "gps"
  },
  "confidence": {
    "score": 90,
    "label": "élevé",
    "justification": "coordonnées GPS présentes (+40) | ..."
  },
  "infrastructures": [
    {
      "name": "Gare du Nord",
      "type": "railway_station",
      "category": "transport",
      "osm_tags": {"railway": "station"},
      "source": "OpenStreetMap"
    }
  ],
  "report": { ... },
  "sources": ["OpenStreetMap / Nominatim — https://nominatim.openstreetmap.org"],
  "warnings": []
}
```

---

## POST /api/export/markdown

Convertit une réponse d'analyse en Markdown.

**Corps** : identique à la réponse de `/api/analyze`

**Réponse** : texte Markdown (`text/markdown`)
