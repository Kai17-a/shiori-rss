import { describe, expect, it, vi } from "vitest";

import {
  applySidebarCatalogResults,
  createSidebarCatalogState,
  refreshSidebarCatalogSafely,
} from "~/utils/sidebarCatalog";

describe("sidebarCatalog helpers", () => {
  it("creates a predictable empty state", () => {
    expect(createSidebarCatalogState()).toEqual({
      folders: [],
      tags: [],
      rssFeeds: [],
      newsSites: [],
      loaded: false,
    });
  });

  it("applies loaded catalog data to the state object", () => {
    const state = createSidebarCatalogState();
    const folders = [{ id: 1, name: "Work", created_at: "2026-04-10T00:00:00Z" }];
    const tags = [{ id: 2, name: "Frontend" }];
    const rssFeeds = [{ id: 3, title: "Daily", url: "https://example.com/feed", description: null, created_at: "2026-04-10T00:00:00Z", updated_at: "2026-04-10T00:00:00Z" }];

    const newsSites = [{ id: 4, title: "Custom Daily", url: "https://example.com/news", description: null, notify_webhook_enabled: true, webhook_ids: [], created_at: "2026-04-10T00:00:00Z", updated_at: "2026-04-10T00:00:00Z" }];

    expect(applySidebarCatalogResults(state, folders, tags, rssFeeds, newsSites)).toBe(state);
    expect(state).toEqual({
      folders,
      tags,
      rssFeeds,
      newsSites,
      loaded: true,
    });
  });

  it("contains initial catalog failures and supports forced retry", async () => {
    const failedRefresh = vi.fn().mockRejectedValue(new Error("offline"));
    await expect(refreshSidebarCatalogSafely(failedRefresh)).resolves.toBe(false);

    const recoveredRefresh = vi.fn().mockResolvedValue(undefined);
    await expect(refreshSidebarCatalogSafely(recoveredRefresh, true)).resolves.toBe(true);
    expect(recoveredRefresh).toHaveBeenCalledWith(true);
  });
});
