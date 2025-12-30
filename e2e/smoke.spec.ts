/**
 * E2E Smoke Tests
 * Basic end-to-end tests to verify core functionality.
 * Run with: bash scripts/test-setup.sh
 */

import { test, expect } from '@playwright/test';

test.describe('Maestra E2E Smoke Tests', () => {
  test('should load app and display header', async ({ page }) => {
    await page.goto('/');
    
    // Check header is visible
    const header = page.locator('header');
    await expect(header).toBeVisible();
    
    // Check Maestra title
    const title = page.locator('h1');
    await expect(title).toContainText('Maestra');
  });

  test('should send a message and receive response', async ({ page }) => {
    await page.goto('/');
    
    // Find input field using test ID
    const input = page.locator('[data-testid="message-input"]');
    await expect(input).toBeVisible();
    
    // Type message
    await input.fill('Hello Maestra');
    
    // Send message
    const sendButton = page.locator('[data-testid="send-button"]');
    await sendButton.click();
    
    // Wait for response message to appear
    const messagesContainer = page.locator('[data-testid="messages-container"]');
    await expect(messagesContainer).toContainText('Hello Maestra');
  });

  test('should toggle pins drawer', async ({ page }) => {
    await page.goto('/');
    
    // Find pins button
    const pinsButton = page.locator('button:has-text("Pins")');
    await expect(pinsButton).toBeVisible();
    
    // Click to open
    await pinsButton.click();
    
    // Check drawer is visible (look for PinsDrawer component)
    const drawer = page.locator('[data-testid="pins-drawer"]');
    await expect(drawer).toBeVisible();
    
    // Click to close
    await pinsButton.click();
    await expect(drawer).not.toBeVisible();
  });

  test('should toggle capture mode', async ({ page }) => {
    await page.goto('/');
    
    // Find capture mode toggle
    const captureToggle = page.locator('[data-testid="capture-mode-toggle"]');
    await expect(captureToggle).toBeVisible();
    
    // Click to enable capture mode
    await captureToggle.click();
    
    // Check input placeholder changes
    const input = page.locator('[data-testid="message-input"]');
    await expect(input).toHaveAttribute('placeholder', /Describe what you want to capture/);
  });

  test('should display mode indicator', async ({ page }) => {
    await page.goto('/');
    
    // Check for mode badge (should show Default or Replit)
    const modeBadge = page.locator('span:has-text(/Default|Replit/)');
    await expect(modeBadge).toBeVisible();
  });

  test('should display Maestra card', async ({ page }) => {
    await page.goto('/');
    
    // Check for main card component
    const card = page.locator('[data-testid="maestra-card"]');
    await expect(card).toBeVisible();
  });
});
