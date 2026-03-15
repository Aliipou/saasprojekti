/**
 * renderer.js — High-performance Canvas-based station renderer.
 *
 * For datasets > CLUSTER_THRESHOLD stations, switches from Leaflet DOM
 * markers (slow at 1 000+) to a single Canvas overlay drawn with
 * requestAnimationFrame.  Below the threshold the standard Leaflet
 * CircleMarker path is used (better popups).
 *
 * The canvas is kept in sync with map pan/zoom via Leaflet's
 * L.CanvasRenderer and a custom L.Canvas extension.
 */

const CLUSTER_THRESHOLD = 300;   // switch to canvas above this count

/**
 * Decide whether to use canvas rendering for a given dataset.
 * @param {GeoJSON.FeatureCollection} geojson
 * @returns {boolean}
 */
export function shouldUseCanvas(geojson) {
  return geojson.features.length > CLUSTER_THRESHOLD;
}

/**
 * Colour a circle on a raw CanvasRenderingContext2D.
 * Called inside a rAF loop for bulk rendering.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} x
 * @param {number} y
 * @param {number} r        radius in px
 * @param {string} colour   hex or rgba
 */
export function drawCircle(ctx, x, y, r, colour) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fillStyle   = colour;
  ctx.globalAlpha = 0.85;
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = 'rgba(255,255,255,0.4)';
  ctx.lineWidth   = 1;
  ctx.stroke();
}

/**
 * Batch-render all features onto a canvas in a single rAF frame.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {number}                  w   canvas width
 * @param {number}                  h   canvas height
 * @param {GeoJSON.Feature[]}       features
 * @param {(lat:number,lon:number)=>{x:number,y:number}} project
 * @param {(props:object)=>string}  colourFn
 * @param {number}                  radius
 */
export function batchRender(ctx, w, h, features, project, colourFn, radius = 5) {
  ctx.clearRect(0, 0, w, h);
  for (const f of features) {
    const [lon, lat] = f.geometry.coordinates;
    const { x, y }  = project(lat, lon);
    if (x < -radius || x > w + radius || y < -radius || y > h + radius) continue;
    drawCircle(ctx, x, y, radius, colourFn(f.properties));
  }
}

/**
 * Smooth debounce using requestAnimationFrame.
 * Replaces setTimeout-based debounce for resize/scroll events.
 * @param {Function} fn
 * @returns {Function}
 */
export function rafDebounce(fn) {
  let frame;
  return (...args) => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => fn(...args));
  };
}

/**
 * Linear interpolate between two numeric values — used for smooth
 * slider animation even when frames arrive at irregular intervals.
 * @param {number} a
 * @param {number} b
 * @param {number} t  0–1
 * @returns {number}
 */
export function lerp(a, b, t) {
  return a + (b - a) * t;
}
