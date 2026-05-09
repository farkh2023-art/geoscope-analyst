/* ─────────────────────────────────────────
   GeoScope Analyst — app.js  v0.3.0
   Carte interactive Leaflet.js + UI
───────────────────────────────────────── */

let lastResponse   = null;
let leafletMap     = null;
let isOffline      = false;
let categoryLayers = {};   // { cat: L.LayerGroup }
let categoryActive = {};   // { cat: boolean }
let clickMarker        = null; // référence Leaflet courante (invalidée à chaque renderMap)
let selectedClickPoint = null; // {lat, lon} — persiste entre les cartes

const HISTORY_KEY = 'geoscope_history';
const MAX_HISTORY = 5;

/* Couleurs par catégorie d'infrastructure */
const CAT_COLORS = {
  transport:      '#4f8ef7',
  'santé':        '#f46060',
  'éducation':    '#3ecf8e',
  'énergie':      '#f59e42',
  eau:            '#22d3ee',
  industrie:      '#94a3b8',
  administratif:  '#a78bfa',
  environnement:  '#4ade80',
  autre:          '#64748b',
};

/* ── Health check au chargement ── */
async function checkHealth() {
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    isOffline = d.offline_mode;
    if (isOffline) document.getElementById('offlineBadge').classList.remove('hidden');
  } catch (_) {}
}

/* ── Analyse principale ── */
async function runAnalysis() {
  const input = document.getElementById('inputField').value.trim();
  if (!input) { showError('Veuillez saisir des coordonnées, une URL ou un nom de lieu.'); return; }

  /* Vider le point sélectionné si l'input a changé (analyse manuelle sans clic carte) */
  if (selectedClickPoint) {
const expected = `${selectedClickPoint.lat.toFixed(6)},${selectedClickPoint.lon.toFixed(6)}`;
    if (input !== expected) selectedClickPoint = null;
  }

  const radius_m = parseInt(document.getElementById('radiusField').value);
  const mode     = document.getElementById('modeField').value;

  setLoading(true);
  hideError();
  document.getElementById('resultsSection').classList.add('hidden');

  try {
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input, radius_m, mode }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `Erreur HTTP ${resp.status}`);
    }
    const data = await resp.json();
    lastResponse = data;
    saveToHistory(data, input, radius_m);
    renderResults(data, radius_m);
  } catch (e) {
    showError(e.message);
  } finally {
    setLoading(false);
  }
}

