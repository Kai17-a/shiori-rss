import { expect, test } from "@playwright/test";

test("opens the RSS feed manager as the app home", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/feeds$/);

  await page.goto("/feeds");
  await expect(page.getByRole("heading", { name: "Your feeds" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Follow the web on your terms." })).toBeVisible();
  await expect(page.getByText("Custom news sites")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Bookmarks" })).toHaveCount(0);
});

test("does not expose the former RSS screen route", async ({ page }) => {
  await page.goto("/rss");
  await expect(page).toHaveURL(/\/rss$/);
  await expect(page.getByText("404")).toBeVisible();
});

test("shows LLM connection settings without restoring custom news", async ({ page }) => {
  await page.goto("/settings");

  await expect(page.getByText("LLM connection", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Provider")).toBeVisible();
  await expect(page.getByText("Custom news sites")).toHaveCount(0);
});
