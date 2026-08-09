import { expect, test } from "@playwright/test";

test("opens the rolling 24-hour news summary as the app home", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Last 24 hours" })).toBeVisible();
  await expect(page.getByText(/^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), /)).toBeVisible();
  await expect(page.getByText("Recent articles", { exact: true })).toBeVisible();
  await expect(page.getByText("Follow the web on your terms.")).toHaveCount(0);
  await expect(page.getByText("Your signal, uninterrupted")).toHaveCount(0);
  await expect(page.getByText("Automation", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Home", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Bookmarks" })).toHaveCount(0);
});

test("opens the Ask AI chat modal from the floating launcher", async ({ page }) => {
  await page.route("**/ai/chat", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        answer: [
          "## Highlights",
          "",
          "- **Agentic systems** were the main theme. [S1]",
          "- Read the `saved summary` for details.",
        ].join("\n"),
        sources: [{
          source_type: "rss",
          article_id: 12,
          source_id: 3,
          source_title: "Tech Feed",
          title: "Agentic systems",
          summary: "A saved summary",
          url: "https://example.com/agentic-systems",
          published: "2026-08-09T08:00:00Z",
          created_at: "2026-08-09T08:00:00Z",
        }],
      }),
    });
  });
  await page.goto("/");

  await page.getByRole("button", { name: "Open Ask AI chat" }).click();
  await expect(page.getByRole("dialog", { name: "Ask AI" })).toBeVisible();
  await expect(page.getByText("Ask about your feed library")).toBeVisible();
  await page.getByLabel("Ask AI message").fill("Summarize agent news");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("heading", { name: "Highlights" })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: "Agentic systems" })).toBeVisible();
  await expect(page.getByText("saved summary", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /Agentic systems/ })).toHaveAttribute(
    "href",
    "https://example.com/agentic-systems",
  );

  await page.getByRole("button", { name: "Close Ask AI" }).click();
  await expect(page.getByRole("dialog", { name: "Ask AI" })).toBeHidden();
});

test("lists custom RSS sources in the sidebar", async ({ page }) => {
  await page.route("**/news-sites?per_page=100", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [{
          id: 7,
          title: "LLM Daily",
          url: "https://example.com/news",
          description: null,
          notify_webhook_enabled: true,
          webhook_ids: [],
          created_at: "2026-08-08T00:00:00Z",
          updated_at: "2026-08-08T00:00:00Z",
        }],
        total: 1,
        page: 1,
        per_page: 100,
        total_pages: 1,
      }),
    });
  });

  await page.goto("/");

  await page.getByRole("button", { name: "Custom RSS", exact: true }).click();
  await expect(page).toHaveURL(/\/custom-feeds$/);
  await expect(page.getByRole("link", { name: "All custom RSS" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "LLM Daily" })).toHaveAttribute(
    "href",
    "/custom-feeds/7",
  );
  await page.getByRole("button", { name: "Custom RSS", exact: true }).click();
  await expect(page.getByRole("link", { name: "LLM Daily" })).toBeHidden();

  await page.goto("/custom-feeds/7");
  await expect(page.getByRole("link", { name: "LLM Daily" })).toBeVisible();
  await page.getByRole("button", { name: "Custom RSS", exact: true }).click();
  await expect(page).toHaveURL(/\/custom-feeds$/);
  await expect(page.getByRole("link", { name: "LLM Daily" })).toBeHidden();
});

test("shows the RSS feed library at its root route", async ({ page }) => {
  await page.goto("/feeds");
  await expect(page).toHaveURL(/\/feeds$/);
  await expect(page.getByRole("heading", { name: "Your feeds" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add feed" })).toBeVisible();
});

test("shows the custom RSS library at its root route", async ({ page }) => {
  await page.goto("/custom-feeds");
  await expect(page).toHaveURL(/\/custom-feeds$/);
  await expect(page.getByRole("heading", { name: "Custom RSS", level: 2 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add custom RSS" })).toBeVisible();
});

test("does not expose the former RSS screen route", async ({ page }) => {
  await page.goto("/rss");
  await expect(page).toHaveURL(/\/rss$/);
  await expect(page.getByRole("heading", { name: "Your feeds" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Last 24 hours" })).toHaveCount(0);
});

test("shows the LLM connection settings used by custom RSS", async ({ page }) => {
  await page.goto("/settings?tab=llm");

  await expect(page.getByText("Tune your feed workflow.")).toHaveCount(0);
  await expect(page.getByText("LLM connection", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Provider")).toBeVisible();
  await expect(page.getByText("Article analysis batch", { exact: true })).toBeVisible();
  await expect(page.getByText("Token usage and content sharing", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Analyze saved articles")).not.toBeChecked();
  await expect(page.getByLabel("Analyze saved articles")).toBeDisabled();
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
