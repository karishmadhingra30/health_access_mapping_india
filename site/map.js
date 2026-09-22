const map = L.map('map', { scrollWheelZoom: true }).setView([23.8, 82.4], 5);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const clusters = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 48 });
let datasets = { facilities: null, districts: null, grid: null, metadata: null };
let activeOverlay = null;

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? 'Not stated').replace(/[&<>'"]/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[char]));
const sector = () => $('sector-select').value;
const state = () => $('state-select').value;
const selected = () => document.querySelector('input[name="metric"]:checked').value;

function visible(feature) {
  const p = feature.properties;
  return (state() === 'all' || p.state === state()) && (sector() === 'all' || p.sector === sector());
}
function color(value, breaks, colors) {
  if (value === null || value === undefined) return '#b6bcc0';
  return colors.find((_, index) => value <= breaks[index]) || colors.at(-1);
}
function setLegend(text) { $('legend').textContent = text; }
function removeOverlay() { if (activeOverlay) map.removeLayer(activeOverlay); activeOverlay = null; map.removeLayer(clusters); clusters.clearLayers(); }
function facilityPopup(p) {
  const services = p.services?.length ? p.services.map(escapeHtml).join(', ') : 'Not listed by source';
  return `<strong>${escapeHtml(p.name)}</strong><br>${escapeHtml(p.facility_type)} · ${escapeHtml(p.sector)}<br>${escapeHtml(p.district)}, ${escapeHtml(p.state)}<br><b>Services:</b> ${services}<br><b>Location:</b> ${escapeHtml(p.geocode_precision)}<br><a href="${escapeHtml(p.source_url)}" target="_blank" rel="noreferrer">View source ↗</a>`;
}
function showFacilities() {
  datasets.facilities.features.filter(visible).forEach(feature => {
    const [lon, lat] = feature.geometry.coordinates;
    clusters.addLayer(L.marker([lat, lon]).bindPopup(facilityPopup(feature.properties)));
  });
  map.addLayer(clusters);
  setLegend('Points are source-listed facilities. Filtered sectors reflect the source’s tags, which can be incomplete.');
}
function showDistricts(metric) {
  const isPerCapita = metric === 'percapita';
  activeOverlay = L.geoJSON(datasets.districts, {
    filter: feature => state() === 'all' || feature.properties.state === state(),
    style: feature => ({ color:'#ffffff', weight:1, fillOpacity:.72, fillColor: isPerCapita ? color(feature.properties.facilities_per_100k, [1, 3, 8, 20], ['#e4eff0','#9ecfd0','#4f9fa1','#075f63','#013d40']) : color(feature.properties.services_available_count, [0, 2, 5, 8], ['#f3e8d2','#e5bb6b','#9abf8d','#3d8962','#075f63']) }),
    onEachFeature: (feature, layer) => layer.bindPopup(`<strong>${escapeHtml(feature.properties.district)}</strong><br>${isPerCapita ? `Facilities per 100,000 (Census 2011): <b>${escapeHtml(feature.properties.facilities_per_100k ?? 'No data')}</b><br>Mapped facilities: ${escapeHtml(feature.properties.facility_count ?? 'No data')}` : `Services found: <b>${escapeHtml(feature.properties.services_available_count)} / 11</b><br><b>Not evidenced in listed data:</b><ul class="popup-list">${(feature.properties.services_missing || []).map(s => `<li>${escapeHtml(s)}</li>`).join('') || '<li>None</li>'}</ul>`}`)
  }).addTo(map);
  setLegend(isPerCapita ? 'Shared scale, both states: pale = ≤1; dark = >20 facilities per 100,000. Grey = no population match/data.' : 'Service tags evidenced in at least one mapped facility. This measures source evidence, not actual availability.');
}
function showDistance() {
  activeOverlay = L.geoJSON(datasets.grid, { filter: feature => state() === 'all' || feature.properties.state === state(), style: feature => ({ color:'transparent', fillOpacity:.62, fillColor: color(feature.properties.distance_km, [2, 5, 10, 25], ['#d4eee5','#92cfbf','#e6c86d','#d9824e','#a44638']) }), onEachFeature: (feature, layer) => layer.bindPopup(`<b>${escapeHtml(feature.properties.distance_km)} km</b> straight-line distance to the nearest mapped facility`) }).addTo(map);
  setLegend('Shared straight-line distance scale: green = closer; red = farther. It does not measure roads, travel time, cost, or opening hours.');
}
function redraw() {
  if (!datasets.facilities) return;
  removeOverlay();
  if (selected() === 'facilities') showFacilities();
  if (selected() === 'percapita' || selected() === 'services') showDistricts(selected());
  if (selected() === 'distance') showDistance();
}
function zoomToState() {
  if (state() === 'all') { map.setView([23.8, 82.4], 5); return; }
  const stateFeature = datasets.districts.features.filter(f => f.properties.state === state());
  if (stateFeature.length) map.fitBounds(L.geoJSON({ type:'FeatureCollection', features: stateFeature }).getBounds(), { padding:[18,18] });
}
function showMetadata(metadata) {
  datasets.metadata = metadata;
  const sourceWarnings = (metadata.sources || []).filter(source => ['failed', 'partial', 'stale_cache_after_error'].includes(source.status));
  const attempted = metadata.last_attempted_refresh_at && metadata.last_attempted_refresh_at !== metadata.refreshed_at ? `<dt>Last refresh attempt</dt><dd>${escapeHtml(metadata.last_attempted_refresh_at)}</dd>` : '';
  $('refresh-status').innerHTML = `<dt>Refresh status</dt><dd>${escapeHtml(metadata.refresh_status || 'No successful refresh published yet')}</dd><dt>Data snapshot</dt><dd>${escapeHtml(metadata.refreshed_at || 'No successful refresh published yet')}</dd>${attempted}<dt>Mapped facilities</dt><dd>${escapeHtml(metadata.facility_count ?? 'No data')}</dd><dt>Location precision</dt><dd>${escapeHtml(metadata.geocode_precision?.exact ?? 0)} exact; ${escapeHtml(metadata.geocode_precision?.approximated ?? 0)} approximated</dd>${sourceWarnings.length ? `<dt>Source warnings</dt><dd>${sourceWarnings.map(source => escapeHtml(`${source.name}: ${source.status}`)).join('<br>')}</dd>` : ''}`;
}
Promise.all(['facilities', 'districts', 'grid', 'refresh_metadata'].map(name => fetch(`data/${name}.geojson`.replace('_metadata.geojson', '_metadata.json')).then(response => response.ok ? response.json() : Promise.reject(new Error(name))))).then(([facilities, districts, grid, metadata]) => { datasets = { facilities, districts, grid, metadata }; showMetadata(metadata); redraw(); }).catch(() => { $('refresh-status').innerHTML = '<dt>Status</dt><dd>No published refresh yet. Run the manual GitHub Actions refresh workflow.</dd>'; setLegend('Waiting for the first data snapshot.'); });
document.querySelectorAll('input[name="metric"]').forEach(input => input.addEventListener('change', redraw));
$('sector-select').addEventListener('change', redraw);
$('state-select').addEventListener('change', () => { redraw(); zoomToState(); });
