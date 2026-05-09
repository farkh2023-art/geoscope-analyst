# Backend — GeoScope Analyst

## Lancement rapide

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

## Fonctionnalités principales

- **Analyse par coordonnées GPS** — saisir `48.8566, 2.3522` ou coller une URL Google Maps
- **Analyse par clic sur carte** — cliquer n'importe où sur la carte Leaflet après une première analyse ; les coordonnées du point cliqué remplissent automatiquement le champ et l'analyse se lance sans action supplémentaire. Un marqueur orange "Point sélectionné" confirme le point avant le résultat.
- **Filtres de catégorie** — cliquer sur un item de la légende affiche/masque la couche correspondante
- **Historique local** — les 5 dernières analyses sont sauvegardées dans `localStorage` et restaurables en un clic
- **Export** — JSON, Markdown, GeoJSON

## Tests

```bash
pytest -v
```

## Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app + routes
│   ├── core/
│   │   ├── config.py        # Settings (.env)
│   │   └── safety.py        # Garde-fous
│   ├── models/
│   │   └── schemas.py       # Modèles Pydantic
│   ├── services/
│   │   ├── input_detector.py
│   │   ├── coordinate_parser.py
│   │   ├── nominatim_client.py
│   │   ├── overpass_client.py
│   │   ├── infrastructure_classifier.py
│   │   ├── confidence_scoring.py
│   │   ├── report_generator.py
│   │   └── markdown_exporter.py
│   └── static/              # Interface web
├── tests/
├── requirements.txt
└── .env.example
```
