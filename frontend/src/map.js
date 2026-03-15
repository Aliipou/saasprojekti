/**
 * map.js — Leaflet map initialisation + station marker rendering.
 *
 * Owns the map instance and all station layers.
 * Does NOT fetch data — caller passes GeoJSON.
 */

import { tempColour, windColour, precipColour } from './layers.js';

const FINLAND_CENTER = [65.0, 26.0];
const FINLAND_ZOOM   = 5;

/** @typedef {'temp'|'wind'|'precip'} LayerMode */

export class WeatherMap {
  /**
   * @param {string|HTMLElement} container  Leaflet map container id or element
   */
  constructor(container) {
    this._map = L.map(container, {
      center: FINLAND_CENTER,
      zoom:   FINLAND_ZOOM,
      zoomControl: true,
    });

    // Base tile layers
    this._baseLayers = {
      'CartoDB Positron': L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        { attribution: '© OpenStreetMap © CartoDB', maxZoom: 19 }
      ),
      'OpenStreetMap': L.tileLayer(
        'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        { attribution: '© OpenStreetMap contributors', maxZoom: 19 }
      ),
    };
    this._baseLayers['CartoDB Positron'].addTo(this._map);

    /** @type {L.LayerGroup|null} */
    this._stationLayer  = null;
    this._clusterLayer  = null;
    this._useCluster    = false;

    /** @type {GeoJSON.FeatureCollection|null} */
    this._currentData = null;
    /** @type {LayerMode} */
    this._mode = 'temp';

    L.control.layers(this._baseLayers, {}, { position: 'topright' }).addTo(this._map);
  }

  // ── Public API ───────────────────────────────────────────────

  get leaflet() { return this._map; }

  /**
   * Render a GeoJSON FeatureCollection as station markers.
   * @param {GeoJSON.FeatureCollection} geojson
   * @param {LayerMode} mode
   */
  render(geojson, mode = this._mode) {
    this._currentData = geojson;
    this._mode = mode;
    this._rebuildLayer();
  }

  /** Switch the colouring mode and re-render. */
  setMode(mode) {
    this._mode = mode;
    if (this._currentData) this._rebuildLayer();
  }

  /** Toggle marker clustering. */
  setCluster(enabled) {
    this._useCluster = enabled;
    if (this._currentData) this._rebuildLayer();
  }

  /** Fit map bounds to the current station set. */
  fitStations() {
    if (!this._currentData?.features.length) return;
    const coords = this._currentData.features.map(f => [
      f.geometry.coordinates[1],
      f.geometry.coordinates[0],
    ]);
    this._map.fitBounds(L.latLngBounds(coords).pad(0.1));
  }

  /** Draw a rectangle on the map; returns { remove, getBounds } */
  startBboxDraw(onComplete) {
    let rect = null, start = null;

    const onClick = e => {
      if (!start) {
        start = e.latlng;
      } else {
        const bounds = L.latLngBounds(start, e.latlng);
        if (rect) this._map.removeLayer(rect);
        rect = L.rectangle(bounds, { color: '#7c6af7', weight: 2, fillOpacity: 0.1 }).addTo(this._map);
        this._map.off('click', onClick);
        this._map.getContainer().style.cursor = '';
        onComplete({
          bbox: `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`,
          remove: () => { if (rect) this._map.removeLayer(rect); rect = null; },
        });
        start = null;
      }
    };

    this._map.getContainer().style.cursor = 'crosshair';
    this._map.on('click', onClick);
    return { cancel: () => { this._map.off('click', onClick); this._map.getContainer().style.cursor = ''; } };
  }

  // ── Private ──────────────────────────────────────────────────

  _rebuildLayer() {
    if (this._stationLayer) { this._map.removeLayer(this._stationLayer); this._stationLayer = null; }
    if (this._clusterLayer) { this._map.removeLayer(this._clusterLayer); this._clusterLayer = null; }

    const markers = this._currentData.features.map(f => this._makeMarker(f));

    if (this._useCluster && typeof L.markerClusterGroup === 'function') {
      this._clusterLayer = L.markerClusterGroup({ maxClusterRadius: 40 });
      markers.forEach(m => this._clusterLayer.addLayer(m));
      this._clusterLayer.addTo(this._map);
    } else {
      this._stationLayer = L.layerGroup(markers).addTo(this._map);
    }
  }

  /** @param {GeoJSON.Feature} feature */
  _makeMarker(feature) {
    const p = feature.properties;
    const [lon, lat] = feature.geometry.coordinates;

    const colour = this._modeColour(p);
    const radius = this._modeRadius(p);

    const marker = L.circleMarker([lat, lon], {
      radius,
      color:       colour,
      fillColor:   colour,
      fillOpacity: 0.85,
      weight:      1.5,
    });

    marker.bindTooltip(this._tooltipText(p), { sticky: true, opacity: 0.9 });
    marker.bindPopup(this._popupHtml(p, colour), { maxWidth: 260 });
    return marker;
  }

  _modeColour(p) {
    switch (this._mode) {
      case 'wind':   return windColour(p.wind_speed_ms);
      case 'precip': return precipColour(p.precipitation_mmh);
      default:       return tempColour(p.temperature_c);
    }
  }

  _modeRadius(p) {
    if (this._mode === 'wind' && isFinite(p.wind_speed_ms)) {
      return Math.max(5, Math.min(18, 5 + p.wind_speed_ms));
    }
    return 8;
  }

  _tooltipText(p) {
    const temp = isFinite(p.temperature_c) ? `${p.temperature_c.toFixed(1)} °C` : '–';
    return `<b>${p.station_name}</b>  ${temp}`;
  }

  _popupHtml(p, colour) {
    const fmt = (v, d = 1, u = '') =>
      (isFinite(v) ? `${v.toFixed(d)}${u ? ' ' + u : ''}` : '–');
    const ts = p.observed_at ? new Date(p.observed_at).toLocaleString('fi-FI') : '';
    const rows = [
      ['Lämpötila', fmt(p.temperature_c, 1, '°C')],
      ['Tuuli',     fmt(p.wind_speed_ms, 1, 'm/s')],
      ['Sademäärä', fmt(p.precipitation_mmh, 2, 'mm/h')],
      ['Kosteus',   fmt(p.humidity_pct, 0, '%')],
      ['Paine',     fmt(p.pressure_hpa, 1, 'hPa')],
    ];
    const extra = Object.entries(p.extra ?? {})
      .map(([k, v]) => `<tr><td>${k}</td><td>${isFinite(v) ? v.toFixed(2) : '–'}</td></tr>`)
      .join('');
    const rowHtml = rows.map(([k, v]) =>
      `<tr><td>${k}</td><td style="color:${colour};font-weight:700">${v}</td></tr>`
    ).join('');
    return `
      <div class="station-popup">
        <h4>${p.station_name}</h4>
        <table>${rowHtml}${extra}</table>
        <div class="ts">${ts}</div>
      </div>`;
  }
}
