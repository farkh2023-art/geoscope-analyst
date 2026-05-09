# Roadmap GeoScope Analyst

## Phase 1 — MVP (v0.1.0) ✅

- [x] Détection du type d'entrée (GPS, URL, nom, image)
- [x] Parsing de coordonnées multi-format
- [x] Reverse geocoding via Nominatim (+ mock offline)
- [x] Requêtes d'infrastructures via Overpass API (+ mock offline)
- [x] Classification des infrastructures par catégorie
- [x] Score de confiance (0–100)
- [x] Rapport structuré (flash / analyst / full)
- [x] Export JSON et Markdown
- [x] Interface web responsive (thème sombre)
- [x] Tests pytest (33 tests)

## Phase 2 — Carte interactive (v0.2.0) ✅

- [x] Intégration Leaflet.js (tuiles OpenStreetMap — aucune clé API)
- [x] Marqueur principal de localisation avec popup
- [x] Cercle de rayon d'analyse (pointillés bleus)
- [x] Marqueurs d'infrastructure colorés par catégorie
- [x] Légende dynamique des catégories présentes
- [x] Gestion gracieuse du mode hors-ligne (message tuiles indisponibles)
- [x] Endpoint `/api/map-data` (GeoJSON-ready)
- [x] Variable `MAP_TILE_URL` configurable en `.env`
- [x] Mise à jour de la version à 0.2.0
- [x] Badge version dans l'interface
- [x] `.env` confirmé dans `.gitignore`
- [x] Aucune clé secrète dans le code

## Phase 3A — Interactivité carte (v0.3.0) ✅

- [x] Filtres de catégorie interactifs sur la carte (toggle par couche Leaflet)
- [x] Compteurs par catégorie dans la légende
- [x] Boutons "Tout afficher / Tout masquer"
- [x] **Analyse par clic sur carte** — `map.on('click')` → input auto-rempli → analyse automatique → marqueur "Point sélectionné"
- [x] Historique local des 5 dernières analyses (localStorage, restaurable en 1 clic)
- [x] Filtre rapide sur la table des infrastructures
- [x] Export GeoJSON (FeatureCollection complète)
- [x] Correction : `mapOfflineNote` masquée au début de chaque nouvelle analyse

## Phase 3B — Enrichissement (v0.4.0)

- [ ] Vraies coordonnées OSM pour les marqueurs (utiliser `/api/map-data` + Overpass `lat/lon` réels)
- [ ] Clustering Leaflet (`L.MarkerClusterGroup`) pour les zones denses
- [ ] Analyse d'image / OCR (intégration Claude API vision multimodale)
- [ ] Support URL Google Maps complète (extraction coordonnées depuis `@lat,lon`)
- [ ] Lien de partage par URL (`?input=...&radius=...&mode=...`)
- [ ] Export PDF (WeasyPrint ou ReportLab)
- [ ] Cache Redis pour Nominatim/Overpass (rate limiting)

## Phase 4 — Production (v1.0.0)

- [ ] Authentification par API key
- [ ] Rate limiting (slowapi)
- [ ] Logs structurés (structlog)
- [ ] Déploiement Docker + docker-compose
- [ ] Intégration Google Earth Engine (occupation du sol réelle)
- [ ] Intégration Copernicus (données environnementales)
- [ ] Mode multi-langues (EN, AR, ES)
