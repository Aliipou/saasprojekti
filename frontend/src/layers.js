/**
 * layers.js — Colour scales and legend data for all map layers.
 *
 * Pure functions; no Leaflet dependency.
 */

// ── Temperature ─────────────────────────────────────────────

/** @type {[number, string, string][]}  [minThreshold, hex, label] */
export const TEMP_BANDS = [
  [-99,  '#1565C0', 'Pakkanen (< 0 °C)'],
  [  0,  '#42A5F5', 'Viileä (0 – 10 °C)'],
  [ 10,  '#66BB6A', 'Leuto (10 – 20 °C)'],
  [ 20,  '#FFA726', 'Lämmin (20 – 28 °C)'],
  [ 28,  '#E53935', 'Kuuma (≥ 28 °C)'],
];

/** @param {number} t @returns {string} hex colour */
export function tempColour(t) {
  if (!isFinite(t)) return '#9E9E9E';
  for (let i = TEMP_BANDS.length - 1; i >= 0; i--) {
    if (t >= TEMP_BANDS[i][0]) return TEMP_BANDS[i][1];
  }
  return TEMP_BANDS[0][1];
}

// ── Wind speed ───────────────────────────────────────────────

export const WIND_BANDS = [
  [  0, '#B3E5FC', 'Tyyntö (0 – 3 m/s)'],
  [  3, '#4FC3F7', 'Heikko (3 – 8 m/s)'],
  [  8, '#0288D1', 'Kohtalainen (8 – 14 m/s)'],
  [ 14, '#FF8F00', 'Navakka (14 – 21 m/s)'],
  [ 21, '#D32F2F', 'Myrsky (≥ 21 m/s)'],
];

export function windColour(w) {
  if (!isFinite(w)) return '#9E9E9E';
  for (let i = WIND_BANDS.length - 1; i >= 0; i--) {
    if (w >= WIND_BANDS[i][0]) return WIND_BANDS[i][1];
  }
  return WIND_BANDS[0][1];
}

// ── Precipitation ────────────────────────────────────────────

export const PRECIP_BANDS = [
  [    0, '#E8F5E9', 'Ei sadetta'],
  [ 0.01, '#81C784', 'Heikko (< 1 mm/h)'],
  [    1, '#1E88E5', 'Kohtalainen (1 – 5 mm/h)'],
  [    5, '#7B1FA2', 'Voimakas (≥ 5 mm/h)'],
];

export function precipColour(r) {
  if (!isFinite(r)) return '#9E9E9E';
  for (let i = PRECIP_BANDS.length - 1; i >= 0; i--) {
    if (r >= PRECIP_BANDS[i][0]) return PRECIP_BANDS[i][1];
  }
  return PRECIP_BANDS[0][1];
}

// ── Legend builder ───────────────────────────────────────────

/**
 * Build legend DOM into *container* for the given mode.
 * @param {HTMLElement} container
 * @param {'temp'|'wind'|'precip'} mode
 */
export function buildLegend(container, mode) {
  container.innerHTML = '';
  const bands = mode === 'wind' ? WIND_BANDS : mode === 'precip' ? PRECIP_BANDS : TEMP_BANDS;

  bands.forEach(([, colour, label]) => {
    const item = document.createElement('div');
    item.className = 'legend-item';
    item.innerHTML =
      `<span class="legend-dot" style="background:${colour}"></span>` +
      `<span>${label}</span>`;
    container.appendChild(item);
  });

  // No-data entry
  const nd = document.createElement('div');
  nd.className = 'legend-item';
  nd.innerHTML = '<span class="legend-dot" style="background:#9E9E9E"></span><span>Ei tietoa</span>';
  container.appendChild(nd);
}
