import {
  applySidebarCatalogResults,
  createSidebarCatalogState,
  type SidebarCatalogState,
} from "~/utils/sidebarCatalog";
import type { RSSFeedListResponse } from "~/types";

let sidebarCatalogLoadPromise: Promise<void> | null = null;

export const useSidebarCatalog = () => {
  const state = useState<SidebarCatalogState>("sidebar-catalog", createSidebarCatalogState);
  const { request } = useApi();
  const loading = ref(false);

  const refresh = async (force = false) => {
    if (state.value.loaded && !force) return;
    if (sidebarCatalogLoadPromise) return sidebarCatalogLoadPromise;

    sidebarCatalogLoadPromise = (async () => {
      loading.value = true;
      try {
        const response = await request<RSSFeedListResponse>("/rss-feeds?per_page=100");
        applySidebarCatalogResults(state.value, response.items || []);
      } finally {
        loading.value = false;
        sidebarCatalogLoadPromise = null;
      }
    })();
    return sidebarCatalogLoadPromise;
  };

  return {
    rssFeeds: computed(() => state.value.rssFeeds),
    loaded: computed(() => state.value.loaded),
    loading: computed(() => loading.value),
    refresh,
  };
};
