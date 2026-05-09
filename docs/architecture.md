# Architecture GeoScope Analyst — v0.3.0

## Vue d'ensemble

```
Entrée utilisateur
       │
       ▼
┌─────────────────┐
│  input_detector │  Détecte le type : GPS / URL / nom de lieu / image
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│coordinate_parser│  Extrait lat/lon depuis l'entrée
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
Nominatim  Overpass
(geocoding) (infrastructures)
    │         │
    └────┬────┘
         │
         ▼
┌─────────────────────┐
│ infrastructure_     │  Classe en catégories
│ classifier          │
└────────┬────────────┘
         │
         ▼
┌─────────────────┐
│confidence_scoring│  Score 0-100
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│report_generator │  Rapport structuré (flash/analyst/full)
└────────┬────────┘
         │
    ┌────┴────────────┐
    │                 │
    ▼                 ▼
 JSON API        markdown_exporter
    │
    ▼
Frontend Leaflet.js
    ├── Marqueur localisation
    ├── Cercle rayon d'analyse
    ├── Markers infrastructures (colorés par catégorie)
    └── Légende dynamique
```

## Composants Backend (`backend/app/`)

| Fichier | Rôle |
|---|---|
| `main.py` | FastAPI — 5 routes |
| `core/config.py` | Settings via .env (pydantic-settings) |
| `core/safety.py` | Garde-fous : données publiques uniquement |
| `models/schemas.py` | Modèles Pydantic (requêtes / réponses / carte) |
| `services/input_detector.py` | Détection du type d'entrée |
| `services/coordinate_parser.py` | Parsing de coordonnées multi-format |
| `services/nominatim_client.py` | Reverse geocoding (+ mock offline) |
| `services/overpass_client.py` | Requêtes infrastructures OSM (+ mock offline) |
| `services/infrastructure_classifier.py` | Classification par catégorie |
| `services/confidence_scoring.py` | Calcul du score de confiance |
| `services/report_generator.py` | Génération du rapport territorial |
| `services/markdown_exporter.py` | Export Markdown du rapport |

## Composants Frontend (`backend/app/static/`)

| Fichier | Rôle |
|---|---|
| `index.html` | SPA — structure HTML, Leaflet CDN |
| `styles.css` | Thème sombre, responsive, styles Leaflet |
| `app.js` | Logique UI, carte Leaflet, appels API |

### Carte interactive (Phase 2 → 3A)

- **Bibliothèque** : Leaflet.js 1.9.4 (CDN, libre, aucune clé API)
- **Tuiles** : OpenStreetMap (configurable via `MAP_TILE_URL`)
- **Marqueur localisation** : div icon bleu avec halo
- **Cercle d'analyse** : `L.circle` en pointillés, rayon configurable
- **Markers infra** : `L.circleMarker`, couleur par catégorie, organisés en `L.layerGroup` par catégorie
- **Offline** : les markers et le cercle s'affichent sans tuiles

#### Analyse par clic sur carte (Phase 3A)

`leafletMap.on('click', onMapClick)` est enregistré à chaque création de carte.  
Flux : clic utilisateur → `onMapClick(e)` → marqueur orange "Point sélectionné" ajouté → champ `#inputField` rempli avec `lat, lon` → `runAnalysis()` appelé automatiquement.  
Le `clickMarker` est nettoyé à chaque nouveau `renderMap()` (var globale remise à `null` lors du `leafletMap.remove()`).

#### Filtres de catégorie (Phase 3A)

Chaque appel à `renderMap` crée un `L.layerGroup` par catégorie (`categoryLayers`).  
`toggleCategory(cat)` ajoute ou retire la couche de la carte et met à jour la légende (classe `.legend-inactive`).

#### Historique local (Phase 3A)

`saveToHistory(data, input, radius_m)` persiste les 5 dernières analyses dans `localStorage['geoscope_history']`.  
`restoreAnalysis(index)` recharge l'entrée et rappelle `renderResults`.

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| GET | `/` | Interface web |
| GET | `/api/health` | État + version + config carte |
| POST | `/api/analyze` | Analyse géospatiale complète |
| POST | `/api/map-data` | Données GeoJSON pour la carte |
| POST | `/api/export/markdown` | Export Markdown |

## Modes de sortie

| Mode | Sections incluses |
|---|---|
| `flash` | Résumé, identification, confiance, 5 infras max |
| `analyst` | + connectivité, activités économiques |
| `full` | + occupation du sol, environnement, contexte territorial |

## Catégories infrastructure & couleurs carte

| Catégorie | Couleur |
|---|---|
| transport | `#4f8ef7` bleu |
| santé | `#f46060` rouge |
| éducation | `#3ecf8e` vert |
| énergie | `#f59e42` orange |
| eau | `#22d3ee` cyan |
| industrie | `#94a3b8` gris |
| administratif | `#a78bfa` violet |
| environnement | `#4ade80` vert clair |
| autre | `#64748b` gris sombre |
