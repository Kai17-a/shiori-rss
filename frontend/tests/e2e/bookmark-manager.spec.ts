import { expect, test, type Locator, type Page } from "@playwright/test";
import { createServer } from "node:http";
import process from "node:process";

const apiBaseUrl = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";
const discordWebhookUrl = "https://discord.com/api/webhooks/1234567890/test-token";
const buttonByText = (page: Page, label: string) => page.locator(`button:has-text("${label}")`).first();
const headingByText = (page: Page, text: string) => page.locator("h1").filter({ hasText: text }).last();
const activate = async (locator: Locator) => {
  await locator.focus();
  await locator.press("Enter");
};

const createBookmark = async (
  page: Page,
  suffix: string,
  overrides: Partial<{
    url: string;
    title: string;
    description: string;
    folder_id: number | null;
    tag_ids: number[];
    is_favorite: boolean;
  }> = {},
) => {
  const created = await page.request.post(`${apiBaseUrl}/bookmarks`, {
    data: {
      url: overrides.url ?? `https://example.com/${suffix}`,
      title: overrides.title ?? `Example Bookmark ${suffix}`,
      description: overrides.description ?? "Original description",
      folder_id: overrides.folder_id ?? null,
      tag_ids: overrides.tag_ids ?? [],
    },
  });
  expect(created.status()).toBe(201);
  const createdBody = (await created.json()) as { id: number };

  if (overrides.is_favorite) {
    const favorited = await page.request.patch(`${apiBaseUrl}/bookmarks/favorite`, {
      data: {
        bookmark_id: createdBody.id,
        is_favorite: true,
      },
    });
    expect(favorited.status()).toBe(200);
  }

  return createdBody;
};

const startRssServer = async (suffix: string) => {
  const server = createServer((_, res) => {
    res.writeHead(200, { "content-type": "application/rss+xml; charset=utf-8" });
    res.end(`<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>RSS Feed ${suffix}</title>
    <link>https://example.com/${suffix}</link>
    <description>RSS description</description>
    <item>
      <title>Item ${suffix}</title>
      <link>https://example.com/${suffix}/1</link>
      <description>Item description</description>
    </item>
  </channel>
</rss>`);
  });

  await new Promise<void>((resolve) => {
    server.listen(0, "127.0.0.1", resolve);
  });

  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("Failed to start RSS test server");
  }

  return {
    url: `http://127.0.0.1:${address.port}/feed.xml`,
    close: () =>
      new Promise<void>((resolve, reject) => {
        server.close((err) => (err ? reject(err) : resolve()));
      }),
  };
};

test.describe.configure({ mode: "serial" });

