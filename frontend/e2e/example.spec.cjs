const { test, expect } = require('@playwright/test');
const path = require('path');

/**
 * Example Playwright E2E test for FlatBOMGenerator plugin
 * 
 * This test verifies Playwright can access and login to InvenTree SPA.
 * 
 * Credentials are loaded from config/servers.json (dev server section).
 */

const configPath = path.resolve(__dirname, '../../../../config/servers.json');
let username = 'admin';
let password = 'admin';
let baseURL = 'http://localhost:8001';

try {
  const config = require(configPath);
  if (config?.servers?.dev) {
    username = config.servers.dev.username || 'admin';
    password = config.servers.dev.password || 'admin';
    baseURL = config.servers.dev.url || 'http://localhost:8001';
  }
} catch (error) {
  console.log('Using default credentials (config/servers.json not found or error reading)');
}

test.describe('InvenTree Login', () => {
  test('can navigate to login page', async ({ page }) => {
    // Navigate to InvenTree web interface
    await page.goto('/web');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Check if we're redirected to login
    const currentUrl = page.url();
    expect(currentUrl).toMatch(/\/(login|web)/);
  });

  test('login form is accessible', async ({ page }) => {
    // Navigate to login page
    await page.goto('/web');
    await page.waitForLoadState('networkidle');
    
    // Check for login form elements (try multiple possible selectors)
    const usernameInput = page.locator('input[name="username"], input[type="text"], #username').first();
    const passwordInput = page.locator('input[name="password"], input[type="password"], #password').first();
    const submitButton = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")').first();
    
    // Wait a moment for SPA to render
    await page.waitForTimeout(2000);
    
    // Log what we found for debugging
    console.log('Username input visible:', await usernameInput.isVisible().catch(() => false));
    console.log('Password input visible:', await passwordInput.isVisible().catch(() => false));
    console.log('Submit button visible:', await submitButton.isVisible().catch(() => false));
    
    // At least one of these should be visible
    const hasLoginForm = await usernameInput.isVisible().catch(() => false) || 
                         await passwordInput.isVisible().catch(() => false);
    
    expect(hasLoginForm).toBeTruthy();
  });

  test('can login with dev credentials and navigate to parts', async ({ page }) => {
    // Increase test timeout for login attempt
    test.setTimeout(60000);
    
    // Navigate to login page
    await page.goto('/web');
    await page.waitForLoadState('networkidle');
    
    // Wait for SPA to render
    await page.waitForTimeout(3000);
    
    // Try multiple selectors for username input
    const usernameSelectors = [
      'input[name="username"]',
      'input[placeholder*="Username" i]',
      'input[placeholder*="username" i]',
      'input[type="text"]',
      '#username',
      'input:not([type="password"])',
    ];
    
    let usernameInput = null;
    for (const selector of usernameSelectors) {
      const locator = page.locator(selector).first();
      if (await locator.isVisible().catch(() => false)) {
        usernameInput = locator;
        console.log('Found username input with selector:', selector);
        break;
      }
    }
    
    // Find password input
    let passwordInput = null;
    const passwordSelectors = [
      'input[type="password"]',
      'input[name="password"]',
      'input[placeholder*="Password" i]',
    ];
    
    for (const selector of passwordSelectors) {
      const locator = page.locator(selector).first();
      if (await locator.isVisible().catch(() => false)) {
        passwordInput = locator;
        console.log('Found password input with selector:', selector);
        break;
      }
    }
    
    expect(usernameInput, 'username input should be found').toBeTruthy();
    expect(passwordInput, 'password input should be found').toBeTruthy();
    
    // Fill both fields with dev credentials
    await usernameInput.fill(username);
    await passwordInput.fill(password);
    
    // Tab between fields to ensure focus events fire
    await usernameInput.press('Tab');
    await passwordInput.fill(password);
    
    // Find submit button and wait for it to be enabled
    const submitButton = page.locator('button[type="submit"]').first();
    await submitButton.waitFor({ state: 'visible', timeout: 10000 });
    
    // Wait for button to be enabled (form validation complete)
    await page.waitForFunction(() => {
      const btn = document.querySelector('button[type="submit"]');
      return btn && !btn.disabled && !btn.getAttribute('data-disabled');
    }, { timeout: 10000 });
    
    // Click submit
    await submitButton.click();
    
    // Wait for navigation after login
    await page.waitForTimeout(5000);
    
    // Check if we're now on a logged-in page
    const currentUrl = page.url();
    console.log('After login URL:', currentUrl);
    
    // Login should succeed and no longer be on login page
    expect(currentUrl).not.toContain('/login');
    
    // Navigate to parts page after successful login
    await page.goto('/part/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    const partsUrl = page.url();
    console.log('Parts page URL:', partsUrl);
    expect(partsUrl).toContain('/part');
  });
});