/* ── Rendu global ── */
function renderResults(data, radius_m) {
  renderLocation(data.location);
  renderConfidence(data.confidence);
  renderWarnings(data.warnings);
  renderMap(data.location, data.infrastructures, radius_m);
  renderInfrastructures(data.infrastructures);
  renderReport(data.report);
  renderSources(data.sources);
  document.getElementById('resultsSection').classList.remove('hidden');
  document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

/* ── Carte Leaflet ── */
function renderMap(location, infrastructures, radius_m) {
  const container = document.getElementById('mapContainer');

  /* Détruire la carte précédente */
  if (leafletMap) { leafletMap.remove(); leafletMap = null; }
  container.innerHTML = '';
  categoryLayers = {};
  categoryActive = {};
  clickMarker = null;

  /* Réinitialiser la note hors-ligne */
  document.getElementById('mapOfflineNote').classList.add('hidden');

  if (!location.coordinates) {
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:0.9rem;">Coordonnées non disponibles — carte non affichable.</div>';
    document.getElementById('mapLegend').innerHTML = '';
    document.getElementById('mapToggleBar').classList.add('hidden');
    return;
  }

  const { lat, lon } = location.coordinates;

  leafletMap = L.map(container, {
    center: [lat, lon], zoom: 13, zoomControl: true, attributionControl: true,
  });

  /* Clic sur la carte → remplir input + lancer analyse */
  leafletMap.on('click', onMapClick);

  const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  });
  tileLayer.on('tileerror', () => document.getElementById('mapOfflineNote').classList.remove('hidden'));
  tileLayer.addTo(leafletMap);

  /* Cercle rayon d'analyse */
  L.circle([lat, lon], {
    radius: radius_m, color: '#4f8ef7', fillColor: '#4f8ef7',
    fillOpacity: 0.06, weight: 1.5, dashArray: '6 4',
  }).addTo(leafletMap);

  /* Marqueur principal */
  const locIcon = L.divIcon({
    html: `<div style="width:18px;height:18px;background:#4f8ef7;border:3px solid #fff;border-radius:50%;box-shadow:0 0 0 3px rgba(79,142,247,0.4);"></div>`,
    className: '', iconSize: [18, 18], iconAnchor: [9, 9],
  });
  const city    = location.city || location.display_name || 'Zone analysée';
  const country = location.country || '';
  L.marker([lat, lon], { icon: locIcon })
    .addTo(leafletMap)
    .bindPopup(`
      <strong>${city}</strong><br>
      ${country ? country + '<br>' : ''}
      <span style="color:var(--text-muted);font-size:0.8rem">${lat.toFixed(5)}, ${lon.toFixed(5)}</span>
    `, { maxWidth: 220 })
    .openPopup();

  /* Couches par catégorie + marqueurs */
  const catCounts = {};
  infrastructures.forEach(infra => {
    const cat   = infra.category;
    const color = CAT_COLORS[cat] || CAT_COLORS.autre;

    if (!categoryLayers[cat]) {
      categoryLayers[cat] = L.layerGroup().addTo(leafletMap);
      categoryActive[cat] = true;
      catCounts[cat] = 0;
    }
    catCounts[cat]++;

    const seed = infra.name.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    const dLat = ((seed % 17) - 8) * 0.0008;
    const dLon = ((seed % 13) - 6) * 0.0010;

    const tags = Object.entries(infra.osm_tags || {})
      .map(([k, v]) => `<span style="opacity:.7">${k}</span>: ${v}`).join('<br>');

    L.circleMarker([lat + dLat, lon + dLon], {
      radius: 6, fillColor: color, color: '#fff', weight: 1.5, fillOpacity: 0.9,
    })
      .bindPopup(`
        <strong>${infra.name}</strong><br>
        <span style="color:${color};font-weight:600">${cat}</span> · ${infra.type}<br>
        ${tags ? `<br><small>${tags}</small>` : ''}
        <br><small style="opacity:.6">Source : ${infra.source}</small>
      `, { maxWidth: 220 })
      .addTo(categoryLayers[cat]);
  });

  /* Légende interactive */
  renderLegend(Object.keys(categoryLayers), catCounts);

  /* Boutons tout afficher / masquer */
  const toggleBar = document.getElementById('mapToggleBar');
  toggleBar.classList.toggle('hidden', Object.keys(categoryLayers).length < 2);

  /* Re-placer le marqueur "Point sélectionné" après chaque analyse */
  if (selectedClickPoint) {
    clickMarker = L.marker(
      [selectedClickPoint.lat, selectedClickPoint.lon],
      { icon: _makeClickIcon() }
    )
      .addTo(leafletMap)
      .bindPopup(
        `<strong style="color:#f59e42">Point sélectionné</strong><br>
         <small>${selectedClickPoint.lat.toFixed(5)}, ${selectedClickPoint.lon.toFixed(5)}</small>`,
        { maxWidth: 180 }
      );
  }

  if (isOffline) document.getElementById('mapOfflineNote').classList.remove('hidden');
}

/* ── Clic carte → analyse automatique ── */
function onMapClick(e) {
  const lat = e.latlng.lat;
  const lng = e.latlng.lng;
  const coordStr = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;

  /* Mémoriser les coordonnées pour re-placer le marker après chaque renderMap */
  selectedClickPoint = { lat, lon: lng };

  /* Feedback immédiat : remplacer l'éventuel marker précédent sur la carte courante */
  if (clickMarker) { clickMarker.remove(); clickMarker = null; }
  clickMarker = L.marker([lat, lng], { icon: _makeClickIcon() })
    .addTo(leafletMap)
    .bindPopup(
      `<strong style="color:#f59e42">Point sélectionné</strong><br>
       <small>${lat.toFixed(5)}, ${lng.toFixed(5)}</small>`,
      { maxWidth: 180 }
    )
    .openPopup();

  document.getElementById('inputField').value = coordStr;
  runAnalysis();
}

