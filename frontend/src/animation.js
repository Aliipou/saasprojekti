/**
 * animation.js — Time-series playback controller.
 *
 * Manages a list of { timestamp, geojson } frames and drives
 * a callback on each step.  Decoupled from Leaflet.
 */

/** @typedef {{ timestamp: string, geojson: GeoJSON.FeatureCollection }} Frame */

export class TimeAnimator {
  /**
   * @param {(frame: Frame, index: number, total: number) => void} onFrame
   *   Called for each animation step with the current frame.
   */
  constructor(onFrame) {
    this._onFrame  = onFrame;
    /** @type {Frame[]} */
    this._frames   = [];
    this._index    = 0;
    this._timer    = null;
    this._speed    = 500;    // ms per step
    this._playing  = false;
  }

  // ── Public API ───────────────────────────────────────────────

  /**
   * Load frames and jump to the last (most recent) one.
   * @param {Frame[]} frames  Ordered oldest → newest
   */
  load(frames) {
    this._frames  = frames;
    this._index   = Math.max(0, frames.length - 1);
    this._playing = false;
    this._clearTimer();
    if (frames.length) this._dispatch();
  }

  /** Start or resume playback. */
  play() {
    if (!this._frames.length || this._playing) return;
    this._playing = true;
    this._tick();
  }

  /** Pause playback (preserves position). */
  pause() {
    this._playing = false;
    this._clearTimer();
  }

  /** Stop and reset to last frame. */
  stop() {
    this._playing = false;
    this._clearTimer();
    this._index = Math.max(0, this._frames.length - 1);
    if (this._frames.length) this._dispatch();
  }

  /** Seek to a specific frame index. */
  seekTo(index) {
    if (index < 0 || index >= this._frames.length) return;
    this._index = index;
    this._dispatch();
  }

  /** Set playback speed in ms per frame. */
  setSpeed(ms) {
    this._speed = Math.max(50, ms);
    if (this._playing) { this._clearTimer(); this._tick(); }
  }

  get isPlaying()   { return this._playing; }
  get frameCount()  { return this._frames.length; }
  get currentIndex(){ return this._index; }
  get currentFrame(){ return this._frames[this._index] ?? null; }

  // ── Private ──────────────────────────────────────────────────

  _tick() {
    this._clearTimer();
    this._timer = setTimeout(() => {
      if (!this._playing) return;
      this._index = (this._index + 1) % this._frames.length;
      this._dispatch();
      // Loop or stop at end
      if (this._index === this._frames.length - 1) {
        this._playing = false;
      } else {
        this._tick();
      }
    }, this._speed);
  }

  _clearTimer() {
    if (this._timer != null) { clearTimeout(this._timer); this._timer = null; }
  }

  _dispatch() {
    const frame = this._frames[this._index];
    if (frame) this._onFrame(frame, this._index, this._frames.length);
  }
}

/**
 * Format an ISO timestamp string for display.
 * @param {string} iso
 * @returns {string}
 */
export function formatTimestamp(iso) {
  try {
    return new Date(iso).toLocaleString('fi-FI', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
