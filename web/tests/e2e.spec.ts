import { test, expect } from "@playwright/test";

test("homepage loads and displays correct title", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/JobHunter/);
});

test("dashboard links are visible", async ({ page }) => {
  await page.goto("/");

  // Since dashboard is protected, we just check if the links exist on the homepage navbar
  const logo = page.getByRole("link", { name: "JH Logo JobHunter" });
  await expect(logo).toBeVisible();

  const loginBtn = page.getByRole("link", { name: "Log in" });
  await expect(loginBtn).toBeVisible();
});
