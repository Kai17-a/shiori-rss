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

test("shows configured feed icons in the recent news list", async ({ page }) => {
  await page.route("**/api/dashboard", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        generated_at: "2026-08-10T01:00:00Z",
        window_started_at: "2026-08-09T01:00:00Z",
        summary: {
          rss_feed_count: 1,
          custom_feed_count: 0,
          recent_article_count: 1,
          pending_notification_count: 0,
        },
        articles: [{
          source_type: "rss",
          source_id: 3,
          source_title: "Tech Feed",
          source_icon_url: "https://cdn.example.com/tech-feed.png",
          url: "https://example.com/article",
          title: "Recent article",
          summary: null,
          published: "2026-08-10T00:00:00Z",
          created_at: "2026-08-10T00:00:00Z",
          webhook_notified: true,
        }],
      }),
    });
  });

  await page.goto("/");

  await expect(page.getByRole("img", { name: "Tech Feed icon" })).toHaveAttribute(
    "src",
    "https://cdn.example.com/tech-feed.png",
  );
});

test("opens the Ask AI chat modal from the floating launcher", async ({ page }) => {
  const requestBodies: Array<Record<string, unknown>> = [];
  let releaseFirstResponse = () => {};
  const firstResponsePending = new Promise<void>((resolve) => {
    releaseFirstResponse = resolve;
  });
  await page.route("**/ai/chat/stream", async (route) => {
    requestBodies.push(route.request().postDataJSON());
    const followUp = requestBodies.length === 2;
    if (!followUp) await firstResponsePending;
    await route.fulfill({
      contentType: "application/x-ndjson",
      body: followUp ? [
        JSON.stringify({ type: "delta", delta: "S1 describes agentic systems in detail. [S1]" }),
        JSON.stringify({ type: "sources", sources: requestBodies[0]?.context_sources || [] }),
        JSON.stringify({ type: "done" }),
      ].join("\n") + "\n" : [
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
  const sendButton = page.getByRole("button", { name: "Send" });
  await expect(sendButton.locator("[data-slot=leadingIcon]")).toHaveClass(
    /i-lucide:loader-circle/,
  );
  await expect(sendButton.locator("[data-slot=leadingIcon]")).toHaveClass(/animate-spin/);
  releaseFirstResponse();
  await expect(page.getByRole("heading", { name: "Highlights" })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: "Agentic systems" })).toBeVisible();
  await expect(page.getByText("saved summary", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /Agentic systems/ })).toHaveAttribute(
    "href",
    "https://example.com/agentic-systems",
  );

  await page.getByLabel("Ask AI message").fill("S1の内容を詳しく教えて");
  await page.getByRole("button", { name: "Send" }).click();
  await expect.poll(() => requestBodies.length).toBe(2);
  expect(requestBodies[1]).toMatchObject({
    message: "S1の内容を詳しく教えて",
    history: [
      { role: "user", content: "Summarize agent news" },
      { role: "assistant", content: expect.stringContaining("Agentic systems") },
    ],
    context_sources: [
      { reference: "S1", article_id: 12, title: "Agentic systems" },
    ],
  });

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

test("scrolls the custom RSS editor when it exceeds the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 640, height: 480 });
  await page.goto("/custom-feeds");
  await page.getByRole("button", { name: "Add custom RSS" }).click();

  const dialog = page.getByRole("dialog");
  const form = dialog.locator("form");
  await expect(dialog).toBeVisible();
  await expect(form).toHaveCSS("overflow-y", "auto");
  expect(await form.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true);

  await page.getByRole("button", { name: "Analyze and register" }).scrollIntoViewIfNeeded();
  await page.getByRole("button", { name: "Analyze and register" }).click();
  await expect(page.getByText("Page URL is required.")).toBeVisible();
});

test("registers custom RSS with manual selectors without AI setup", async ({ page }) => {
  let submitted: Record<string, unknown> | undefined;
  await page.route("**/api/news-sites", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    submitted = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: 21,
        url: "https://example.com/news",
        title: "Example News",
        description: null,
        notify_webhook_enabled: true,
        webhook_ids: [],
        icon_url: null,
        icon_uploaded: false,
        configuration_mode: "manual",
        scrape_config: submitted.scrape_config,
        created_at: "2026-08-12T00:00:00Z",
        updated_at: "2026-08-12T00:00:00Z",
      }),
    });
  });

  await page.goto("/custom-feeds");
  await page.getByRole("button", { name: "Add custom RSS" }).click();
  await page.getByRole("tab", { name: "Manual setup" }).click();
  await page.getByLabel("Site URL").fill("https://example.com/news");
  await page.getByLabel("Title", { exact: true }).fill("Example News");
  await page.getByLabel("Article item selector").fill("article.news-item");
  await page.getByLabel("Title selector").fill("h2 a");
  await page.getByLabel("Link selector").fill("h2 a");
  await page.getByRole("button", { name: "Test and register" }).click();

  await expect(page.getByText("Custom RSS created.", { exact: true })).toBeVisible();
  expect(submitted?.configuration_mode).toBe("manual");
  expect(submitted?.scrape_config).toMatchObject({
    item_selector: "article.news-item",
    title_selector: "h2 a",
    link_selector: "h2 a",
    link_attribute: "href",
  });
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
            entities: [
              "OpenAI",
              `https://example.com/${"unbroken-path-segment".repeat(30)}`,
            ],
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
  await page.getByRole("link", { name: "AI analysis data", exact: true }).click();

  await expect(page).toHaveURL(/\/ai-data$/);
  await expect(page.getByRole("heading", { name: "Analyzed articles" })).toBeVisible();
  await expect(page.getByRole("link", { name: "OpenAI platform update" })).toBeVisible();
  await expect(page.getByText("The platform added new agent capabilities.")).toBeVisible();
  await expect(page.getByText("Tokens: 120 in / 40 out")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    ),
  ).toBe(false);
});

