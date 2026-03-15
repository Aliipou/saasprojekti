/**
 * app.js — Main orchestrator for saa-wfs frontend.
 *
 * Coordinates: WeatherMap ↔ WFS API ↔ TimeAnimator ↔ UI helpers
 */

import { WeatherMap }    from './map.js';
import { fetchObservations, fetchTimeSeries, featureRange, APIError } from './wfs.js';
import { TimeAnimator, formatTimestamp } from './animation.js';
import { buildLegend }  from './layers.js';
import {
  showToast, setLoading, updateStationCount,
  updateTempRange, updateLastUpdate, updateTimeLabel, setAnimState,
} from './ui.js';

// ── DOM refs ─────────────────────────────────────────────────

const $ = id => document.getElementById(id);

const fetchBtn    = $('fetch-btn');
const refreshBtn  = $('refresh-btn');
const hoursSlider = $('hours-slider');
const hoursVal    = $('hours-val');
const placeInput  = $('place-input');

const layerTemp    = $('layer-temp');
const layerWind    = $('layer-wind');
const layerPrecip  = $('layer-precip');
const layerCluster = $('layer-cluster');

const bboxDrawBtn  = $('bbox-draw-btn');
const bboxClearBtn = $('bbox-clear-btn');

const animPlay   = $('anim-play');
const animPause  = $('anim-pause');
const animStop   = $('anim-stop');
const timeSlider = $('time-slider');
const animSpeed  = $('anim-speed');

const legendContainer = $('legend-container');
const sidePanel       = $('side-panel');
const panelToggle     = $('panel-toggle');

// ── State ─────────────────────────────────────────────────────

let _abortController = null;
let _bboxState       = null;   // { bbox, remove } | null

// ── Init ──────────────────────────────────────────────────────

const map       = new WeatherMap('map');
const animator  = new TimeAnimator((frame, idx, total) => {
  map.render(frame.geojson);
  updateTimeLabel(frame.timestamp);
  timeSlider.value = String(idx);
  timeSlider.max   = String(total - 1);
  if (!animator.isPlaying) setAnimState('paused');
});

buildLegend(legendContainer, 'temp');

// ── Hours slider live label ───────────────────────────────────

hoursSlider.addEventListener('input', () => {
  hoursVal.textContent = `${hoursSlider.value} h`;
});

// ── Fetch button ──────────────────────────────────────────────

fetchBtn.addEventListener('click', fetchData);
refreshBtn.addEventListener('click', fetchData);

async function fetchData() {
  if (_abortController) _abortController.abort();
  _abortController = new AbortController();

  const opts = {
    hours: Number(hoursSlider.value),
    place: placeInput.value.trim() || null,
    bbox:  _bboxState?.bbox ?? null,
  };

  setLoading(true, 'Haetaan säätietoja FMI WFS:stä…');
  fetchBtn.disabled = true;

  try {
    const geojson = await fetchObservations(opts, _abortController.signal);

    if (!geojson.features.length) {
      showToast('Ei havaintoja valitulle alueelle / ajanjaksolle', 'info');
      return;
    }

    const mode = activeLayerMode();
    map.render(geojson, mode);
    map.fitStations();

    const [tMin, tMax] = featureRange(geojson, 'temperature_c');
    if (isFinite(tMin)) updateTempRange(tMin, tMax);

    updateStationCount(geojson.features.length);
    updateLastUpdate(geojson.meta?.fetched_at ?? new Date());
    showToast(`${geojson.features.length} asemaa ladattu`, 'success');

    // Also load time series for animation (non-blocking)
    loadTimeSeries(opts);

  } catch (err) {
    if (err.name === 'AbortError') return;
    const msg = err instanceof APIError
      ? `Palvelinvirhe (${err.status}): ${err.message}`
      : `Yhteysvirhe: ${err.message}`;
    showToast(msg, 'error');
    console.error(err);
  } finally {
    setLoading(false);
    fetchBtn.disabled = false;
    _abortController = null;
  }
}

async function loadTimeSeries(baseOpts) {
  try {
    const frames = await fetchTimeSeries({ ...baseOpts, hours: 6, steps: 6 });
    animator.load(frames);
    timeSlider.max   = String(Math.max(0, frames.length - 1));
    timeSlider.value = String(frames.length - 1);
    setAnimState('idle');
  } catch {
    // Time series is optional — silently ignore errors
  }
}

// ── Layer toggles ─────────────────────────────────────────────

[layerTemp, layerWind, layerPrecip].forEach(cb => {
  cb.addEventListener('change', () => {
    if (!cb.checked) return;
    // Mutual exclusion for display mode
    [layerTemp, layerWind, layerPrecip].forEach(o => { if (o !== cb) o.checked = false; });
    const mode = activeLayerMode();
    map.setMode(mode);
    buildLegend(legendContainer, mode);
  });
});

layerCluster.addEventListener('change', () => map.setCluster(layerCluster.checked));

function activeLayerMode() {
  if (layerWind.checked)   return 'wind';
  if (layerPrecip.checked) return 'precip';
  return 'temp';
}

// ── Bbox drawing ──────────────────────────────────────────────

bboxDrawBtn.addEventListener('click', () => {
  if (_bboxState) return;
  showToast('Klikkaa ensin, sitten toinen kulma', 'info', 4000);
  map.startBboxDraw(result => {
    _bboxState = result;
    bboxClearBtn.disabled = false;
    bboxDrawBtn.disabled  = true;
    showToast('Alue valittu — hae nyt säätiedot', 'success');
  });
});

bboxClearBtn.addEventListener('click', () => {
  _bboxState?.remove();
  _bboxState        = null;
  bboxClearBtn.disabled = true;
  bboxDrawBtn.disabled  = false;
});

// ── Animation ─────────────────────────────────────────────────

animPlay.addEventListener('click', () => {
  animator.play();
  setAnimState('playing');
});
animPause.addEventListener('click', () => {
  animator.pause();
  setAnimState('paused');
});
animStop.addEventListener('click', () => {
  animator.stop();
  setAnimState('idle');
});

timeSlider.addEventListener('input', () => {
  animator.seekTo(Number(timeSlider.value));
});

animSpeed.addEventListener('change', () => {
  animator.setSpeed(Number(animSpeed.value));
});

// ── Side panel toggle ─────────────────────────────────────────

panelToggle.addEventListener('click', () => {
  sidePanel.classList.toggle('collapsed');
});

// ── Auto-fetch on load ────────────────────────────────────────

fetchData();
