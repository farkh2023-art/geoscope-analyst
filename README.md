# GeoScope Analyst — v0.4.0
[![Tests](https://github.com/farkh2023-art/geoscope-analyst/actions/workflows/tests.yml/badge.svg)](https://github.com/farkh2023-art/geoscope-analyst/actions/workflows/tests.yml)

Super agent géospatial — aide à l'implantation commerciale avec **carte interactive Leaflet.js**.

Accepte une adresse (coordonnées GPS, URL cartographique ou nom de lieu) et une activité, géocode via la **Géoplateforme (IGN)** par défaut, détecte les commerces et équipements environnants via Overpass (OSM), identifie les concurrents directs, et produit un rapport structuré avec carte interactive.

## Fonctionnalités

- Détection automatique du type d'entrée (GPS / URL / nom de lieu / image)
- Géocodage via la **Géoplateforme (IGN)** par défaut — Nominatim et un mode `mock` restent disponibles
- Taxonomie commerce (12 catégories) et identification des concurrents directs selon l'activité choisie
- Détection d'infrastructures via Overpass API en `nwr` (nœuds, chemins, relations — rayon configurable)
- Score de confiance 0–100 avec justification
- Rapport en 3 modes : Flash / Analyste / Dossier complet
- **Carte interactive Leaflet.js** avec marqueurs colorés par catégorie et par rôle
- Export JSON, Markdown et GeoJSON
- Cache mémoire TTL et limiteur de débit sur les appels géocodage/Overpass
- Mode hors-ligne (données mockées) disponible via `OFFLINE_MODE=true` / `GEOCODER=mock`
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
| `OFFLINE_MODE` | `false` | `true` = infrastructures Overpass mockées, `false` = vraies API |
| `GEOCODER` | `geoplateforme` | `geoplateforme` \| `nominatim` \| `mock` — provider de géocodage |
| `GEOPF_BASE_URL` | data.geopf.fr/geocodage | Endpoint Géoplateforme (IGN) |
| `NOMINATIM_BASE_URL` | nominatim.openstreetmap.org | Endpoint Nominatim (si `GEOCODER=nominatim`) |
| `OVERPASS_BASE_URL` | overpass-api.de | Endpoint Overpass |
| `NOMINATIM_USER_AGENT` | — | User-Agent envoyé à Nominatim/Overpass ; **doit contenir un contact valide** en usage réel (les instances publiques interdisent l'usage commercial intensif sans contact identifiable) |
| `DEFAULT_RADIUS_M` | `1500` | Rayon d'analyse par défaut |
| `REQUEST_TIMEOUT_SECONDS` | `20` | Timeout HTTP |
| `RATE_LIMIT_PER_SECOND` | `40` | Plafond de requêtes/seconde vers le géocodeur et Overpass |
| `CACHE_TTL_SECONDS` | `86400` | Durée de vie du cache mémoire (géocodage + Overpass) |
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
  -d '{"input": "48.8566, 2.3522", "radius_m": 1500, "mode": "analyst", "activity": "restaurant"}'
```

## Limites du MVP

- Analyse d'image stubée (Phase 3)
- En `OFFLINE_MODE=true`, tuiles de carte non disponibles (marqueurs visibles)
- Le géocodeur Géoplateforme ne couvre que les adresses françaises (BAN/BD TOPO/Parcellaire Express)
- Sans `activity` renseignée, aucun concurrent n'est identifié (rôle toujours `service`/`autre`/`flux`)

## Changelog

### v0.4.0
- Provider de géocodage **Géoplateforme (IGN)** par défaut, remplaçant Nominatim comme choix par défaut (`GEOCODER=geoplateforme`)
- Abstraction `Geocoder` (`geoplateforme` / `nominatim` / `mock`) dans `app/services/geocoding/`
- `OFFLINE_MODE` passe à `false` par défaut : l'application interroge les vraies API par défaut
- Limiteur de débit configurable et retry sur HTTP 429 (respecte `Retry-After`) pour le géocodage et Overpass
- Cache mémoire TTL (24 h par défaut) sur le géocodage et Overpass
- `LocationResult` gagne `postcode` et `citycode` (code INSEE)
- Avertissement au démarrage si `GEOCODER=nominatim` sans contact configuré dans `NOMINATIM_USER_AGENT`
- Source de vérité unique pour la version (`app/version.py`)

### v0.3.0
- Taxonomie commerce (12 catégories) remplaçant la taxonomie territoriale
- Requêtes Overpass en `nwr` (nœuds, chemins, relations) — couvre les commerces cartographiés en polygone
- Rôle par infrastructure (`concurrent` / `flux` / `service` / `autre`) selon l'activité analysée
- Coordonnées OSM réelles et distances calculées pour chaque infrastructure (suppression des positions générées par hash)

### v0.2.0
- Carte interactive Leaflet.js (OpenStreetMap, aucune clé API)
- Marqueur de localisation, cercle de rayon, markers d'infrastructure colorés
- Endpoint `/api/map-data` (GeoJSON-ready)
- Variable `MAP_TILE_URL` configurable
- Gestion hors-ligne gracieuse pour la carte

### v0.1.0
- MVP initial : FastAPI + Nominatim + Overpass + interface web
