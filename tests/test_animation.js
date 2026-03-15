/**
 * test_animation.js — Vitest tests for animation.js (100% coverage).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TimeAnimator, formatTimestamp } from '../frontend/src/animation.js';

// ── Helpers ──────────────────────────────────────────────────

function makeFrames(n) {
  return Array.from({ length: n }, (_, i) => ({
    timestamp: `2024-01-15T${String(i).padStart(2, '0')}:00:00Z`,
    geojson:   { type: 'FeatureCollection', features: [] },
  }));
}

// ── TimeAnimator ──────────────────────────────────────────────

describe('TimeAnimator — load', () => {
  it('loads frames and dispatches last frame', () => {
    const cb = vi.fn();
    const a = new TimeAnimator(cb);
    const frames = makeFrames(3);
    a.load(frames);
    expect(cb).toHaveBeenCalledOnce();
    expect(cb.mock.calls[0][1]).toBe(2);     // last index
    expect(cb.mock.calls[0][2]).toBe(3);     // total
  });

  it('does not dispatch for empty frames', () => {
    const cb = vi.fn();
    const a = new TimeAnimator(cb);
    a.load([]);
    expect(cb).not.toHaveBeenCalled();
  });

  it('resets playing state', () => {
    const a = new TimeAnimator(vi.fn());
    a.load(makeFrames(3));
    expect(a.isPlaying).toBe(false);
  });

  it('exposes frameCount', () => {
    const a = new TimeAnimator(vi.fn());
    a.load(makeFrames(5));
    expect(a.frameCount).toBe(5);
  });
});

describe('TimeAnimator — seekTo', () => {
  it('seeks to a valid index', () => {
    const cb = vi.fn();
    const a = new TimeAnimator(cb);
    a.load(makeFrames(4));
    cb.mockClear();
    a.seekTo(1);
    expect(a.currentIndex).toBe(1);
    expect(cb).toHaveBeenCalledOnce();
  });

  it('ignores out-of-range index', () => {
    const cb = vi.fn();
    const a = new TimeAnimator(cb);
    a.load(makeFrames(3));
    cb.mockClear();
    a.seekTo(99);
    expect(cb).not.toHaveBeenCalled();
    a.seekTo(-1);
    expect(cb).not.toHaveBeenCalled();
  });
});

describe('TimeAnimator — play / pause / stop', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('advances frames during playback', () => {
    const cb = vi.fn();
    const a = new TimeAnimator(cb);
    a.load(makeFrames(4));
    a.seekTo(0);
    cb.mockClear();
    a.play();
    expect(a.isPlaying).toBe(true);
    vi.advanceTimersByTime(500);
    expect(cb).toHaveBeenCalled();
    expect(a.currentIndex).toBe(1);
  });

  it('play is idempotent when already playing', () => {
    const a = new TimeAnimator(vi.fn());
    a.load(makeFrames(4));
    a.play();
    const first = a.isPlaying;
    a.play();
    expect(a.isPlaying).toBe(first);
  });

  it('pause stops timer and preserves position', () => {
    const cb = vi.fn();
    const a = new TimeAnimator(cb);
    a.load(makeFrames(4));
    a.seekTo(1);
    a.play();
    a.pause();
    cb.mockClear();
    vi.advanceTimersByTime(2000);
    expect(cb).not.toHaveBeenCalled();
    expect(a.isPlaying).toBe(false);
    expect(a.currentIndex).toBe(1);
  });

  it('stop resets to last frame', () => {
    const cb = vi.fn();
    const a = new TimeAnimator(cb);
    a.load(makeFrames(4));
    a.seekTo(0);
    a.play();
    a.stop();
    expect(a.isPlaying).toBe(false);
    expect(a.currentIndex).toBe(3);
  });

  it('does not play when no frames loaded', () => {
    const a = new TimeAnimator(vi.fn());
    a.play();
    expect(a.isPlaying).toBe(false);
  });

  it('stops playing at last frame (no loop)', () => {
    const cb = vi.fn();
    const a = new TimeAnimator(cb);
    const frames = makeFrames(3);
    a.load(frames);
    a.seekTo(0);
    a.play();
    vi.advanceTimersByTime(500 * 3);
    expect(a.isPlaying).toBe(false);
  });
});

describe('TimeAnimator — setSpeed', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('changes frame interval', () => {
    const cb = vi.fn();
    const a = new TimeAnimator(cb);
    a.load(makeFrames(4));
    a.seekTo(0);
    a.setSpeed(200);
    cb.mockClear();
    a.play();
    vi.advanceTimersByTime(200);
    expect(cb).toHaveBeenCalled();
  });

  it('clamps minimum speed to 50 ms', () => {
    const a = new TimeAnimator(vi.fn());
    a.setSpeed(10);
    expect(a._speed).toBe(50);
  });

  it('restarts timer when playing', () => {
    const a = new TimeAnimator(vi.fn());
    a.load(makeFrames(4));
    a.play();
    expect(() => a.setSpeed(300)).not.toThrow();
  });
});

describe('TimeAnimator — currentFrame', () => {
  it('returns current frame', () => {
    const a = new TimeAnimator(vi.fn());
    const frames = makeFrames(3);
    a.load(frames);
    a.seekTo(1);
    expect(a.currentFrame).toBe(frames[1]);
  });

  it('returns null when no frames', () => {
    const a = new TimeAnimator(vi.fn());
    expect(a.currentFrame).toBeNull();
  });
});

// ── formatTimestamp ───────────────────────────────────────────

describe('formatTimestamp', () => {
  it('formats ISO timestamp', () => {
    const result = formatTimestamp('2024-01-15T12:30:00Z');
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });

  it('handles invalid string gracefully', () => {
    const result = formatTimestamp('not-a-date');
    expect(typeof result).toBe('string');
  });
});