test("runs article analysis manually with a loading state", async ({ page }) => {
  let executionRequests = 0;
  let releaseAnalysis = () => {};
  const analysisPending = new Promise<void>((resolve) => {
    releaseAnalysis = resolve;
  });
  await page.route(/\/api\/ai\/article-analyses/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [],
        total: 0,
        page: 1,
        per_page: 20,
        total_pages: 0,
      }),
    });
  });
  await page.route(/\/api\/settings\/ai-article-analysis\/status\/?$/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ running: false }),
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

  await page.goto("/ai-data");
  await expect(page.getByRole("heading", { name: "Analyzed articles" })).toBeVisible();
  const runButton = page.getByRole("button", { name: "Run analysis now" });
  await expect(runButton).toBeEnabled();
  await runButton.evaluate((button: HTMLButtonElement) => {
    button.click();
    button.click();
  });

  await expect(runButton).toBeDisabled();
  await expect(runButton.locator(".animate-spin")).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Article analysis is running");
  expect(executionRequests).toBe(1);
  await page.waitForTimeout(3_200);
  await expect(runButton).toBeDisabled();
  await expect(runButton.locator(".animate-spin")).toBeVisible();
  releaseAnalysis();
  await expect(page.getByText("Article analysis completed.", { exact: true })).toBeVisible();
  await expect(runButton).toBeEnabled();
  await expect(page.getByRole("status")).toBeHidden();
});

test("disables manual analysis while the server reports a running job", async ({ page }) => {
  let cancellationRequests = 0;
  await page.route(/\/api\/ai\/article-analyses/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [],
        total: 0,
        page: 1,
        per_page: 20,
        total_pages: 0,
      }),
    });
  });
  await page.route(/\/api\/settings\/ai-article-analysis\/status\/?$/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        running: true,
        stopping: cancellationRequests > 0,
        total: 10,
        processed: 4,
        succeeded: 3,
        failed: 1,
        skipped_current: 2,
        current_article_title: "Vue 3.5 released",
        tokens_used_today: 1250,
        daily_token_limit: 50000,
        started_at: 1786492800,
      }),
    });
  });
  await page.route(/\/api\/settings\/ai-article-analysis\/cancel\/?$/, async (route) => {
    cancellationRequests += 1;
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ cancellation_requested: true }),
    });
  });

  await page.goto("/ai-data");

  const runButton = page.getByRole("button", { name: "Run analysis now" });
  await expect(runButton).toBeDisabled();
  await expect(runButton).toContainText("Analysis running");
  await expect(runButton.locator(".animate-spin")).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Article analysis is running");
  await expect(page.getByText("4 / 10 articles")).toBeVisible();
  await expect(page.getByText("40%")).toBeVisible();
  await expect(page.getByText("Current: Vue 3.5 released")).toBeVisible();
  await expect(page.getByText("3 succeeded")).toBeVisible();
  await expect(page.getByText("1,250 / 50,000 tokens today")).toBeVisible();
  await expect(page.getByLabel("Article analysis progress")).toHaveAttribute(
    "aria-valuenow",
    "4",
  );
  const stopButton = page.getByRole("button", { name: "Stop analysis" });
  await stopButton.click();
  await expect.poll(() => cancellationRequests).toBe(1);
  await expect(stopButton).toBeDisabled();
  await expect(stopButton.locator(".animate-spin")).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Stopping article analysis");
});

test("shows an alert when manual article analysis stops with an error", async ({ page }) => {
  await page.route(/\/api\/ai\/article-analyses/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [],
        total: 0,
        page: 1,
        per_page: 20,
        total_pages: 0,
      }),
    });
  });
  await page.route(/\/api\/settings\/ai-article-analysis\/status\/?$/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ running: false }),
    });
  });
  await page.route(/\/api\/settings\/ai-article-analysis\/execute\/?$/, async (route) => {
    await route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({ detail: "The LLM provider stopped responding." }),
    });
  });

  await page.goto("/ai-data");
  await page.getByRole("button", { name: "Run analysis now" }).click();

  const alert = page.getByRole("alert").filter({ hasText: "Article analysis stopped" });
  await expect(alert).toBeVisible();
  await expect(alert).toContainText("The LLM provider stopped responding.");
  await alert.getByRole("button", { name: "Dismiss" }).click();
  await expect(alert).toBeHidden();
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

test("clears AI analysis results from settings after confirmation", async ({ page }) => {
  await page.route(/\/api\/settings\/ai-article-analysis\/results\/?$/, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ cleared_count: 4 }),
    });
  });
  await page.goto("/settings?tab=llm");

  await page.getByRole("button", { name: "Clear analysis results" }).click();
  const dialog = page.getByRole("dialog", { name: "Clear AI analysis results" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("Daily token usage is kept");
  await dialog.getByRole("button", { name: "Clear results" }).click();

  await expect(page.getByText("AI analysis results cleared.", { exact: true })).toBeVisible();
  await expect(page.getByText("4 results removed.", { exact: true })).toBeVisible();
});

test("configures the webhook article limit", async ({ page }) => {
  await page.goto("/settings?tab=webhooks");

  const limitInput = page.getByLabel("Maximum articles per webhook run");
  await expect(limitInput).toHaveValue("20");
  await limitInput.fill("3");
  await page.getByRole("button", { name: "Save limit" }).click();

  await expect(page.getByText("Webhook article limit updated.", { exact: true })).toBeVisible();
  await expect(limitInput).toHaveValue("3");
});
