/**
 * wfs.js — Fetch weather observation GeoJSON from the saa-wfs FastAPI backend.
 *
 * All functions return plain objects/GeoJSON — no Leaflet dependency here.
 */

const API_BASE = 'http://localhost:8000';

/**
 * @typedef {Object} FetchObsOptions
 * @property {number}        [hours=1]
 * @property {string|null}   [place=null]
 * @property {string|null}   [bbox=null]   "lon_min,lat_min,lon_max,lat_max"
 * @property {string|null}   [parameters=null]
 */

/**
 * Fetch latest observations as a GeoJSON FeatureCollection.
 * @param {FetchObsOptions} opts
 * @param {AbortSignal}     [signal]
 * @returns {Promise<GeoJSON.FeatureCollection>}
 */
export async function fetchObservations(opts = {}, signal) {
  const { hours = 1, place = null, bbox = null, parameters = null } = opts;

  const params = new URLSearchParams({ hours: String(hours) });
  if (place)      params.set('place',      place);
  if (bbox)       params.set('bbox',       bbox);
  if (parameters) params.set('parameters', parameters);

  const resp = await fetch(`${API_BASE}/api/observations?${params}`, {
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!resp.ok) {
    const msg = await resp.text().catch(() => resp.statusText);
    throw new APIError(resp.status, msg);
  }
  return resp.json();
}

/**
 * Fetch a multi-step time series for animation.
 * Returns an array of FeatureCollections, one per time step,
 * ordered oldest → newest.
 * @param {FetchObsOptions & { steps?: number }} opts
 * @param {AbortSignal} [signal]
 * @returns {Promise<{ timestamp: string, geojson: GeoJSON.FeatureCollection }[]>}
 */
export async function fetchTimeSeries(opts = {}, signal) {
  const { hours = 6, steps = 6, place = null, bbox = null } = opts;
  const params = new URLSearchParams({
    hours: String(hours),
    steps: String(steps),
  });
  if (place) params.set('place', place);
  if (bbox)  params.set('bbox',  bbox);

  const resp = await fetch(`${API_BASE}/api/timeseries?${params}`, {
    headers: { Accept: 'application/json' },
    signal,
  });
  if (!resp.ok) {
    const msg = await resp.text().catch(() => resp.statusText);
    throw new APIError(resp.status, msg);
  }
  return resp.json();  // Array<{ timestamp, geojson }>
}

/** Structured API error. */
export class APIError extends Error {
  constructor(status, message) {
    super(message);
    this.name   = 'APIError';
    this.status = status;
  }
}

/**
 * Extract the numeric value of a specific property from GeoJSON features.
 * Returns an array of [min, max] or [0, 0] for empty sets.
 * @param {GeoJSON.FeatureCollection} geojson
 * @param {string} property
 */
export function featureRange(geojson, property) {
  const vals = geojson.features
    .map(f => f.properties[property])
    .filter(v => typeof v === 'number' && isFinite(v));
  if (!vals.length) return [0, 0];
  return [Math.min(...vals), Math.max(...vals)];
}
