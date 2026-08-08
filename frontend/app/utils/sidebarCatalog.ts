import type { NewsSiteResponse, RSSFeedResponse } from "~/types";

export type SidebarCatalogState = {
  rssFeeds: RSSFeedResponse[];
  customFeeds: NewsSiteResponse[];
  loaded: boolean;
};

export const createSidebarCatalogState = (): SidebarCatalogState => ({
  rssFeeds: [],
  customFeeds: [],
  loaded: false,
});

export const applySidebarCatalogResults = (
  state: SidebarCatalogState,
  rssFeeds: RSSFeedResponse[],
  customFeeds: NewsSiteResponse[],
) => {
  state.rssFeeds = rssFeeds;
  state.customFeeds = customFeeds;
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
