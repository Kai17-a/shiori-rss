import { expect, test } from "@playwright/test";

test("opens the RSS feed manager as the app home", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/rss$/);

  await page.goto("/rss");
  await expect(page.getByRole("heading", { name: "RSS feeds" })).toBeVisible();
  await expect(page.getByText("Custom news sites")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Bookmarks" })).toHaveCount(0);
});
