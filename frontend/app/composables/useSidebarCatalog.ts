import {
  applySidebarCatalogResults,
  createSidebarCatalogState,
  type SidebarCatalogState,
} from "~/utils/sidebarCatalog";
import type {
  FolderResponse,
  NewsSiteListResponse,
  RSSFeedListResponse,
  TagResponse,
} from "~/types";

let sidebarCatalogLoadPromise: Promise<void> | null = null;

export const useSidebarCatalog = () => {
  const state = useState<SidebarCatalogState>("sidebar-catalog", createSidebarCatalogState);

  const { request } = useBookmarkApi();
  const loading = ref(false);

  const refresh = async (force = false) => {
    if (state.value.loaded && !force) {
      return;
    }

    if (sidebarCatalogLoadPromise) {
      return sidebarCatalogLoadPromise;
    }

    sidebarCatalogLoadPromise = (async () => {
      loading.value = true;
      try {
        const [foldersRes, tagsRes, rssFeedsRes, newsSitesRes] = await Promise.all([
          request<FolderResponse[]>("/folders"),
          request<TagResponse[]>("/tags"),
          request<RSSFeedListResponse>("/rss-feeds?per_page=100"),
          request<NewsSiteListResponse>("/news-sites?per_page=100"),
        ]);

        applySidebarCatalogResults(
          state.value,
          foldersRes,
          tagsRes,
          rssFeedsRes.items || [],
          newsSitesRes.items || [],
        );
      } finally {
        loading.value = false;
        sidebarCatalogLoadPromise = null;
      }
    })();

    return sidebarCatalogLoadPromise;
  };

  return {
    folders: computed(() => state.value.folders),
    tags: computed(() => state.value.tags),
    rssFeeds: computed(() => state.value.rssFeeds),
    newsSites: computed(() => state.value.newsSites),
    loaded: computed(() => state.value.loaded),
    loading: computed(() => loading.value),
    refresh,
  };
};