function _makeClickIcon() {
  return L.divIcon({
    html: `<div style="
      width:14px;height:14px;
      background:#f59e42;
      border:2px solid #fff;
      border-radius:50%;
      box-shadow:0 0 0 3px rgba(245,158,66,0.45);
    "></div>`,
    className: '', iconSize: [14, 14], iconAnchor: [7, 7],
  });
}

/* ── Légende interactive ── */
function renderLegend(categories, counts) {
  const legendEl = document.getElementById('mapLegend');
  legendEl.innerHTML = categories.map(cat => {
    const color  = CAT_COLORS[cat] || CAT_COLORS.autre;
    const count  = counts[cat] || 0;
    const active = categoryActive[cat] !== false;
    return `<div class="legend-item${active ? '' : ' legend-inactive'}" data-cat="${cat}"
              onclick="toggleCategory('${escapeSQ(cat)}')">
      <div class="legend-dot" style="background:${color}"></div>
      <span>${cat} <small class="legend-count">(${count})</small></span>
    </div>`;
  }).join('');

  /* Entrée "Point sélectionné" si un clic carte est actif */
  if (selectedClickPoint) {
    legendEl.innerHTML += `<div class="legend-item legend-click-point">
      <div class="legend-dot" style="background:#f59e42;box-shadow:0 0 0 2px rgba(245,158,66,0.4);"></div>
      <span>Point sélectionné</span>
    </div>`;
  }
}

