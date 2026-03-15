/**
 * ui.js — UI helpers: toast notifications, loading overlay, status updates.
 */

let _toastTimer = null;

/**
 * Show a toast notification.
 * @param {string}              msg
 * @param {'info'|'success'|'error'} [type='info']
 * @param {number}              [ms=3500]
 */
export function showToast(msg, type = 'info', ms = 3500) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className   = type;
  el.classList.remove('hidden');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.add('hidden'), ms);
}

/**
 * Show / hide the full-page loading overlay.
 * @param {boolean} visible
 * @param {string}  [label]
 */
export function setLoading(visible, label = 'Ladataan…') {
  const overlay = document.getElementById('loading-overlay');
  const lbl     = document.getElementById('loading-label');
  if (!overlay) return;
  if (lbl) lbl.textContent = label;
  overlay.classList.toggle('hidden', !visible);
}

/**
 * Update the station count badge.
 * @param {number} count
 */
export function updateStationCount(count) {
  const el = document.getElementById('station-count');
  if (el) el.textContent = `${count} asemaa`;
}

/**
 * Update the temperature range display in the topbar.
 * @param {number} min
 * @param {number} max
 */
export function updateTempRange(min, max) {
  const minEl = document.getElementById('temp-min');
  const maxEl = document.getElementById('temp-max');
  if (minEl) minEl.textContent = `${min.toFixed(1)} °C`;
  if (maxEl) maxEl.textContent = `${max.toFixed(1)} °C`;
}

/**
 * Update the "last updated" timestamp in the topbar.
 * @param {Date|string} date
 */
export function updateLastUpdate(date) {
  const el = document.getElementById('last-update');
  if (!el) return;
  try {
    el.textContent = new Date(date).toLocaleTimeString('fi-FI');
  } catch {
    el.textContent = String(date);
  }
}

/**
 * Update the time-series label below the time slider.
 * @param {string} isoTimestamp
 */
export function updateTimeLabel(isoTimestamp) {
  const el = document.getElementById('time-label');
  if (!el) return;
  try {
    el.textContent = new Date(isoTimestamp).toLocaleString('fi-FI');
  } catch {
    el.textContent = isoTimestamp;
  }
}

/**
 * Set animation control button states.
 * @param {'idle'|'playing'|'paused'} state
 */
export function setAnimState(state) {
  const play  = document.getElementById('anim-play');
  const pause = document.getElementById('anim-pause');
  const stop  = document.getElementById('anim-stop');
  if (!play) return;
  play.disabled  = state === 'playing';
  pause.disabled = state !== 'playing';
  stop.disabled  = state === 'idle';
}
