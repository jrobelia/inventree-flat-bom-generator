import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for FlatBOMGenerator plugin E2E tests
 * 
 * This configuration is set up to test the plugin frontend against
 * the InvenTree dev server running in the devcontainer.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: 'http://localhost:8001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  webServer: {
    // InvenTree dev server should be running before tests
    command: 'echo "Ensure InvenTree server is running on http://localhost:8001"',
    port: 8001,
    timeout: 120 * 1000,
    reuseExistingServer: !process.env.CI,
  },
});