function escapeSQ(s) { return s.replace(/\\/g, '\\\\').replace(/'/g, "\\'"); }

/* ── Toggle catégorie ── */
function toggleCategory(cat) {
  if (!categoryLayers[cat] || !leafletMap) return;
  categoryActive[cat] = !categoryActive[cat];
  if (categoryActive[cat]) {
    categoryLayers[cat].addTo(leafletMap);
  } else {
    leafletMap.removeLayer(categoryLayers[cat]);
  }
  document.querySelectorAll('.legend-item').forEach(el => {
    if (el.dataset.cat === cat) el.classList.toggle('legend-inactive', !categoryActive[cat]);
  });
}

function showAllCategories() {
  Object.keys(categoryLayers).forEach(cat => { if (!categoryActive[cat]) toggleCategory(cat); });
}

function hideAllCategories() {
  Object.keys(categoryLayers).forEach(cat => { if (categoryActive[cat]) toggleCategory(cat); });
}

/* ── Localisation ── */
function renderLocation(loc) {
  const rows = [
    ['Adresse', loc.display_name || '—'],
    ['Pays', loc.country || '—'],
    ['Région', loc.region || '—'],
    ['Département', loc.department || '—'],
    ['Ville', loc.city || '—'],
    ['Quartier', loc.neighborhood || '—'],
    ['Type d\'entrée', loc.input_type || '—'],
  ];
  if (loc.coordinates) {
    rows.splice(1, 0, ['Coordonnées', `${loc.coordinates.lat.toFixed(5)}, ${loc.coordinates.lon.toFixed(5)}`]);
  }
  document.getElementById('locationContent').innerHTML =
    `<table class="info-table">${rows.map(([k, v]) =>
      `<tr><td>${k}</td><td>${v}</td></tr>`).join('')}</table>`;
}

/* ── Confiance ── */
function renderConfidence(conf) {
  const lvl = conf.label === 'élevé' ? 'eleve' : conf.label === 'moyen' ? 'moyen' : 'faible';
  document.getElementById('confidenceContent').innerHTML = `
    <div class="confidence-score level-${lvl}">${conf.score}</div>
    <div class="confidence-label level-${lvl}">${conf.label.toUpperCase()}</div>
    <div class="confidence-bar-bg">
      <div class="confidence-bar bar-${lvl}" style="width:${conf.score}%"></div>
    </div>
    <div class="confidence-justification">${conf.justification}</div>
  `;
}

/* ── Avertissements ── */
function renderWarnings(warnings) {
  const section = document.getElementById('warningsSection');
  if (!warnings || warnings.length === 0) { section.classList.add('hidden'); return; }
  document.getElementById('warningsList').innerHTML = warnings.map(w => `<li>${w}</li>`).join('');
  section.classList.remove('hidden');
}

/* ── Infrastructures ── */
function renderInfrastructures(infras) {
  const content   = document.getElementById('infraContent');
  const filterBar = document.getElementById('infraFilterBar');

  if (!infras || infras.length === 0) {
    content.innerHTML = '<p style="color:var(--text-muted)">Aucune infrastructure détectée.</p>';
    filterBar.classList.add('hidden');
    return;
  }

  filterBar.classList.remove('hidden');
  document.getElementById('infraFilter').value = '';

  const rows = infras.map(i => {
    const color = CAT_COLORS[i.category] || CAT_COLORS.autre;
    return `<tr>
      <td>${i.name}</td>
      <td>${i.type}</td>
      <td><span class="cat-badge" style="color:${color};border-color:${color}">${i.category}</span></td>
      <td>${i.source}</td>
    </tr>`;
  }).join('');

  content.innerHTML = `
    <table class="infra-table">
      <thead><tr><th>Nom</th><th>Type OSM</th><th>Catégorie</th><th>Source</th></tr></thead>
      <tbody id="infraTbody">${rows}</tbody>
    </table>`;
}

function filterInfraTable() {
  const q = document.getElementById('infraFilter').value.toLowerCase();
  document.querySelectorAll('#infraTbody tr').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

/* ── Rapport ── */
function renderReport(report) {
  const LABELS = {
    resume_executif:                  '📋 Résumé exécutif',
    identification_administrative:    '🏛 Identification administrative',
    coordonnees_et_rayon:             '📐 Coordonnées et rayon',
    description_zone:                 '🗺 Description de la zone',
    connectivite:                     '🔗 Connectivité',
    activites_economiques_probables:  '💼 Activités économiques probables',
    occupation_du_sol_estimee:        '🌿 Occupation du sol',
    sensibilites_environnementales:   '⚡ Sensibilités environnementales',
    contexte_territorial:             '🏙 Contexte territorial',
    niveau_confiance:                 null,
    limites_analyse:                  '⚠ Limites de l\'analyse',
  };

  let html = '';
  for (const [key, label] of Object.entries(LABELS)) {
    if (!label || !(key in report)) continue;
    const val = report[key];
    html += `<div class="report-section"><h3>${label}</h3>`;
    if (typeof val === 'string') html += `<p>${val}</p>`;
    else if (Array.isArray(val)) html += `<ul>${val.map(v => `<li>${v}</li>`).join('')}</ul>`;
    else if (typeof val === 'object') html += `<ul>${Object.entries(val).map(([k, v]) =>
      `<li><strong>${k.replace(/_/g, ' ')}:</strong> ${v}</li>`).join('')}</ul>`;
    html += '</div>';
  }
  document.getElementById('reportContent').innerHTML =
    html || '<p style="color:var(--text-muted)">Rapport non disponible.</p>';
}

/* ── Sources ── */
function renderSources(sources) {
  if (!sources || sources.length === 0) {
    document.getElementById('sourcesList').innerHTML = '<li>Aucune source disponible.</li>';
    return;
  }
  document.getElementById('sourcesList').innerHTML = sources.map(s => {
    const m = s.match(/https?:\/\/\S+/);
    if (m) {
      const label = s.replace(m[0], '').trim().replace(/[·\-—]/, '').trim();
      return `<li>${label} — <a href="${m[0]}" target="_blank" rel="noopener">${m[0]}</a></li>`;
    }
    return `<li>${s}</li>`;
  }).join('');
}

/* ── Export JSON ── */
function exportJSON() {
  if (!lastResponse) return;
  triggerDownload(
    new Blob([JSON.stringify(lastResponse, null, 2)], { type: 'application/json' }),
    'geoscope_rapport.json',
  );
}

/* ── Export Markdown ── */
async function exportMarkdown() {
  if (!lastResponse) return;
  try {
    const resp = await fetch('/api/export/markdown', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lastResponse),
    });
    const text = await resp.text();
    triggerDownload(new Blob([text], { type: 'text/markdown' }), 'geoscope_rapport.md');
  } catch (e) {
    showError('Erreur export Markdown : ' + e.message);
  }
}

/* ── Export GeoJSON ── */
function exportGeoJSON() {
  if (!lastResponse) return;
  const loc      = lastResponse.location;
  const features = [];

  if (loc.coordinates) {
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [loc.coordinates.lon, loc.coordinates.lat] },
      properties: {
        name:       loc.display_name || loc.city || 'Zone analysée',
        type:       'location',
        country:    loc.country,
        city:       loc.city,
        confidence: lastResponse.confidence.score,
      },
    });
  }

  lastResponse.infrastructures.forEach(infra => {
    if (!loc.coordinates) return;
    const seed = infra.name.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    const dLat = ((seed % 17) - 8) * 0.0008;
    const dLon = ((seed % 13) - 6) * 0.0010;
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [loc.coordinates.lon + dLon, loc.coordinates.lat + dLat] },
      properties: {
        name: infra.name, type: infra.type, category: infra.category,
        source: infra.source, osm_tags: infra.osm_tags,
      },
    });
  });

  triggerDownload(
    new Blob([JSON.stringify({ type: 'FeatureCollection', features }, null, 2)], { type: 'application/geo+json' }),
    'geoscope_carte.geojson',
  );
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a   = Object.assign(document.createElement('a'), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}

