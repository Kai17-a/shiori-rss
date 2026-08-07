import { expect, test } from "@playwright/test";

test("opens the RSS feed manager as the app home", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/rss$/);

  await page.goto("/rss");
  await expect(page.getByRole("heading", { name: "RSS feeds" })).toBeVisible();
  await expect(page.getByText("Custom news sites")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Bookmarks" })).toHaveCount(0);
});

test("shows LLM connection settings without restoring custom news", async ({ page }) => {
  await page.goto("/settings");

  await expect(page.getByText("LLM connection", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Provider")).toBeVisible();
  await expect(page.getByText("Custom news sites")).toHaveCount(0);
});
