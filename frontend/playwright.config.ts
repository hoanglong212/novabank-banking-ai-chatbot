import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e', fullyParallel: false, workers: 1, retries: 0,
  timeout: 60_000, expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:8092', viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure', screenshot: 'only-on-failure', headless: true },
  webServer: { command: 'node scripts/start-e2e-server.mjs', url: 'http://127.0.0.1:8092/api/health',
    reuseExistingServer: false, timeout: 60_000 },
});
