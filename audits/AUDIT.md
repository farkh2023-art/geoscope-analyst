# Audit de véracité du rapport — Étape 4

Objectif : vérifier, sur des adresses réelles et en mode en ligne, que chaque phrase du
rapport dérive d'une donnée vérifiable — et supprimer ou reconstruire celles qui ne
passaient pas ce test : **« cette phrase serait-elle exactement identique pour une
adresse à Bordeaux ? »**

## Méthodologie

- `scripts/audit_report.py` force `OFFLINE_MODE=false` et `GEOCODER=geoplateforme`
  (ignore le `.env` local), et appelle la chaîne complète : Géoplateforme (géocodage) →
  Overpass (infrastructures) → `report_generator.generate_report`.
- Trois adresses réelles, vérifiables par quiconque sur openstreetmap.org, avec des
  profils délibérément différents et une activité différente à chaque fois.
- **Incident rencontré et résolu pendant l'audit** : les deux premières tentatives sur
  chaque adresse ont échoué (HTTP 406 renvoyé par Apache sur overpass-api.de). Diagnostic :
  la valeur `NOMINATIM_USER_AGENT=GeoScopeAnalyst/0.2.0 local-test` présente dans le
  `backend/.env` de développement a fini par être bloquée par les protections anti-abus
  du serveur public, probablement à cause du volume de requêtes de test envoyées durant
  les étapes précédentes avec cette même chaîne. Un User-Agent identifiable et distinct
  (`GeoScopeAnalyst/0.4.0 (audit-veracite; contact: yousseffarkh2014@gmail.com)`) a
  immédiatement résolu le blocage. Ceci confirme empiriquement l'avertissement déjà ajouté
  à l'Étape 3 sur la nécessité d'un contact valide dans le User-Agent — la valeur par
  défaut du `.env` de développement devrait être mise à jour séparément.

## Les trois adresses

| Adresse | Profil | Activité | Rayon | Résultat |
|---|---|---|---|---|
| [78 Rue Montorgueil, Paris](78-rue-montorgueil-paris.md) | Rue commerçante parisienne très dense | `boulangerie` | 500 m | 200 infrastructures (plafond `out center 200` atteint), 2 concurrents |
| [Avenue Jean Jaurès, Pantin](avenue-jean-jaurès-pantin.md) | Avenue de périphérie (Seine-Saint-Denis) | `coiffure` | 800 m | 200 infrastructures (plafond atteint), 9 concurrents |
| [Place du Chatel, Provins](place-du-chatel-provins.md) | Petite ville (Seine-et-Marne, ~80 km de Paris) | `restaurant` | 500 m | 58 infrastructures, 12 concurrents |

Les trois adresses sont vérifiables directement sur openstreetmap.org. Exemples de noms
cités dans les rapports et vérifiables : **Stohrer** (pâtisserie historique de 1730, 51
Rue Montorgueil), **Au Rocher de Cancale** (restaurant historique, Rue Montorgueil),
**La Terrasse Du Châtel** (restaurant, Place du Châtel, Provins).

Notez que Provins, bien que ressentie comme une « petite ville de province », est
administrativement en région Île-de-France (département de Seine-et-Marne) — la
différence entre les trois adresses n'apparaît donc pas dans le champ « région », mais
dans les données réelles : 58 infrastructures contre 200 (plafond) pour les deux autres,
et une composition différente (11 places de stationnement recensées à Provins contre 3 à
Montorgueil, absence de banques dans le rayon à Provins, etc.). C'est précisément le
point de l'audit : la différenciation vient des comptages et entités réelles, jamais
d'une étiquette qualitative.

## Test de Bordeaux : phrases supprimées ou reconstruites

Chaque ligne ci-dessous a été identifiée comme **vraie pour n'importe quelle adresse**,
donc ne dérivant d'aucune donnée, et a été supprimée ou reconstruite.

