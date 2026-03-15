/**
 * Playwright E2E — weather map interaction.
 * Requires backend running on http://localhost:8000
 * Run: npx playwright test
 */

import { test, expect } from '@playwright/test';

test.describe('Map loads', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the /api/observations endpoint so tests run offline
    await page.route('**/api/observations**', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              geometry: { type: 'Point', coordinates: [24.94, 60.17] },
              properties: {
                station_name: 'Helsinki Kaisaniemi',
                temperature_c: 5.2,
                wind_speed_ms: 3.1,
                precipitation_mmh: 0.0,
                humidity_pct: 85.0,
                pressure_hpa: 1013.2,
                observed_at: '2024-01-15T11:00:00+00:00',
                extra: {},
              },
            },
          ],
          meta: { station_count: 1, fetched_at: new Date().toISOString(), from_cache: false },
        }),
      })
    );
    await page.route('**/api/timeseries**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );
    await page.goto('/');
  });

  test('Leaflet map container is rendered', async ({ page }) => {
    await expect(page.locator('#map')).toBeVisible();
    await expect(page.locator('.leaflet-container')).toBeVisible();
  });

  test('topbar shows station count after load', async ({ page }) => {
    await expect(page.locator('#station-count')).toContainText('asemaa', { timeout: 5000 });
  });

  test('temperature range is shown in topbar', async ({ page }) => {
    await expect(page.locator('#temp-min')).toContainText('°C', { timeout: 5000 });
    await expect(page.locator('#temp-max')).toContainText('°C', { timeout: 5000 });
  });

  test('station marker is visible on map', async ({ page }) => {
    await expect(page.locator('.leaflet-interactive').first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe('UI controls', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/**', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ type: 'FeatureCollection', features: [], meta: { station_count: 0 } }),
      })
    );
    await page.goto('/');
  });

  test('side panel collapses on toggle', async ({ page }) => {
    await page.locator('#panel-toggle').click();
    await expect(page.locator('#side-panel')).toHaveClass(/collapsed/);
  });

  test('side panel expands again', async ({ page }) => {
    await page.locator('#panel-toggle').click();
    await page.locator('#panel-toggle').click();
    await expect(page.locator('#side-panel')).not.toHaveClass(/collapsed/);
  });

  test('hours slider updates label', async ({ page }) => {
    await page.locator('#hours-slider').fill('6');
    await page.locator('#hours-slider').dispatchEvent('input');
    await expect(page.locator('#hours-val')).toContainText('6 h');
  });

  test('fetch button triggers API call', async ({ page }) => {
    let called = false;
    await page.route('**/api/observations**', route => {
      called = true;
      route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ type: 'FeatureCollection', features: [], meta: {} }) });
    });
    await page.locator('#fetch-btn').click();
    await page.waitForTimeout(500);
    expect(called).toBe(true);
  });
});
