# Architecture GeoScope Analyst — v0.4.0

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
geocoding/   Overpass
factory.py   (infrastructures)
(Géoplateforme
 par défaut,
 Nominatim ou
 mock au choix)
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
| `services/geocoding/factory.py` | Sélectionne le geocoder actif (`geoplateforme` par défaut, `nominatim`, ou `mock` en offline) |
| `services/geocoding/geoplateforme.py` | Géocodage direct/inverse via l'API Géoplateforme (IGN) |
| `services/geocoding/nominatim.py` | Géocodage via Nominatim/OSM (alternative) |
| `services/geocoding/mock.py` | Données mockées (mode `OFFLINE_MODE=true` uniquement) |
| `services/overpass_client.py` | Requêtes infrastructures OSM (taxonomie 12 catégories, + mock offline) |
| `services/infrastructure_classifier.py` | Classification par catégorie |
| `services/role_classifier.py` | Rôle par infrastructure (`concurrent` / `flux` / `service` / `autre`) selon l'activité choisie |
| `services/geo_utils.py` | Distance haversine |
| `services/http_resilience.py` | Rate limiting client + retry (429, timeouts) sur les appels API externes |
| `services/ttl_cache.py` | Cache en mémoire des réponses Overpass (TTL configurable) |
| `services/confidence_scoring.py` | Calcul du score de confiance (qualité de la collecte, pas du lieu — voir `docs/scoring.md`) |
| `services/report_generator.py` | Génération du rapport territorial — chaque phrase narrative dérive d'un comptage/distance réel (voir `audits/AUDIT.md`) |
| `services/markdown_exporter.py` | Export Markdown du rapport |

`scripts/audit_report.py` appelle cette même chaîne en forçant le mode en ligne
(`OFFLINE_MODE=false`, `GEOCODER=geoplateforme`) pour produire les rapports d'audit de
véracité dans `audits/`.

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
| `flash` | Résumé, identification, confiance, 5 infras max affichées (comptages calculés sur la liste complète, troncature déclarée dans `limites_analyse`) |
| `analyst` | + connectivité, activités économiques |
| `full` | + contexte territorial |

Les sections `occupation_du_sol_estimee` et `sensibilites_environnementales` du mode
`full` ont été **supprimées à l'Étape 4** (`audits/AUDIT.md`) : la taxonomie commerce
n'interroge plus `landuse=*` ni `waterway`/`leisure=park`/`power`, donc aucune donnée ne
permet de les dériver honnêtement. Le renoncement est documenté dans `limites_analyse`
plutôt que comblé par une estimation inventée.

## Catégories infrastructure & couleurs carte

Taxonomie commerce (12 catégories, `infrastructure_classifier.CATEGORIES`) — couleurs
définies dans `static/app.js` (`CAT_COLORS`) :

| Catégorie | Couleur |
|---|---|
| commerce_alimentaire | `#f59e42` orange |
| restauration | `#f46060` rouge |
| services_personne | `#a78bfa` violet |
| commerce_non_alimentaire | `#e879f9` magenta |
| sante | `#3ecf8e` vert |
| education | `#4f8ef7` bleu |
| transport | `#22d3ee` cyan |
| bureaux | `#94a3b8` gris |
| loisirs_culture | `#4ade80` vert clair |
| hebergement | `#eab308` jaune |
| stationnement | `#64748b` gris sombre |
| autre | `#94a3b8` gris |

Chaque infrastructure porte aussi un **rôle** (`role_classifier.py`), déterminé par
l'activité choisie par l'utilisateur — indépendant de la catégorie ci-dessus :

| Rôle | Couleur | Signification |
|---|---|---|
| concurrent | `#f46060` rouge | Même activité que celle analysée |
| flux | `#4f8ef7` bleu | Générateur de flux (transport, éducation, bureaux) |
| service | `#4ade80` vert | Service de proximité, pas concurrent direct |
| autre | `#64748b` gris | Ni concurrent, ni flux, ni service identifié |
