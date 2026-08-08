import { expect, test } from "@playwright/test";

test("opens the RSS feed manager as the app home", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Your feeds" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Follow the web on your terms." })).toBeVisible();
  await expect(page.getByText("Automation", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Custom news sites")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Bookmarks" })).toHaveCount(0);
});

test("does not expose the former feed library route", async ({ page }) => {
  await page.goto("/feeds");
  await expect(page).toHaveURL(/\/feeds$/);
  await expect(page.getByText("404")).toBeVisible();
});

test("does not expose the former RSS screen route", async ({ page }) => {
  await page.goto("/rss");
  await expect(page).toHaveURL(/\/rss$/);
  await expect(page.getByText("404")).toBeVisible();
});

test("shows LLM connection settings without restoring custom news", async ({ page }) => {
  await page.goto("/settings");

  await expect(page.getByText("Theme", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "LLM" }).click();
  await expect(page.getByText("LLM connection", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Provider")).toBeVisible();
  await expect(page.getByText("Custom news sites")).toHaveCount(0);
});

test("groups automation controls under the settings tabs", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/settings?tab=automation");

  const tabList = page.getByRole("tablist");
  await expect(tabList).toBeVisible();
  expect(await tabList.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(false);
  await expect(page.getByRole("tab", { name: "Automation" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByLabel("Scheduled refresh")).toBeVisible();
  await expect(page.getByLabel("Webhook delivery")).toBeVisible();
  await expect(page.getByText("Theme", { exact: true })).toHaveCount(0);
});
