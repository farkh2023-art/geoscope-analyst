# Proposition de score d'implantation — document de travail

**Statut : proposition, non implémentée.** Ce document ne contient aucun code et ne doit
pas être interprété comme une spécification prête à coder. Il liste les variables
envisageables, leurs sources, ce qui est réellement disponible aujourd'hui, ce qui ne
l'est pas, et la règle de validation à respecter avant tout affichage à un utilisateur.

## Pourquoi ce document et pas un score directement

Le score de confiance actuel (`confidence_scoring.py`) mesure la **qualité de la
collecte** (a-t-on des coordonnées, un géocodage réussi, assez d'infrastructures) — pas
la **qualité du lieu pour un commerce donné**. Construire ce second score sans
méthodologie explicite reproduirait l'erreur corrigée à l'Étape 4 : des affirmations qui
sonnent juste sans dériver d'aucune donnée vérifiable. Un score d'implantation est plus
dangereux qu'une phrase de rapport, parce qu'un chiffre unique invite à la confiance
immédiate et masque la marge d'erreur — d'où la règle de validation en fin de document.

## Ce dont on dispose déjà dans le pipeline

| Donnée | Origine | Statut |
|---|---|---|
| Catégorie commerciale (12 catégories) | Overpass, taxonomie Étape 2 | Disponible |
| Rôle par infrastructure (`concurrent` / `flux` / `service` / `autre`) | `role_classifier.py`, dépend de l'activité choisie | Disponible |
| Distance exacte de chaque infrastructure | Haversine sur coordonnées OSM réelles | Disponible |
| Code INSEE de la commune (`citycode`) | Géoplateforme | Disponible (Étape 3) — clé nécessaire pour croiser une future source INSEE, non exploitée à ce jour |
| Code postal | Géoplateforme | Disponible |
| Score de qualité de collecte | `confidence_scoring.py` | Disponible, mais mesure la collecte, pas le lieu |

## Variables candidates pour un score d'implantation

Proposition organisée en quatre familles. Pour chaque variable : la donnée nécessaire,
si elle est obtenable aujourd'hui avec les sources déjà branchées (Overpass,
Géoplateforme), et une pondération **hypothèse de départ**, pas une valeur calibrée — voir
la section validation plus bas.

### 1. Concurrence directe

| Variable | Calcul proposé | Source | Disponible ? | Poids hypothèse |
|---|---|---|---|---|
| Nombre de concurrents dans le rayon | `count(role == "concurrent")` | Overpass + `role_classifier` | Oui | Fort (négatif) |
| Distance au concurrent le plus proche | `min(distance_m)` parmi les concurrents | Overpass | Oui | Fort (négatif si très proche) |
| Densité concurrentielle par rapport à la catégorie | Concurrents ÷ total d'établissements de la même catégorie | Overpass | Oui | Moyen |
| Enseignes nationales vs indépendants parmi les concurrents | Nécessite une base de reconnaissance de marque | — | **Non** (OSM ne qualifie pas systématiquement `brand=*`, couverture trop partielle pour être fiable) | — |

### 2. Générateurs de flux

| Variable | Calcul proposé | Source | Disponible ? | Poids hypothèse |
|---|---|---|---|---|
| Nombre d'infrastructures `flux` (transport, éducation, bureaux) dans le rayon | `count(role == "flux")` | Overpass | Oui | Positif |
| Distance à la station de transport la plus proche | `min(distance_m)` parmi `category == "transport"` | Overpass | Oui | Positif |
| Fréquentation réelle de ces flux (voyageurs/jour, effectifs) | Comptages voyageurs, effectifs scolaires/salariés | — | **Non** (aucune source ouverte fiable et à jour à l'échelle d'une adresse) | — |
| **Flux piétons réels devant l'adresse** | Comptages piétons horodatés | — | **Non — aucune donnée ouverte disponible en France à cette granularité** | — |

### 3. Environnement commercial

| Variable | Calcul proposé | Source | Disponible ? | Poids hypothèse |
|---|---|---|---|---|
| Établissements `service`/`autre` à proximité (effet de synergie / pôle commercial) | `count(role in ("service", "autre"))` | Overpass | Oui | Faible à moyen (positif) |
| Diversité des catégories présentes | Nombre de catégories distinctes non vides | Overpass | Oui | Faible |
| Taux de vacance commerciale (locaux vides) | Inventaire des locaux commerciaux vacants | — | **Non** (OSM ne recense pas les locaux vides ; nécessiterait une source type Data Rue Commerce, non ouverte partout) | — |

