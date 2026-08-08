import { describe, expect, it, vi } from "vitest";

import {
  applySidebarCatalogResults,
  createSidebarCatalogState,
  refreshSidebarCatalogSafely,
} from "~/utils/sidebarCatalog";

describe("sidebarCatalog helpers", () => {
  it("creates an empty RSS catalog", () => {
    expect(createSidebarCatalogState()).toEqual({
      rssFeeds: [],
      customFeeds: [],
      loaded: false,
    });
  });

  it("applies loaded RSS feeds", () => {
    const state = createSidebarCatalogState();
    const rssFeeds = [{
      id: 3,
      title: "Daily",
      url: "https://example.com/feed",
      description: null,
      notify_webhook_enabled: true,
      webhook_ids: [],
      created_at: "2026-04-10T00:00:00Z",
      updated_at: "2026-04-10T00:00:00Z",
    }];
    const customFeeds = [{
      id: 7,
      title: "LLM Daily",
      url: "https://example.com/news",
      description: null,
      notify_webhook_enabled: true,
      webhook_ids: [],
      created_at: "2026-04-10T00:00:00Z",
      updated_at: "2026-04-10T00:00:00Z",
    }];

    expect(applySidebarCatalogResults(state, rssFeeds, customFeeds)).toBe(state);
    expect(state).toEqual({ rssFeeds, customFeeds, loaded: true });
  });

  it("contains initial catalog failures and supports forced retry", async () => {
    const failedRefresh = vi.fn().mockRejectedValue(new Error("offline"));
    await expect(refreshSidebarCatalogSafely(failedRefresh)).resolves.toBe(false);

    const recoveredRefresh = vi.fn().mockResolvedValue(undefined);
    await expect(refreshSidebarCatalogSafely(recoveredRefresh, true)).resolves.toBe(true);
    expect(recoveredRefresh).toHaveBeenCalledWith(true);
  });
});