| Fonction | Avant (supprimé) | Après | Donnée dérivée |
|---|---|---|---|
| `_territorial_context` | *« Les données publiques disponibles suggèrent une centralité locale modérée à forte. »* | *« L'infrastructure la plus proche du point analysé est {nom} ({catégorie}), à {distance} m. »* | Nom réel + catégorie + distance de l'infrastructure OSM la plus proche |
| `_estimate_land_use` (section entière `occupation_du_sol_estimee`) | 3 phrases figées selon `zone_type` (« Concentration de commerces… », « Usage mixte : résidentiel, tertiaire… ») | **Section supprimée** | La taxonomie commerce (Étape 2) n'interroge plus `landuse=*` : aucune donnée ne permet d'estimer l'occupation du sol. Une reconstruction aurait nécessité d'inventer une donnée non collectée — exclu par la règle du projet. Le renoncement est documenté dans `limites_analyse`. |
| `sensibilites_environnementales` (section entière) | *« Aucune sensibilité environnementale majeure identifiée. »* (toujours affiché, jamais dérivé de données puisque `waterway`/`leisure=park`/`power` ne sont plus interrogés) | **Section supprimée**, repliée dans `limites_analyse` | Idem : absence de collecte, pas absence de risque — la phrase originale prétendait conclure sur un risque à partir d'une donnée qu'on ne regarde plus |
| `_infer_zone_type` / `_describe_zone` | *« Zone à dominante {urbaine dense / naturelle / rurale / mixte}. »* | *« {N} infrastructure(s) recensée(s)… Répartition par catégorie : {cat} ({n}), … »* | Comptage réel par catégorie sur la liste complète d'infrastructures |
| `_describe_connectivity` | *« Bonne connectivité via réseau ferroviaire, axes routiers principaux. »* / *« Connectivité faible ou non détectée. »* | *« {N} infrastructure(s) de transport recensée(s) : {noms} ({distances}). »* | Comptage + noms + distances des infrastructures de catégorie `transport` |
| `_infer_economy` | *« Activité tertiaire et services aux entreprises, services d'enseignement… »* (clichés par présence/absence de catégorie) | *« {N} établissement(s) à vocation économique recensé(s) : {cat} : {n}, … »* | Comptage réel par catégorie économique (hors transport/stationnement) |
| `_build_summary` | *« Zone identifiée comme {zone_type}. »* | *« {N} établissement(s) recensé(s), dont {N} concurrent(s) direct(s) identifié(s). Établissement le plus proche : {nom} ({distance} m). »* | Comptages réels + rôle `concurrent` (déterminé par l'activité choisie) + entité nommée la plus proche |
| `confidence_scoring.compute_confidence` | *« reverse geocoding réussi (+25) »* — libellé faux pour une recherche par nom de lieu (geocodage direct, pas inverse) | *« géocodage réussi (+25) »* | Découvert pendant l'audit sur l'adresse de Montorgueil (entrée texte → geocodage direct, jamais reverse) |

## Test de la liste noire (automatisé)

`backend/tests/test_report_veracity.py` fait échouer la suite si l'une de ces
formulations réapparaît dans un rapport généré (mode `full`, y compris le cas dégénéré
« 0 infrastructure », le plus à risque de retomber sur un cliché) :

`"modérée à forte"`, `"centralité locale"`, `"usage mixte"`, `"non déterminées avec les
données disponibles"`, `"Bonne connectivité"`, `"Connectivité faible ou non détectée"`,
`"Concentration de commerces, bureaux et transports"`, `"Présence de services de santé
et/ou d'éducation"`, `"Aucune sensibilité environnementale majeure identifiée"`, `"Zone
à dominante"`, `"se présente comme une zone"`.

Le même test vérifie que `resume_executif`, `description_zone`, `connectivite`,
`activites_economiques_probables` et `contexte_territorial` contiennent chacun au moins
un chiffre, y compris dans le cas dégénéré à 0 infrastructure.

## Sections conservées telles quelles — donnée dont elles dérivent

| Section | Donnée source |
|---|---|
| `identification_administrative` | Champs directs de la réponse Géoplateforme (`city`, `department`/`region` dérivés de `context`, `label`) |
| `coordonnees_et_rayon` | Coordonnées géocodées + rayon demandé par l'utilisateur |
| `infrastructures` (table détaillée) | Liste triée par distance issue d'Overpass, avec nom OSM réel et distance haversine calculée |
| `niveau_confiance` | Score additif dont chaque terme cite une condition vérifiable (présence de coordonnées, nombre d'infrastructures, cohérence administrative) |
| `limites_analyse` | Constats structurels du pipeline (absence de coordonnées, faible couverture si <3 infrastructures, portée de la taxonomie, troncature en mode flash le cas échéant) |
| `sources` | URLs des API effectivement appelées |

## Incohérence du mode `flash` (relevée à l'Étape 0) — correction

**Choix retenu : calculer tous les comptages narratifs sur la liste complète, y compris
en mode flash ; ne tronquer que l'affichage détaillé de la table `infrastructures`, avec
une mention explicite dans `limites_analyse`.**

Justification : l'alternative (tronquer avant le calcul du score) aurait fait mentir le
score de confiance sur le nombre réel d'infrastructures disponibles — hors de propos
pour un score censé refléter la fiabilité de la collecte. Tronquer uniquement
l'affichage, avec disclosure explicite, permet au mode flash de rester un format
allégé sans jamais faire dire au rapport un nombre différent de celui utilisé pour le
score. Testé dans `test_flash_mode_truncates_display_but_not_counts`.

## Ce qui n'a pas été touché (hors périmètre)

- `docs/architecture.md` et `docs/roadmap.md` référencent encore l'ancienne architecture
  et l'ancienne taxonomie (signalé aux Étapes 2 et 3, non corrigé).
- La valeur `NOMINATIM_USER_AGENT` du `backend/.env` de développement local n'a pas été
  modifiée (fichier gitignored, appartient à l'utilisateur) — mais l'audit démontre
  concrètement qu'elle doit être changée avant tout usage réel.
