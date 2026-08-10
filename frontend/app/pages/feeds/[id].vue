<template>
  <UDashboardPanel id="feed-detail">
    <template #header>
      <PageHeaderActions title="Feed" />
    </template>

    <template #body>
      <FeedDetailLayout
        :state="state"
        error-title="Failed to load RSS feed"
        :error-description="loadError"
        not-found-title="RSS feed not found"
        not-found-description="The requested feed does not exist."
      >
        <template #title>
          <div class="flex items-center gap-3">
            <UAvatar
              :src="feed?.icon_url || undefined"
              :alt="feed?.title || 'RSS feed'"
              icon="i-lucide-rss"
              size="2xl"
              color="primary"
              class="shrink-0 rounded-2xl shadow-sm"
              :ui="{ icon: 'size-6' }"
            />
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Feed channel</p>
              <h1 class="mt-1 text-3xl font-bold tracking-tight text-highlighted">{{ feed?.title }}</h1>
            </div>
          </div>
        </template>

        <template #description>
          <p v-if="feed?.description" class="max-w-2xl text-sm leading-6 text-muted">
            {{ feed.description }}
          </p>
          <p v-else class="text-sm text-muted">No description provided.</p>
        </template>

        <template #meta>
          <div class="flex flex-wrap items-center gap-3 pt-2">
            <a
              :href="feed?.url"
              target="_blank"
              rel="noreferrer"
              class="inline-flex max-w-full items-center gap-2 rounded-full bg-elevated px-3 py-1.5 text-xs text-muted hover:text-primary"
            >
              <UIcon name="i-lucide-external-link" class="size-3.5 shrink-0" />
              <span class="truncate">{{ feed?.url }}</span>
            </a>
            <UBadge
              :color="feed?.notify_webhook_enabled ? 'success' : 'neutral'"
              variant="soft"
              :icon="feed?.notify_webhook_enabled ? 'i-lucide-bell-ring' : 'i-lucide-bell-off'"
              :label="feed?.notify_webhook_enabled ? 'Delivery enabled' : 'Delivery muted'"
            />
          </div>
        </template>

        <template #actions>
          <IconButton
            size="sm"
            label="Fetch now"
            icon="i-lucide-refresh-cw"
            color="primary"
            variant="soft"
            :loading="executing"
            @click="executeFeed"
          />
          <IconButton
            size="sm"
            label="Edit"
            icon="i-lucide-pencil"
            color="neutral"
            variant="soft"
            @click="openEditModal"
          />
          <IconButton
            size="sm"
            label="Delete"
            icon="i-lucide-trash-2"
            color="error"
            variant="soft"
            @click="deleteOpen = true"
          />
        </template>

        <ArticleHistoryPanel
          v-model:search-title="searchTitle"
          v-model:published-range="selectedPublishedRange"
          :items="articleList.items"
          :total="articleList.total"
          :current-page="articlePage"
          :total-pages="articleList.total_pages"
          :loading="articlesLoading"
          @page="setArticlePage"
          @refresh="loadArticles(true)"
        />

        <RSSFeedEditorModal
          v-model:open="modalOpen"
          :form="feedForm"
          :webhooks="webhooks"
          :title="feedForm.id ? 'Edit RSS feed' : 'Register RSS feed'"
          :description="feedForm.id ? 'Update the selected feed.' : 'Create a new feed link.'"
          title-placeholder="Feed title"
          url-placeholder="https://example.com/feed.xml"
          description-placeholder="Optional description"
          submit-label="Save feed"
          :saving="saving"
          @save="saveFeed"
        />

        <DeleteConfirmModal
          v-model:open="deleteOpen"
          title="Delete RSS feed"
          :subject="feed?.title"
          confirm-label="Delete feed"
          :loading="deleting"
          @cancel="deleteOpen = false"
          @confirm="confirmDelete"
        />
      </FeedDetailLayout>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { DateRange } from "reka-ui";
import type {
  RSSFeedArticleListResponse,
  RSSFeedExecuteResponse,
  RSSFeedResponse,
  SettingsWebhookListResponse,
  SettingsWebhookResponse,
} from "~/types";

const route = useRoute();
const router = useRouter();
const { request } = useApi();
const toast = useSingleToast();
const { refresh: refreshSidebarCatalog } = useSidebarCatalog();

const state = ref<"loading" | "ready" | "error" | "not-found">("loading");
const loadError = ref("");
const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const executing = ref(false);
const articlesLoading = ref(false);
const searchTitle = ref("");
const selectedPublishedRange = shallowRef<DateRange>();
const modalOpen = ref(false);
const deleteOpen = ref(false);
const feed = ref<RSSFeedResponse | null>(null);
const articleList = ref<RSSFeedArticleListResponse>({
  items: [],
  total: 0,
  page: 1,
  per_page: 20,
  total_pages: 0,
});
const articlePage = ref(1);
const webhooks = ref<SettingsWebhookResponse[]>([]);
const feedForm = reactive({
  id: "",
  title: "",
  url: "",
  description: "",
  webhookIds: [] as number[],
  iconUrl: "",
  iconFile: null as File | null,
  existingIconUrl: "",
  removeIcon: false,
});

const articlePageCount = computed(() => Math.max(articleList.value.total_pages, 1));

