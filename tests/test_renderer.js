/**
 * test_renderer.js — Vitest tests for renderer.js (100% coverage).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  shouldUseCanvas,
  drawCircle,
  batchRender,
  rafDebounce,
  lerp,
} from '../frontend/src/renderer.js';

// ── shouldUseCanvas ───────────────────────────────────────────

describe('shouldUseCanvas', () => {
  const makeGeoJSON = n => ({
    type: 'FeatureCollection',
    features: Array.from({ length: n }, (_, i) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [25 + i * 0.01, 60] },
      properties: { temperature_c: i },
    })),
  });

  it('returns false for small datasets', () => {
    expect(shouldUseCanvas(makeGeoJSON(50))).toBe(false);
    expect(shouldUseCanvas(makeGeoJSON(300))).toBe(false);
  });

  it('returns true above threshold', () => {
    expect(shouldUseCanvas(makeGeoJSON(301))).toBe(true);
    expect(shouldUseCanvas(makeGeoJSON(1000))).toBe(true);
  });
});

// ── drawCircle ────────────────────────────────────────────────

describe('drawCircle', () => {
  it('calls ctx methods without throwing', () => {
    const ctx = {
      beginPath: vi.fn(), arc: vi.fn(), fill: vi.fn(),
      stroke: vi.fn(), fillStyle: '', globalAlpha: 1,
      strokeStyle: '', lineWidth: 0,
    };
    expect(() => drawCircle(ctx, 100, 100, 6, '#FF0000')).not.toThrow();
    expect(ctx.beginPath).toHaveBeenCalled();
    expect(ctx.arc).toHaveBeenCalledWith(100, 100, 6, 0, Math.PI * 2);
    expect(ctx.fill).toHaveBeenCalled();
    expect(ctx.stroke).toHaveBeenCalled();
  });

  it('sets fillStyle to the provided colour', () => {
    const ctx = {
      beginPath: vi.fn(), arc: vi.fn(), fill: vi.fn(),
      stroke: vi.fn(), fillStyle: '', globalAlpha: 1,
      strokeStyle: '', lineWidth: 0,
    };
    drawCircle(ctx, 0, 0, 5, '#00FF00');
    expect(ctx.fillStyle).toBe('#00FF00');
  });

  it('resets globalAlpha to 1 after drawing', () => {
    const ctx = {
      beginPath: vi.fn(), arc: vi.fn(), fill: vi.fn(),
      stroke: vi.fn(), fillStyle: '', globalAlpha: 1,
      strokeStyle: '', lineWidth: 0,
    };
    drawCircle(ctx, 0, 0, 5, '#blue');
    expect(ctx.globalAlpha).toBe(1);
  });
});

// ── batchRender ───────────────────────────────────────────────

describe('batchRender', () => {
  function makeCtx() {
    return {
      clearRect: vi.fn(), beginPath: vi.fn(), arc: vi.fn(),
      fill: vi.fn(), stroke: vi.fn(),
      fillStyle: '', globalAlpha: 1, strokeStyle: '', lineWidth: 0,
    };
  }

  const features = [
    { geometry: { coordinates: [25.0, 60.0] }, properties: { temperature_c: 5 } },
    { geometry: { coordinates: [25.1, 60.1] }, properties: { temperature_c: 10 } },
    { geometry: { coordinates: [99.0, 99.0] }, properties: { temperature_c: 0 } }, // out of bounds
  ];

  const project = (lat, lon) => ({
    x: (lon - 24) * 1000,
    y: (lat - 59) * 1000,
  });

  it('calls clearRect once', () => {
    const ctx = makeCtx();
    batchRender(ctx, 800, 600, features, project, p => '#ff0', 5);
    expect(ctx.clearRect).toHaveBeenCalledWith(0, 0, 800, 600);
  });

  it('skips out-of-bounds features', () => {
    const ctx = makeCtx();
    batchRender(ctx, 800, 600, features, project, p => '#ff0', 5);
    // Only 2 of 3 features are in bounds
    expect(ctx.arc).toHaveBeenCalledTimes(2);
  });

  it('handles empty features array', () => {
    const ctx = makeCtx();
    expect(() => batchRender(ctx, 800, 600, [], project, p => '#ff0')).not.toThrow();
    expect(ctx.arc).not.toHaveBeenCalled();
  });
});

// ── rafDebounce ───────────────────────────────────────────────

describe('rafDebounce', () => {
  it('calls fn via requestAnimationFrame', () => {
    vi.stubGlobal('requestAnimationFrame', cb => { cb(); return 1; });
    vi.stubGlobal('cancelAnimationFrame', vi.fn());

    const fn = vi.fn();
    const debounced = rafDebounce(fn);
    debounced('arg1');
    expect(fn).toHaveBeenCalledWith('arg1');

    vi.unstubAllGlobals();
  });

  it('cancels previous frame on rapid calls', () => {
    const cancelled = [];
    vi.stubGlobal('cancelAnimationFrame', id => cancelled.push(id));
    vi.stubGlobal('requestAnimationFrame', cb => { cb(); return Math.random(); });

    const fn = vi.fn();
    const debounced = rafDebounce(fn);
    debounced();
    debounced();
    expect(cancelled.length).toBeGreaterThan(0);

    vi.unstubAllGlobals();
  });
});

// ── lerp ─────────────────────────────────────────────────────

describe('lerp', () => {
  it('returns a at t=0', () => expect(lerp(10, 20, 0)).toBe(10));
  it('returns b at t=1', () => expect(lerp(10, 20, 1)).toBe(20));
  it('returns midpoint at t=0.5', () => expect(lerp(0, 100, 0.5)).toBe(50));
  it('works with negative values', () => expect(lerp(-10, 10, 0.5)).toBe(0));
  it('extrapolates beyond [0,1]', () => expect(lerp(0, 10, 2)).toBe(20));
});
