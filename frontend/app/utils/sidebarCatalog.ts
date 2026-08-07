import type { FolderResponse, NewsSiteResponse, RSSFeedResponse, TagResponse } from "~/types";

export type SidebarCatalogState = {
  folders: FolderResponse[];
  tags: TagResponse[];
  rssFeeds: RSSFeedResponse[];
  newsSites: NewsSiteResponse[];
  loaded: boolean;
};

export const createSidebarCatalogState = (): SidebarCatalogState => ({
  folders: [],
  tags: [],
  rssFeeds: [],
  newsSites: [],
  loaded: false,
});

export const applySidebarCatalogResults = (
  state: SidebarCatalogState,
  folders: FolderResponse[],
  tags: TagResponse[],
  rssFeeds: RSSFeedResponse[],
  newsSites: NewsSiteResponse[] = [],
) => {
  state.folders = folders;
  state.tags = tags;
  state.rssFeeds = rssFeeds;
  state.newsSites = newsSites;
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