const buildArticleQuery = () => {
  const params = new URLSearchParams({ page: String(articlePage.value) });
  const q = searchTitle.value.trim();
  if (q) params.set("q", q);
  const publishedFrom = selectedPublishedRange.value?.start?.toString();
  const publishedTo = selectedPublishedRange.value?.end?.toString();
  if (publishedFrom) params.set("published_from", publishedFrom);
  if (publishedTo) params.set("published_to", publishedTo);
  return params.toString();
};
const loadWebhooks = async () => {
  try {
    const response = await request<SettingsWebhookListResponse>("/settings/webhooks");
    webhooks.value = response.items;
  } catch (err) {
    toast.show({
      title: "Failed to load webhooks.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

const loadFeed = async (showToast = false) => {
  loading.value = true;
  state.value = "loading";
  loadError.value = "";

  try {
    const result = await request<RSSFeedResponse>(`/rss-feeds/${route.params.id}`);
    feed.value = result;
    state.value = "ready";
    if (showToast) {
      toast.show({
        title: "RSS feed loaded.",
        color: "success",
        icon: "i-lucide-check",
      });
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to load RSS feed.";
    loadError.value = message;
    state.value = message.includes("404") ? "not-found" : "error";
    if (state.value === "error") {
      toast.show({
        title: "Failed to load RSS feed.",
        description: err instanceof Error ? err.message : undefined,
        color: "error",
        icon: "i-lucide-circle-alert",
      });
    }
  } finally {
    loading.value = false;
  }
};

const loadFeedArticles = async (showToast = false) => {
  articlesLoading.value = true;
  try {
    const result = await request<RSSFeedArticleListResponse>(
      `/rss-feeds/${route.params.id}/articles?${buildArticleQuery()}`,
    );
    articleList.value = result;
    if (showToast) {
      toast.show({
        title: "RSS articles loaded.",
        color: "success",
        icon: "i-lucide-check",
      });
    }
  } catch (err) {
    toast.show({
      title: "Failed to load RSS articles.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    articlesLoading.value = false;
  }
};

const loadArticles = async (showToast = false) => {
  await loadFeedArticles(showToast);
};

const setArticlePage = async (nextPage: number) => {
  articlePage.value = Math.min(Math.max(nextPage, 1), articlePageCount.value);
  await loadArticles();
};

watch(
  searchTitle,
  async () => {
    articlePage.value = 1;
    await loadArticles();
  },
);

watch(
  selectedPublishedRange,
  async () => {
    articlePage.value = 1;
    await loadArticles();
  },
  { deep: true },
);

const openEditModal = () => {
  if (!feed.value) return;
  feedForm.id = String(feed.value.id);
  feedForm.title = feed.value.title;
  feedForm.url = feed.value.url;
  feedForm.description = feed.value.description || "";
  feedForm.webhookIds = [...feed.value.webhook_ids];
  feedForm.iconUrl = feed.value.icon_uploaded ? "" : (feed.value.icon_url || "");
  feedForm.iconFile = null;
  feedForm.existingIconUrl = feed.value.icon_url || "";
  feedForm.removeIcon = false;
  modalOpen.value = true;
};

const closeModal = () => {
  modalOpen.value = false;
  feedForm.id = "";
  feedForm.title = "";
  feedForm.url = "";
  feedForm.description = "";
  feedForm.webhookIds = [];
  feedForm.iconUrl = "";
  feedForm.iconFile = null;
  feedForm.existingIconUrl = "";
  feedForm.removeIcon = false;
};

const saveFeed = async () => {
  const url = feedForm.url.trim();
  const title = feedForm.title.trim();
  if (!url || !title) return;

  saving.value = true;
  try {
    const updated = await request<RSSFeedResponse>(`/rss-feeds/${feedForm.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        url,
        title,
        description: feedForm.description || null,
        webhook_ids: feedForm.webhookIds,
        ...(feedForm.iconUrl.trim() ? { icon_url: feedForm.iconUrl.trim() } : {}),
      }),
    });
    if (feedForm.iconFile) {
      const body = new FormData();
      body.append("file", feedForm.iconFile);
      body.append("public_url", `${window.location.origin}/api/rss-feeds/${updated.id}/icon`);
      await request(`/rss-feeds/${updated.id}/icon`, { method: "PUT", body });
    } else if (feedForm.removeIcon) {
      await request(`/rss-feeds/${updated.id}/icon`, { method: "DELETE" });
    }
    closeModal();
    await loadFeed();
    await loadFeedArticles();
    toast.show({
      title: "RSS feed updated.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to update RSS feed.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
};

const executeFeed = async () => {
  if (!feed.value) return;
  executing.value = true;
  try {
    const result = await request<RSSFeedExecuteResponse>(`/rss-feeds/${feed.value.id}/execute`, {
      method: "POST",
    });
    await loadFeedArticles();
    toast.show({
      title: result.delivered ? "RSS feed executed." : "RSS feed execution finished.",
      description: result.message || undefined,
      color: result.delivered ? "success" : "warning",
      icon: result.delivered ? "i-lucide-check" : "i-lucide-circle-alert",
    });
  } catch (err) {
    toast.show({
      title: "Failed to execute RSS feed.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    executing.value = false;
  }
};

const confirmDelete = async () => {
  if (!feed.value) return;
  deleting.value = true;
  try {
    await request(`/rss-feeds/${feed.value.id}`, { method: "DELETE" });
    await refreshSidebarCatalog(true);
    toast.show({
      title: "RSS feed deleted.",
      color: "success",
      icon: "i-lucide-check",
    });
    await router.push("/");
  } catch (err) {
    toast.show({
      title: "Failed to delete RSS feed.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    deleting.value = false;
  }
};

onMounted(() => {
  void loadFeed();
  void loadFeedArticles();
  void loadWebhooks();
});
</script>
