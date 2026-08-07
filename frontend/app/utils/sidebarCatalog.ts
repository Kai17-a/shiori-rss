import type { RSSFeedResponse } from "~/types";

export type SidebarCatalogState = {
  rssFeeds: RSSFeedResponse[];
  loaded: boolean;
};

export const createSidebarCatalogState = (): SidebarCatalogState => ({
  rssFeeds: [],
  loaded: false,
});

export const applySidebarCatalogResults = (
  state: SidebarCatalogState,
  rssFeeds: RSSFeedResponse[],
) => {
  state.rssFeeds = rssFeeds;
  state.loaded = true;
  return state;
};

export const refreshSidebarCatalogSafely = async (
  refresh: (force?: boolean) => Promise<void>,
  force = false,
) => {
  try {
    await refresh(force);
    return true;
  } catch {
    return false;
  }
};