### 4. Contexte socio-économique

| Variable | Calcul proposé | Source | Disponible ? | Poids hypothèse |
|---|---|---|---|---|
| Population de la commune | Recensement INSEE | INSEE (via `citycode`, non intégré) | **Non — explicitement hors périmètre à ce stade** | — |
| Revenu médian / catégories socio-professionnelles du quartier | Filosofi INSEE (IRIS) | INSEE (non intégré) | **Non — explicitement hors périmètre à ce stade** | — |
| Taux de création/défaillance d'entreprises du secteur dans la zone | SIRENE / BODACC | SIRENE (non intégré) | **Non — explicitement hors périmètre à ce stade** | — |
| Loyer commercial au m² dans la rue | Bases notariales ou CCI, rarement ouvertes | — | **Non — aucune source ouverte fiable identifiée** | — |

## Variables qu'on ne peut pas obtenir avec les données ouvertes actuelles

À déclarer explicitement à l'utilisateur si un score est un jour affiché — jamais
remplacées par une estimation :

- **Flux piétons réels** (le cas cité en exemple par le mandat de ce document) — aucune
  source ouverte en France ne fournit de comptage piéton à l'échelle d'une adresse.
- Fréquentation réelle des générateurs de flux (voyageurs, effectifs scolaires/salariés).
- Taux de vacance commerciale locale et rotation des locaux.
- Loyers commerciaux au m².
- Chiffre d'affaires ou solidité financière des concurrents identifiés.
- Reconnaissance fiable des enseignes nationales vs indépendants (couverture `brand=*`
  trop partielle dans OSM pour être exploitable).
- Données démographiques et socio-économiques fines (nécessitent une intégration INSEE
  explicitement hors périmètre pour l'instant).
- Projets d'urbanisme ou travaux à venir susceptibles de modifier la fréquentation.

Un score construit sans ces variables n'est pas un score « faux » s'il est présenté pour
ce qu'il est : une estimation basée sur la densité et la structure commerciale
observables via OSM, pas une prédiction de rentabilité. Le nom du score et sa
présentation à l'utilisateur devront rendre cette limite impossible à manquer.

## Modèle d'agrégation proposé (esquisse, non calibrée)

Sur le même principe additif que `compute_confidence`, mais avec des termes qui peuvent
être positifs ou négatifs selon le signe attendu de la variable :

```
score = base
      + poids_flux      × f(distance_flux, nombre_flux)
      + poids_synergie  × f(établissements_service)
      - poids_concurrence × f(nombre_concurrents, distance_concurrent_proche)
      (bornage 0–100)
```

Chaque `f()` et chaque poids sont des hypothèses de départ à ajuster — pas une formule
figée. La forme exacte (linéaire, décroissance en fonction de la distance, seuils) doit
être décidée après confrontation aux adresses réelles de la phase de validation, pas
avant.

## Plan de validation (esquisse)

Avant tout affichage, constituer un jeu d'environ vingt adresses pour lesquelles le
résultat commercial réel est déjà connu (établissement toujours ouvert après N années,
fermeture précoce, changement d'enseigne, etc.), couvrant :

- Des activités différentes (au minimum celles déjà supportées : restaurant,
  boulangerie, coiffure, boutique, pharmacie, cabinet).
- Des profils de zone différents (dense urbain, périphérie, petite ville — sur le modèle
  des trois adresses de `audits/AUDIT.md`).
- Des issues connues variées : succès clairs, échecs clairs, cas ambigus.

Pour chaque adresse : calculer le score proposé, comparer au résultat réel, documenter
les écarts. Un score qui classerait un échec connu comme favorable (ou l'inverse) doit
faire revoir la pondération ou la variable en cause avant toute nouvelle tentative —
pas être ignoré comme un cas isolé.

## Règle non négociable

**Aucun score d'implantation n'est affiché à un utilisateur avant d'avoir été confronté
à une vingtaine d'adresses dont le résultat commercial réel est déjà connu.**

Cette règle s'applique à toute future implémentation de ce document, quelle que soit la
personne qui l'écrit.
