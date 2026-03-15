/**
 * test_layers.js — Vitest unit tests for layers.js (100% coverage).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  tempColour,
  windColour,
  precipColour,
  buildLegend,
  TEMP_BANDS,
  WIND_BANDS,
  PRECIP_BANDS,
} from '../frontend/src/layers.js';

// ── tempColour ────────────────────────────────────────────────

describe('tempColour', () => {
  it('returns grey for NaN', () => expect(tempColour(NaN)).toBe('#9E9E9E'));
  it('returns grey for Infinity', () => expect(tempColour(Infinity)).toBe('#9E9E9E'));
  it('frost (< 0)', () => expect(tempColour(-10)).toBe('#1565C0'));
  it('cold (0 – 10)', () => expect(tempColour(5)).toBe('#42A5F5'));
  it('exactly 0 → cold', () => expect(tempColour(0)).toBe('#42A5F5'));
  it('mild (10 – 20)', () => expect(tempColour(15)).toBe('#66BB6A'));
  it('exactly 10 → mild', () => expect(tempColour(10)).toBe('#66BB6A'));
  it('warm (20 – 28)', () => expect(tempColour(22)).toBe('#FFA726'));
  it('exactly 20 → warm', () => expect(tempColour(20)).toBe('#FFA726'));
  it('hot (≥ 28)', () => expect(tempColour(30)).toBe('#E53935'));
  it('exactly 28 → hot', () => expect(tempColour(28)).toBe('#E53935'));
});

// ── windColour ────────────────────────────────────────────────

describe('windColour', () => {
  it('NaN → grey', () => expect(windColour(NaN)).toBe('#9E9E9E'));
  it('calm (0)', () => expect(windColour(0)).toBe('#B3E5FC'));
  it('light (3)', () => expect(windColour(3)).toBe('#4FC3F7'));
  it('moderate (8)', () => expect(windColour(8)).toBe('#0288D1'));
  it('strong (14)', () => expect(windColour(14)).toBe('#FF8F00'));
  it('storm (21)', () => expect(windColour(21)).toBe('#D32F2F'));
  it('between calm and light (2)', () => expect(windColour(2)).toBe('#B3E5FC'));
});

// ── precipColour ─────────────────────────────────────────────

describe('precipColour', () => {
  it('NaN → grey', () => expect(precipColour(NaN)).toBe('#9E9E9E'));
  it('no rain (0)', () => expect(precipColour(0)).toBe('#E8F5E9'));
  it('light rain (0.01)', () => expect(precipColour(0.01)).toBe('#81C784'));
  it('moderate (1)', () => expect(precipColour(1)).toBe('#1E88E5'));
  it('heavy (5)', () => expect(precipColour(5)).toBe('#7B1FA2'));
  it('between light and moderate (0.5)', () => expect(precipColour(0.5)).toBe('#81C784'));
});

// ── buildLegend ───────────────────────────────────────────────

describe('buildLegend', () => {
  let container;

  beforeEach(() => {
    container = document.createElement('div');
  });

  it('builds temp legend with correct item count', () => {
    buildLegend(container, 'temp');
    // TEMP_BANDS + no-data entry
    expect(container.querySelectorAll('.legend-item').length).toBe(TEMP_BANDS.length + 1);
  });

  it('builds wind legend', () => {
    buildLegend(container, 'wind');
    expect(container.querySelectorAll('.legend-item').length).toBe(WIND_BANDS.length + 1);
  });

  it('builds precip legend', () => {
    buildLegend(container, 'precip');
    expect(container.querySelectorAll('.legend-item').length).toBe(PRECIP_BANDS.length + 1);
  });

  it('clears previous items on rebuild', () => {
    buildLegend(container, 'temp');
    buildLegend(container, 'wind');
    expect(container.querySelectorAll('.legend-item').length).toBe(WIND_BANDS.length + 1);
  });

  it('each item has a coloured dot and label text', () => {
    buildLegend(container, 'temp');
    container.querySelectorAll('.legend-item').forEach(item => {
      expect(item.querySelector('.legend-dot')).not.toBeNull();
      expect(item.textContent.trim().length).toBeGreaterThan(0);
    });
  });

  it('no-data item is always last', () => {
    buildLegend(container, 'temp');
    const items = container.querySelectorAll('.legend-item');
    expect(items[items.length - 1].textContent).toContain('Ei tietoa');
  });
});
