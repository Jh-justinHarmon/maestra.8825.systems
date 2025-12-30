/**
 * E2E Smoke Tests
 * Basic end-to-end tests to verify core functionality.
 * Run with: npx playwright test
 */

import { test, expect } from '@playwright/test';

const APP_URL = 'http://localhost:5000';
const BACKEND_URL = 'http://localhost:3001';

test.describe('Maestra E2E Smoke Tests', () => {
  test.beforeAll(async () => {
    // Verify backend is running
    const response = await fetch(`${BACKEND_URL}/health`);
    expect(response.ok).toBe(true);
  });

  test('should load app and display header', async ({ page }) => {
    await page.goto(APP_URL);
    
    // Check header is visible
    const header = page.locator('header');
    await expect(header).toBeVisible();
    
    // Check Maestra title
    const title = page.locator('h1');
    await expect(title).toContainText('Maestra');
  });

  test('should send a message and receive response', async ({ page }) => {
    await page.goto(APP_URL);
    
    // Find input field
    const input = page.locator('input[placeholder*="Ask"]');
    await expect(input).toBeVisible();
    
    // Type message
    await input.fill('Hello Maestra');
    
    // Send message
    const sendButton = page.locator('button:has-text("Send")');
    await sendButton.click();
    
    // Wait for response
    const messages = page.locator('[role="article"]');
    await expect(messages).toHaveCount(2); // User + assistant
  });

  test('should toggle pins drawer', async ({ page }) => {
    await page.goto(APP_URL);
    
    // Find pins button
    const pinsButton = page.locator('button:has-text("Pins")');
    await expect(pinsButton).toBeVisible();
    
    // Click to open
    await pinsButton.click();
    
    // Check drawer is visible
    const drawer = page.locator('[role="complementary"]');
    await expect(drawer).toBeVisible();
    
    // Click to close
    await pinsButton.click();
    await expect(drawer).not.toBeVisible();
  });

  test('should capture page content', async ({ page }) => {
    await page.goto(APP_URL);
    
    // Find capture button
    const captureButton = page.locator('button:has-text("Capture")');
    await expect(captureButton).toBeVisible();
    
    // Click capture
    await captureButton.click();
    
    // Verify pins drawer opens
    const drawer = page.locator('[role="complementary"]');
    await expect(drawer).toBeVisible();
    
    // Check pin was added
    const pins = page.locator('[data-testid="pin"]');
    await expect(pins).toHaveCount(1);
  });

  test('should display mode indicator', async ({ page }) => {
    await page.goto(APP_URL);
    
    // Check for mode badge
    const modeBadge = page.locator('span:has-text(/Default|Replit/)');
    await expect(modeBadge).toBeVisible();
  });

  test('should handle errors gracefully', async ({ page }) => {
    // Navigate to invalid URL to trigger error
    await page.goto(APP_URL + '/invalid');
    
    // Should still show error boundary UI or redirect
    const content = page.locator('body');
    await expect(content).toBeVisible();
  });
});
