import { test, expect } from '@playwright/test';

// Regression test for debug console.warn statements that used to fire on
// every app bootstrap (see AuthService.runInitializeUserRequest). They were
// leftover debugging output, unintentionally bumped from console.log to
// console.warn by an unrelated lint-cleanup commit.
test('login page bootstrap does not emit AuthService debug warnings', async ({ page }) => {
  const warnings: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'warning' && msg.text().includes('[AuthService]')) {
      warnings.push(msg.text());
    }
  });

  await page.goto('/auth/login');
  await expect(page.locator('form')).toBeVisible();

  expect(warnings).toEqual([]);
});