test.describe("bookmarks", () => {
  test("loads, edits, searches, and deletes bookmarks", async ({ page }) => {
    const suffix = `${Date.now()}-${test.info().workerIndex}`;
    const url = `https://example.com/${suffix}`;
    const title = `Example Bookmark ${suffix}`;
    const updatedTitle = `${title} Updated`;
    const updatedDescription = "Updated description";
    await page.goto("/bookmarks");
    await expect(page).toHaveURL(/\/bookmarks\/?$/);
    await activate(buttonByText(page, "Register"));
    await expect(page.getByRole("dialog")).toContainText("Register bookmark");
    await page.getByRole("textbox", { name: "Title" }).fill(title);
    await page.getByRole("textbox", { name: "URL" }).fill(url);
    await page.getByRole("textbox", { name: "Description" }).fill("Original description");
    await buttonByText(page, "Save bookmark").click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByText(title, { exact: true })).toBeVisible();

    const bookmarkCard = page.locator("article").filter({ has: page.getByText(title, { exact: true }) });
    await activate(bookmarkCard.locator("button").nth(1));
    await page.getByRole("textbox", { name: "Title" }).fill(updatedTitle);
    await page.getByRole("textbox", { name: "Description" }).fill(updatedDescription);
    await buttonByText(page, "Save bookmark").click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByText(updatedTitle, { exact: true })).toBeVisible();

    const updatedBookmarkCard = page
      .locator("article")
      .filter({ has: page.getByText(updatedTitle, { exact: true }) });
    await activate(updatedBookmarkCard.locator("button").nth(1));
    await page.getByRole("textbox", { name: "Description" }).fill("");
    await buttonByText(page, "Save bookmark").click();
    await expect(page.getByRole("dialog")).toHaveCount(0);

    await activate(updatedBookmarkCard.locator("button").nth(1));
    await expect(page.getByRole("textbox", { name: "Description" })).toHaveValue("");
    await buttonByText(page, "Cancel").click();

    const searchInput = page.getByPlaceholder("Search by title or URL");
    await searchInput.fill(updatedTitle);
    await expect(page.getByText(updatedTitle, { exact: true })).toBeVisible();
    await searchInput.fill("does-not-exist");
    await expect(page.getByText("No bookmarks yet.")).toBeVisible();
    await searchInput.fill(updatedTitle);
    await expect(page.getByText(updatedTitle, { exact: true })).toBeVisible();

    await page
      .locator("article")
      .filter({ has: page.getByText(updatedTitle, { exact: true }) })
      .getByRole("button")
      .last()
      .click({ force: true });
    await buttonByText(page, "Delete bookmark").click();
    await expect(page.getByText(updatedTitle, { exact: true })).toHaveCount(0);
  });

  test("normalizes an out-of-range page after narrowing results", async ({ page }) => {
    const suffix = `${Date.now()}-${test.info().workerIndex}`;
    const titles = Array.from(
      { length: 21 },
      (_, index) => `Paged Bookmark ${suffix} ${index}`,
    );

    for (const [index, title] of titles.entries()) {
      await createBookmark(page, `${suffix}-${index}`, { title });
    }

    await page.goto("/bookmarks?page=999");
    await expect(page).toHaveURL((url) => url.searchParams.get("page") === "2");
    await expect(page.getByText("Page 2 of 2")).toBeVisible();

    const searchInput = page.getByPlaceholder("Search by title or URL");
    await searchInput.fill(titles[0]!);
    await expect(page).toHaveURL(
      (url) => url.searchParams.get("q") === titles[0] && !url.searchParams.has("page"),
    );
    await expect(page.getByText(titles[0]!, { exact: true })).toBeVisible();
    await expect(page.getByText("Page 1 of 1")).toBeVisible();
  });
});

