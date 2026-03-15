import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    coverage: {
      provider:  'v8',
      include:   ['frontend/src/**/*.js'],
      exclude:   ['frontend/src/app.js', 'frontend/src/map.js'],  // leaflet-dependent
      thresholds: { lines: 100, functions: 100, branches: 100, statements: 100 },
      reporter:  ['text', 'html'],
    },
  },
});
