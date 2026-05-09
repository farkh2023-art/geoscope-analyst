# GeoScope Analyst — v0.2.0

Super agent géospatial — analyse territoriale publique avec **carte interactive Leaflet.js**.

Accepte des coordonnées GPS, URLs cartographiques ou noms de lieux, enrichit les données via Nominatim et Overpass (OSM), et produit un rapport territorial structuré avec carte interactive.

## Fonctionnalités

- Détection automatique du type d'entrée (GPS / URL / nom de lieu / image)
- Reverse geocoding via Nominatim
- Détection d'infrastructures via Overpass API (rayon configurable)
- Score de confiance 0–100 avec justification
- Rapport en 3 modes : Flash / Analyste / Dossier complet
- **Carte interactive Leaflet.js** avec marqueurs colorés par catégorie
- Export JSON et Markdown
- Mode hors-ligne (données mockées, aucune connexion requise)
- Aucune clé API requise

## Installation

### Prérequis
- Python 3.11+

### Windows

```bat
cd geoscope-analyst\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### Linux / macOS

```bash
cd geoscope-analyst/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Lancement

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Ouvrir : **http://localhost:8000**

## Configuration (`.env`)

| Variable | Défaut | Description |
|---|---|---|
| `OFFLINE_MODE` | `true` | `true` = données mock, `false` = vraies API |
| `NOMINATIM_BASE_URL` | nominatim.openstreetmap.org | Endpoint Nominatim |
| `OVERPASS_BASE_URL` | overpass-api.de | Endpoint Overpass |
| `DEFAULT_RADIUS_M` | `1500` | Rayon d'analyse par défaut |
| `REQUEST_TIMEOUT_SECONDS` | `20` | Timeout HTTP |
| `MAP_TILE_URL` | OpenStreetMap | URL des tuiles de carte (aucune clé requise) |

## Tests

```bash
cd backend
pytest -v
```

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| GET | `/` | Interface web |
| GET | `/api/health` | État du service |
| POST | `/api/analyze` | Analyse géospatiale |
| POST | `/api/map-data` | Données GeoJSON pour la carte |
| POST | `/api/export/markdown` | Export Markdown |

### Exemple d'appel

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"input": "48.8566, 2.3522", "radius_m": 1500, "mode": "analyst"}'
```

## Limites du MVP

- Analyse d'image stubée (Phase 3)
- En `OFFLINE_MODE=true`, tuiles de carte non disponibles (marqueurs visibles)
- Nominatim retourne l'objet OSM le plus proche, pas toujours l'adresse exacte

## Changelog

### v0.2.0
- Carte interactive Leaflet.js (OpenStreetMap, aucune clé API)
- Marqueur de localisation, cercle de rayon, markers d'infrastructure colorés
- Endpoint `/api/map-data` (GeoJSON-ready)
- Variable `MAP_TILE_URL` configurable
- Gestion hors-ligne gracieuse pour la carte

### v0.1.0
- MVP initial : FastAPI + Nominatim + Overpass + interface web
