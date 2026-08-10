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
  await page.route("**/ai/chat/stream", async (route) => {
    await route.fulfill({
      contentType: "application/x-ndjson",
      body: [
        JSON.stringify({ type: "delta", delta: "## Highlights\n\n- **Agentic systems** " }),
        JSON.stringify({ type: "delta", delta: "were the main theme. [S1]\n- Read the `saved summary` for details." }),
        JSON.stringify({ type: "sources", sources: [{
          reference: "S1",
          source_type: "rss",
          article_id: 12,
          source_id: 3,
          source_title: "Tech Feed",
          title: "Agentic systems",
          summary: "A saved summary",
          url: "https://example.com/agentic-systems",
          published: "2026-08-09T08:00:00Z",
          created_at: "2026-08-09T08:00:00Z",
        }] }),
        JSON.stringify({ type: "done" }),
      ].join("\n") + "\n",
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
  await expect(page.getByRole("heading", { name: "RSS feeds", level: 2 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add feed" })).toBeVisible();
});

test("shows loading while updating a feed notification", async ({ page }) => {
  let releaseUpdate = () => {};
  const updatePending = new Promise<void>((resolve) => {
    releaseUpdate = resolve;
  });
  const feed = {
    id: 1,
    title: "Example feed",
    url: "https://example.com/feed.xml",
    description: "Example description",
    notify_webhook_enabled: true,
    webhook_ids: [],
    created_at: "2026-08-08T00:00:00Z",
    updated_at: "2026-08-08T00:00:00Z",
  };

  await page.route(/\/api\/rss-feeds\?.*$/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [feed],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
      }),
    });
  });
  await page.route("**/api/settings/webhooks", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ items: [] }),
    });
  });
  await page.route("**/api/rss-feeds/1", async (route) => {
    await updatePending;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ ...feed, notify_webhook_enabled: false }),
    });
  });

  await page.goto("/feeds");
  const button = page.getByRole("button", { name: "Mute feed delivery" });
  await button.click();

  await expect(button).toBeDisabled();
  await expect(button.locator(".animate-spin")).toBeVisible();

  releaseUpdate();
  await expect(page.getByRole("button", { name: "Enable feed delivery" })).toBeEnabled();
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
  await expect(page.getByRole("heading", { name: "RSS feeds", level: 2 })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Last 24 hours" })).toHaveCount(0);
});

test("shows the LLM connection settings used by custom RSS", async ({ page }) => {
  await page.route(/\/api\/settings\/llm\/?$/, async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "LLM settings are not configured" }),
    });
  });
  await page.goto("/settings?tab=llm");

  await expect(page.getByText("Tune your feed workflow.")).toHaveCount(0);
  await expect(page.getByText("LLM connection", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Provider")).toBeVisible();
  await expect(page.getByText("Article analysis batch", { exact: true })).toBeVisible();
  await expect(page.getByText("Token usage and content sharing", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Analyze saved articles")).not.toBeChecked();
  await expect(page.getByLabel("Analyze saved articles")).toBeDisabled();
});

test("opens and displays saved AI article analysis data", async ({ page }) => {
  await page.route(/\/api\/ai\/article-analyses/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: 1,
            source_type: "rss",
            article_id: 12,
            source_id: 3,
            source_title: "Tech Feed",
            article_title: "OpenAI platform update",
            article_url: "https://example.com/openai-update",
            article_published: "2026-08-09T08:00:00Z",
            model: "example-model",
            prompt_version: "v1",
            ai_summary: "The platform added new agent capabilities.",
            key_points: ["New agent APIs were announced."],
            topics: ["AI"],
            keywords: ["OpenAI"],
            entities: ["OpenAI"],
            input_tokens: 120,
            output_tokens: 40,
            status: "completed",
            error_message: null,
            attempt_count: 1,
            analyzed_at: "2026-08-10T01:00:00Z",
            updated_at: "2026-08-10T01:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
      }),
    });
  });

  await page.goto("/settings?tab=llm");
  await page.getByRole("link", { name: "View analysis data" }).click();

  await expect(page).toHaveURL(/\/ai-data$/);
  await expect(page.getByRole("heading", { name: "Analyzed articles" })).toBeVisible();
  await expect(page.getByRole("link", { name: "OpenAI platform update" })).toBeVisible();
  await expect(page.getByText("The platform added new agent capabilities.")).toBeVisible();
  await expect(page.getByText("Tokens: 120 in / 40 out")).toBeVisible();
});

test("runs article analysis manually with a loading state", async ({ page }) => {
  let executionRequests = 0;
  let releaseAnalysis = () => {};
  const analysisPending = new Promise<void>((resolve) => {
    releaseAnalysis = resolve;
  });
  await page.route(/\/api\/settings\/llm\/?$/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        provider: "openai",
        base_url: "https://llm.example.com/v1",
        api_key_configured: true,
        model: "example-model",
      }),
    });
  });
  await page.route(/\/api\/settings\/ai-article-analysis\/?$/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        enabled: false,
        max_articles_per_run: 20,
        daily_token_limit: 50000,
        lookback_days: 30,
      }),
    });
  });
  await page.route(/\/api\/settings\/ai-article-analysis\/execute\/?$/, async (route) => {
    executionRequests += 1;
    await analysisPending;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        processed: 2,
        succeeded: 2,
        failed: 0,
        skipped_current: 3,
        stopped_by_token_limit: false,
      }),
    });
  });

  await page.goto("/settings?tab=llm");
  const runButton = page.getByRole("button", { name: "Run analysis now" });
  await expect(runButton).toBeEnabled();
  await runButton.evaluate((button: HTMLButtonElement) => {
    button.click();
    button.click();
  });

  await expect(runButton).toBeDisabled();
  await expect(runButton.locator(".animate-spin")).toBeVisible();
  expect(executionRequests).toBe(1);
  releaseAnalysis();
  await expect(page.getByText("Article analysis completed.", { exact: true })).toBeVisible();
  await expect(runButton).toBeEnabled();
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