test.describe("folders", () => {
  test("creates, edits, opens, and deletes folders from the UI", async ({ page }) => {
    const suffix = `${Date.now()}-${test.info().workerIndex}`;
    const name = `Folder ${suffix}`;
    const updatedName = `${name} Updated`;
    const folderPanel = page.locator("#dashboard-panel-folders");

    await page.goto("/folders");
    await page.getByPlaceholder("New folder name").fill(name);
    await page.getByPlaceholder("Optional folder description").first().fill("Folder description");
    await activate(buttonByText(page, "Add folder"));
    await expect(folderPanel.getByText(name, { exact: true })).toBeVisible();

    let folderCard = folderPanel
      .getByText(name, { exact: true })
      .locator("xpath=ancestor::*[.//button][1]");
    await activate(folderCard.locator("button").first());
    await page.getByRole("textbox", { name: "Folder name" }).fill(updatedName);
    await page.getByRole("textbox", { name: "Description" }).fill("Updated folder description");
    await buttonByText(page, "Save changes").click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(folderPanel.getByText(updatedName, { exact: true })).toBeVisible();

    await activate(folderPanel.locator("a").filter({ hasText: updatedName }).first());
    await expect(page).toHaveURL(/\/folders\/\d+\/?$/);
    await expect(headingByText(page, updatedName)).toBeVisible();

    const folderId = Number(page.url().match(/\/folders\/(\d+)/)?.[1]);
    expect(folderId).toBeGreaterThan(0);
    const relatedTitles = Array.from(
      { length: 21 },
      (_, index) => `Folder bookmark ${suffix} ${index}`,
    );
    for (const [index, title] of relatedTitles.entries()) {
      await createBookmark(page, `${suffix}-folder-${index}`, { folder_id: folderId, title });
    }
    await buttonByText(page, "Refresh").click();
    await expect(page.getByText("21 bookmarks")).toBeVisible();
    await expect(page.getByText("Page 1 of 2")).toBeVisible();
    await buttonByText(page, "Next").click();
    await expect(page.getByText("Page 2 of 2")).toBeVisible();
    await expect(page.getByText(relatedTitles[0]!, { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Delete" }).first().click();
    await buttonByText(page, "Delete folder").click();
    await expect(page).toHaveURL(/\/folders\/?$/);
    await expect(folderPanel.getByText(updatedName, { exact: true })).toHaveCount(0);
  });
});

test.describe("tags", () => {
  test("creates, edits, opens, and deletes tags from the UI", async ({ page }) => {
    const suffix = `${Date.now()}-${test.info().workerIndex}`;
    const name = `Tag ${suffix}`;
    const updatedName = `${name} Updated`;
    const tagPanel = page.locator("#dashboard-panel-tags");

    await page.goto("/tags");
    await page.getByPlaceholder("New tag name").fill(name);
    await page.getByPlaceholder("Optional tag description").first().fill("Tag description");
    await activate(buttonByText(page, "Add tag"));
    await expect(tagPanel.getByText(name, { exact: true })).toBeVisible();

    let tagCard = tagPanel
      .getByText(name, { exact: true })
      .locator("xpath=ancestor::*[.//button][1]");
    await activate(tagCard.locator("button").first());
    await page.getByRole("textbox", { name: "Tag name" }).fill(updatedName);
    await page.getByRole("textbox", { name: "Description" }).fill("Updated tag description");
    await buttonByText(page, "Save changes").click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(tagPanel.getByText(updatedName, { exact: true })).toBeVisible();

    await activate(tagPanel.locator("a").filter({ hasText: updatedName }).first());
    await expect(page).toHaveURL(/\/tags\/\d+\/?$/);
    await expect(headingByText(page, updatedName)).toBeVisible();

    const tagId = Number(page.url().match(/\/tags\/(\d+)/)?.[1]);
    expect(tagId).toBeGreaterThan(0);
    const relatedTitles = Array.from(
      { length: 21 },
      (_, index) => `Tag bookmark ${suffix} ${index}`,
    );
    for (const [index, title] of relatedTitles.entries()) {
      await createBookmark(page, `${suffix}-tag-${index}`, { tag_ids: [tagId], title });
    }
    await buttonByText(page, "Refresh").click();
    await expect(page.getByText("21 bookmarks")).toBeVisible();
    await expect(page.getByText("Page 1 of 2")).toBeVisible();
    await buttonByText(page, "Next").click();
    await expect(page.getByText("Page 2 of 2")).toBeVisible();
    await expect(page.getByText(relatedTitles[0]!, { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Delete" }).first().click();
    await buttonByText(page, "Delete tag").click();
    await expect(page).toHaveURL(/\/tags\/?$/);
    await expect(tagPanel.getByText(updatedName, { exact: true })).toHaveCount(0);
  });
});

test.describe("rss feeds", () => {
  test("creates, edits, opens, and deletes rss feeds from the UI", async ({ page }) => {
    const suffix = `${Date.now()}-${test.info().workerIndex}`;
    const rssServer = await startRssServer(suffix);
    try {
      const title = `RSS Feed ${suffix}`;
      const updatedTitle = `${title} Updated`;
      const rssPanel = page.locator("#dashboard-panel-rss");

      await page.goto("/rss");
      await expect(page).toHaveURL(/\/rss\/?$/);
      await activate(buttonByText(page, "Register"));
      await expect(page.getByRole("dialog")).toContainText("Register RSS feed");
      await page.getByRole("textbox", { name: "Title" }).fill(title);
      await page.getByRole("textbox", { name: "URL" }).fill(rssServer.url);
      await page.getByRole("textbox", { name: "Description" }).fill("RSS description");
      await buttonByText(page, "Save feed").click();
      await expect(page.getByRole("dialog")).toHaveCount(0);
      await expect(rssPanel.getByText(title, { exact: true })).toBeVisible();

      let feedCard = page.locator("article").filter({ has: page.getByText(title, { exact: true }) });
      await activate(feedCard.locator("button").nth(2));
      await page.getByRole("textbox", { name: "Title" }).fill(updatedTitle);
      await page.getByRole("textbox", { name: "Description" }).fill("Updated RSS description");
      await buttonByText(page, "Save feed").click();
      await expect(page.getByRole("dialog")).toHaveCount(0);
      await expect(rssPanel.getByText(updatedTitle, { exact: true })).toBeVisible();

      feedCard = page
        .locator("article")
        .filter({ has: page.getByText(updatedTitle, { exact: true }) });
      await activate(feedCard.locator("a").filter({ hasText: updatedTitle }).first());
      await expect(page).toHaveURL(/\/rss\/\d+\/?$/);
      await expect(headingByText(page, updatedTitle)).toBeVisible();
      await page.goto("/rss");
      await expect(page).toHaveURL(/\/rss\/?$/);
      await expect(rssPanel.getByText(updatedTitle, { exact: true })).toBeVisible();

      const pagedFeedTitles = Array.from(
        { length: 20 },
        (_, index) => `Paged RSS Feed ${suffix} ${index}`,
      );
      for (const [index, pagedTitle] of pagedFeedTitles.entries()) {
        const created = await page.request.post(`${apiBaseUrl}/rss-feeds`, {
          data: {
            title: pagedTitle,
            url: `${rssServer.url}?page=${index}`,
            description: "Paged RSS description",
          },
        });
        expect(created.status()).toBe(201);
        await created.dispose();
      }
      await rssPanel.getByRole("button", { name: "Refresh" }).first().click();
      await expect(page.getByText("Total 21 feeds · Page 1 of 2")).toBeVisible();
      await page.getByRole("button", { name: "2", exact: true }).click();
      await expect(page.getByText("Total 21 feeds · Page 2 of 2")).toBeVisible();
      await expect(rssPanel.getByText(updatedTitle, { exact: true })).toBeVisible();

      feedCard = page
        .locator("article")
        .filter({ has: page.getByText(updatedTitle, { exact: true }) });
      await activate(feedCard.locator("button").nth(3));
      await buttonByText(page, "Delete feed").click();
      await expect(rssPanel.getByText(updatedTitle, { exact: true })).toHaveCount(0);
      await expect(page.getByText("Total 20 feeds · Page 1 of 1")).toBeVisible();
    } finally {
      await rssServer.close();
    }
  });

  test("manages webhook endpoints from settings and toggles rss execution", async ({ page }) => {
    const registered = await page.request.get(`${apiBaseUrl}/settings/webhooks`);
    for (const item of (await registered.json()).items as { id: number }[]) {
      await page.request.delete(`${apiBaseUrl}/settings/webhooks/${item.id}`);
    }
    await page.request.put(`${apiBaseUrl}/settings/rss-execution`, {
      data: { enabled: false },
    });
    await page.request.put(`${apiBaseUrl}/settings/rss-webhook-notification`, {
      data: { enabled: false },
    });

    await page.goto("/settings");
    await expect(page.getByText("No webhooks are registered yet.")).toBeVisible();

    const slackWebhookUrl = "https://hooks.slack.com/services/xxx/yyy/zzz";
    const discordWebhookName = "Discord alerts";
    const slackWebhookName = "Slack alerts";
    const nameInput = page.getByLabel("Name");
    const webhookInput = page.getByLabel("Webhook URL");

    await nameInput.fill(discordWebhookName);
    await webhookInput.fill(discordWebhookUrl);
    await buttonByText(page, "Add webhook").click({ force: true });
    await expect(page.getByText(discordWebhookName)).toBeVisible();

    await nameInput.fill(slackWebhookName);
    await webhookInput.fill(slackWebhookUrl);
    await buttonByText(page, "Add webhook").click({ force: true });
    await expect(page.getByText(slackWebhookName)).toBeVisible();

    await page.reload();
    await expect(page.getByText(discordWebhookName)).toBeVisible();
    await expect(page.getByText(slackWebhookName)).toBeVisible();

    const slackEnabledSwitch = page.getByRole("switch", { name: `Disable ${slackWebhookName}` });
    await expect(slackEnabledSwitch).toHaveAttribute("aria-checked", "true");
    await slackEnabledSwitch.click({ force: true });
    await expect(
      page.getByRole("switch", { name: `Enable ${slackWebhookName}` }),
    ).toHaveAttribute("aria-checked", "false");
    await page.reload();
    await expect(
      page.getByRole("switch", { name: `Enable ${slackWebhookName}` }),
    ).toHaveAttribute("aria-checked", "false");

    const firstWebhookRow = page
      .locator("div.rounded-xl", { hasText: discordWebhookName })
      .first();
    await firstWebhookRow.getByRole("button", { name: "Delete" }).click({ force: true });
    await buttonByText(page, "Delete webhook").click({ force: true });
    await expect(page.getByText(discordWebhookName)).toHaveCount(0);
    await expect(page.getByText(slackWebhookName)).toBeVisible();

    await page.goto("/rss");
    const rssExecutionSwitch = page.getByRole("switch").first();
    const rssWebhookNotificationSwitch = page.getByRole("switch").nth(1);
    await expect(rssExecutionSwitch).toHaveAttribute("aria-checked", "false");
    await rssExecutionSwitch.click({ force: true });
    await expect(rssExecutionSwitch).toHaveAttribute("aria-checked", "true");
    await expect(rssWebhookNotificationSwitch).toHaveAttribute("aria-checked", "false");
    await rssWebhookNotificationSwitch.click({ force: true });
    await expect(rssWebhookNotificationSwitch).toHaveAttribute("aria-checked", "true");
  });

});

test.describe("favorites", () => {
  test("paginates favorite bookmarks and removes them through the favorite toggle", async ({ page }) => {
    const suffix = `${Date.now()}-${test.info().workerIndex}`;
    await createBookmark(page, `${suffix}-regular`, {
      title: `Regular Bookmark ${suffix}`,
      is_favorite: false,
    });
    await createBookmark(page, `${suffix}-favorite`, {
      title: `Favorite Bookmark ${suffix}`,
      is_favorite: true,
    });
    const pagedFavoriteTitles = Array.from(
      { length: 20 },
      (_, index) => `Paged Favorite Bookmark ${suffix} ${index}`,
    );
    for (const [index, title] of pagedFavoriteTitles.entries()) {
      await createBookmark(page, `${suffix}-favorite-page-${index}`, {
        title,
        is_favorite: true,
      });
    }

    await page.goto("/favorites");
    await expect(page).toHaveURL(/\/favorites\/?$/);
    await buttonByText(page, "Refresh").click({ force: true });
    await expect(page.getByText("21 favorites")).toBeVisible();
    await expect(page.getByText("Page 1 of 2")).toBeVisible();
    await expect(page.getByText(`Regular Bookmark ${suffix}`, { exact: true })).toHaveCount(0);

    await buttonByText(page, "Next").click();
    await expect(page.getByText("Page 2 of 2")).toBeVisible();
    await expect(page.getByText(`Favorite Bookmark ${suffix}`, { exact: true })).toBeVisible();

    const favoriteCard = page
      .locator("article")
      .filter({ has: page.getByText(`Favorite Bookmark ${suffix}`, { exact: true }) });
    await favoriteCard.getByRole("button", { name: "Remove from favorites" }).click({ force: true });
    await expect(page.getByText(`Favorite Bookmark ${suffix}`, { exact: true })).toHaveCount(0);
  });
});

test.describe("settings", () => {
  test("toggles theme and persists the selection", async ({ page }) => {
    await page.goto("/settings");
    await expect(page).toHaveURL(/\/settings\/?$/);
    await expect(page.getByText("Theme", { exact: true })).toBeVisible();
    const darkTab = page.locator('[role="tab"]').filter({ hasText: "Dark" });
    const systemTab = page.locator('[role="tab"]').filter({ hasText: "System" });

    await darkTab.focus();
    await page.keyboard.press("Enter");
    await expect(darkTab).toHaveAttribute("aria-selected", "true");
    await page.reload();
    await expect(darkTab).toHaveAttribute("aria-selected", "true");
    await systemTab.focus();
    await page.keyboard.press("Enter");
  });
});
