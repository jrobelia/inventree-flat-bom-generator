const { defineConfig, devices } = require('@playwright/test');

/**
 * Playwright configuration for FlatBOMGenerator plugin E2E tests
 * 
 * This configuration is set up to test the plugin frontend against
 * the InvenTree dev server running in the devcontainer.
 */
module.exports = defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  globalSetup: './e2e/global-setup.cjs',
  reporter: [
    ['list'],
    ['html', { open: 'always' }]
  ],

  use: {
    baseURL: 'http://localhost:8001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Firefox temporarily disabled due to timeout issues
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
});