/* ── Historique localStorage ── */
function saveToHistory(data, input, radius_m) {
  let hist = getHistory();
  hist.unshift({
    ts:         Date.now(),
    input:      input,
    radius_m:   radius_m,
    city:       data.location.city || data.location.display_name || input,
    country:    data.location.country || '',
    confidence: data.confidence.score,
    label:      data.confidence.label,
    data:       data,
  });
  localStorage.setItem(HISTORY_KEY, JSON.stringify(hist.slice(0, MAX_HISTORY)));
  renderHistory();
}

function getHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
  catch { return []; }
}

function restoreAnalysis(index) {
  const entry = getHistory()[index];
  if (!entry) return;
  document.getElementById('inputField').value   = entry.input;
  document.getElementById('radiusField').value  = entry.radius_m || 1500;
  lastResponse = entry.data;
  renderResults(entry.data, entry.radius_m || 1500);
}

function clearHistory() {
  if (!confirm('Effacer tout l\'historique des analyses ?')) return;
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
}

function renderHistory() {
  const hist   = getHistory();
  const panel  = document.getElementById('historyPanel');
  const listEl = document.getElementById('historyList');
  if (!hist.length) { panel.classList.add('hidden'); return; }
  panel.classList.remove('hidden');
  listEl.innerHTML = hist.map((entry, i) => {
    const when  = new Date(entry.ts).toLocaleString('fr-FR', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    });
    const place = entry.city + (entry.country ? ', ' + entry.country : '');
    const lvl   = entry.label === 'élevé' ? 'eleve' : entry.label === 'moyen' ? 'moyen' : 'faible';
    const inp   = entry.input.length > 42 ? entry.input.slice(0, 42) + '…' : entry.input;
    return `<div class="history-item" onclick="restoreAnalysis(${i})" title="Restaurer cette analyse">
      <div class="history-info">
        <span class="history-place">${place}</span>
        <span class="history-score level-${lvl}">${entry.confidence}/100</span>
      </div>
      <div class="history-meta">${when} · <code>${inp}</code></div>
    </div>`;
  }).join('');
}

/* ── UI helpers ── */
function setLoading(on) {
  document.getElementById('analyzeBtn').disabled = on;
  document.getElementById('btnText').textContent = on ? 'Analyse en cours…' : 'Analyser';
  document.getElementById('btnSpinner').classList.toggle('hidden', !on);
}
function showError(msg) {
  const b = document.getElementById('errorBox');
  b.textContent = msg;
  b.classList.remove('hidden');
}
function hideError() { document.getElementById('errorBox').classList.add('hidden'); }

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  renderHistory();
  document.getElementById('inputField').addEventListener('keydown', e => {
    if (e.key === 'Enter') runAnalysis();
  });
});
