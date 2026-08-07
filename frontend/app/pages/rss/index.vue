<template>
  <UDashboardPanel id="rss">
    <template #header>
      <PageHeaderActions title="RSS" />
    </template>

    <template #body>
      <div class="space-y-6">
        <UPageCard
          title="RSS periodic execution"
          description="Enable or disable the scheduled RSS batch process"
          :ui="{ body: 'space-y-4' }"
        >
          <div class="space-y-4">
            <div class="flex items-start justify-between gap-4">
              <div class="space-y-1">
                <p class="text-sm font-medium text-default">Run on schedule</p>
                <p class="text-sm text-muted">
                  When enabled, the batch process runs RSS delivery jobs on the schedule
                  configured for the container.
                </p>
              </div>
              <USwitch v-model="rssExecutionEnabled" :loading="rssExecutionLoading" />
            </div>

            <div class="h-px bg-border/60" />

            <div class="flex items-start justify-between gap-4">
              <div class="space-y-1">
                <p class="text-sm font-medium text-default">Send webhook notifications</p>
                <p class="text-sm text-muted">
                  When disabled, the batch process still runs but skips webhook delivery.
                </p>
              </div>
              <USwitch
                v-model="rssWebhookNotificationEnabled"
                :loading="rssWebhookNotificationLoading"
              />
            </div>
          </div>
        </UPageCard>

        <UPageCard :ui="{ body: 'space-y-4' }">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold text-default">RSS feeds</h2>
              <p class="text-sm text-muted">Manage external feed links separately from bookmarks</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <RefreshButton :loading="loading" @click="refreshFeeds" />
              <UButton label="Register" icon="i-lucide-plus" size="sm" @click="openCreateModal" />
            </div>
          </div>

          <div
            class="flex flex-col gap-3 border-b border-default pb-4 md:flex-row md:items-center md:justify-between"
          >
            <p class="text-xs uppercase tracking-[0.08em] text-muted">
              Total {{ feedList.total }} feeds · Page {{ feedList.page }} of {{ pageCount }}
            </p>
            <div class="flex items-center gap-2">
              <UButton
                size="sm"
                variant="ghost"
                color="neutral"
                :disabled="page <= 1 || loading"
                @click="setPage(page - 1)"
              >
                Prev
              </UButton>
              <template
                v-for="(item, index) in paginationItems"
                :key="`${item.type}-${index}-${item.type === 'page' ? item.value : 'ellipsis'}`"
              >
                <UButton
                  v-if="item.type === 'page'"
                  size="sm"
                  :color="item.value === page ? 'primary' : 'neutral'"
                  :variant="item.value === page ? 'solid' : 'ghost'"
                  :disabled="loading"
                  @click="setPage(item.value)"
                >
                  {{ item.label }}
                </UButton>
                <UButton v-else size="sm" variant="ghost" color="neutral" disabled> ... </UButton>
              </template>
              <UButton
                size="sm"
                variant="ghost"
                color="neutral"
                :disabled="page >= pageCount || loading"
                @click="setPage(page + 1)"
              >
                Next
              </UButton>
            </div>
          </div>

          <div v-if="feedList.items.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <RSSFeedCard
              v-for="feed in feedList.items"
              :key="feed.id"
              :feed="feed"
              :to="`/rss/${feed.id}`"
              :running="executingFeedId === feed.id"
              @edit="openEditModal"
              @execute="executeFeed"
              @toggle-webhook="toggleWebhookNotification"
              @remove="askDelete"
            />
          </div>

          <div
            v-else
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            <p v-if="loading">Loading RSS feeds...</p>
            <p v-else-if="loadError">
              {{ loadError }}
            </p>
            <p v-else>No RSS feeds yet.</p>
          </div>
        </UPageCard>

        <UPageCard :ui="{ body: 'space-y-4' }">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold text-default">Custom news sites</h2>
              <p class="text-sm text-muted">
                Scrape news pages that do not publish RSS or Atom feeds
              </p>
            </div>
            <div class="flex items-center gap-2">
              <RefreshButton :loading="newsLoading" @click="loadNewsSites(true)" />
              <UButton
                label="Register custom site"
                icon="i-lucide-wand-sparkles"
                size="sm"
                :disabled="!llmConfigured"
                @click="openNewsCreateModal"
              />
            </div>
          </div>

          <UAlert
            v-if="!llmConfigured"
            title="Configure an LLM before registering a custom site"
            description="The LLM analyzes the site's HTML and creates a tested scraping configuration."
            color="warning"
            variant="soft"
          >
            <template #actions>
              <UButton to="/settings" size="xs" color="warning" variant="soft">
                Open settings
              </UButton>
            </template>
          </UAlert>

          <div v-if="newsSites.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <NewsSiteCard
              v-for="site in newsSites"
              :key="site.id"
              :site="site"
              :running="executingNewsSiteId === site.id"
              @edit="openNewsEditModal"
              @execute="executeNewsSite"
              @toggle-webhook="toggleNewsWebhookNotification"
              @remove="askDeleteNewsSite"
            />
          </div>
          <div
            v-else
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            <p v-if="newsLoading">Loading custom news sites...</p>
            <p v-else>No custom news sites yet.</p>
          </div>
        </UPageCard>

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

        <NewsSiteEditorModal
          v-model:open="newsModalOpen"
          :form="newsForm"
          :webhooks="webhooks"
          :title="newsForm.id ? 'Edit custom news site' : 'Register custom news site'"
          :description="newsForm.id ? 'Update the selected custom source.' : 'Analyze the site HTML and save a tested scraping configuration.'"
          :saving="newsSaving"
          :error="newsSaveError"
          @save="saveNewsSite"
        />

        <DeleteConfirmModal
          v-model:open="deleteOpen"
          title="Delete RSS feed"
          :subject="pendingFeed?.title"
          confirm-label="Delete feed"
          :loading="deleting"
          @cancel="pendingFeed = null"
          @confirm="confirmDelete"
        />

        <DeleteConfirmModal
          v-model:open="newsDeleteOpen"
          title="Delete custom news site"
          :subject="pendingNewsSite?.title"
          confirm-label="Delete site"
          :loading="newsDeleting"
          @cancel="pendingNewsSite = null"
          @confirm="confirmDeleteNewsSite"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type {
  LLMSettingsResponse,
  NewsSiteExecuteResponse,
  NewsSiteListResponse,
  NewsSiteResponse,
  RSSFeedExecuteResponse,
  RSSFeedListResponse,
  RSSFeedResponse,
  SettingsRssExecutionResponse,
  SettingsRssWebhookNotificationResponse,
  SettingsWebhookListResponse,
  SettingsWebhookResponse,
} from "~/types";

type PaginationItem = { type: "page"; label: string; value: number } | { type: "ellipsis" };

const { request } = useBookmarkApi();
const toast = useSingleToast();
const { refresh: refreshSidebarCatalog } = useSidebarCatalog();

const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const rssExecutionLoading = ref(false);
const rssExecutionSaving = ref(false);
const rssWebhookNotificationLoading = ref(false);
const rssWebhookNotificationSaving = ref(false);
const executingFeedId = ref<number | null>(null);
const loadError = ref("");
const modalOpen = ref(false);
const deleteOpen = ref(false);
const pendingFeed = ref<RSSFeedResponse | null>(null);
const newsLoading = ref(false);
const newsSaving = ref(false);
const newsSaveError = ref("");
const newsDeleting = ref(false);
const newsModalOpen = ref(false);
const newsDeleteOpen = ref(false);
const executingNewsSiteId = ref<number | null>(null);
const pendingNewsSite = ref<NewsSiteResponse | null>(null);
const newsSites = ref<NewsSiteResponse[]>([]);
const llmConfigured = ref(false);
const feedList = ref<RSSFeedListResponse>({
  items: [],
  total: 0,
  page: 1,
  per_page: 20,
  total_pages: 0,
});
const page = ref(1);
const webhooks = ref<SettingsWebhookResponse[]>([]);
const feedForm = reactive({
  id: "",
  title: "",
  url: "",
  description: "",
  webhookIds: [] as number[],
});
const newsForm = reactive({
  id: "",
  title: "",
  url: "",
  description: "",
  webhookIds: [] as number[],
  reanalyze: false,
});
const rssExecutionEnabled = ref(false);
const rssWebhookNotificationEnabled = ref(false);

const pageCount = computed(() => Math.max(feedList.value.total_pages, 1));
const paginationItems = computed<PaginationItem[]>(() => {
  const total = pageCount.value;
  const current = page.value;
  if (total <= 5) {
    return Array.from({ length: total }, (_, index) => ({
      type: "page" as const,
      label: String(index + 1),
      value: index + 1,
    }));
  }
  const pages = new Set<number>([1, total, current]);
  if (current > 1) pages.add(current - 1);
  if (current < total) pages.add(current + 1);
  return Array.from({ length: total }, (_, index) => index + 1)
    .filter((value) => pages.has(value))
    .reduce<PaginationItem[]>((items, value, index, arr) => {
      items.push({ type: "page", label: String(value), value });
      const next = arr[index + 1];
      if (next && next - value > 1) items.push({ type: "ellipsis" });
      return items;
    }, []);
});

const openCreateModal = () => {
  feedForm.id = "";
  feedForm.url = "";
  feedForm.title = "";
  feedForm.description = "";
  feedForm.webhookIds = [];
  modalOpen.value = true;
};

const openEditModal = (feed: RSSFeedResponse) => {
  feedForm.id = String(feed.id);
  feedForm.url = feed.url;
  feedForm.title = feed.title;
  feedForm.description = feed.description || "";
  feedForm.webhookIds = [...feed.webhook_ids];
  modalOpen.value = true;
};

const closeModal = () => {
  modalOpen.value = false;
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

const loadLlmStatus = async () => {
  try {
    await request<LLMSettingsResponse>("/settings/llm");
    llmConfigured.value = true;
  } catch {
    llmConfigured.value = false;
  }
};

const loadNewsSites = async (showToast = false) => {
  newsLoading.value = true;
  try {
    const response = await request<NewsSiteListResponse>("/news-sites?per_page=100");
    newsSites.value = response.items;
    if (showToast) {
      toast.show({
        title: "Custom news sites refreshed.",
        color: "success",
        icon: "i-lucide-check",
      });
    }
  } catch (err) {
    toast.show({
      title: "Failed to load custom news sites.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    newsLoading.value = false;
  }
};

const resetNewsForm = () => {
  newsForm.id = "";
  newsForm.title = "";
  newsForm.url = "";
  newsForm.description = "";
  newsForm.webhookIds = [];
  newsForm.reanalyze = false;
};

const openNewsCreateModal = () => {
  resetNewsForm();
  newsSaveError.value = "";
  newsModalOpen.value = true;
};

const openNewsEditModal = (site: NewsSiteResponse) => {
  newsSaveError.value = "";
  newsForm.id = String(site.id);
  newsForm.title = site.title;
  newsForm.url = site.url;
  newsForm.description = site.description || "";
  newsForm.webhookIds = [...site.webhook_ids];
  newsForm.reanalyze = false;
  newsModalOpen.value = true;
};

const saveNewsSite = async () => {
  const url = newsForm.url.trim();
  const title = newsForm.title.trim();
  if (!url || (newsForm.id && !title)) {
    newsSaveError.value = newsForm.id ? "URL and title are required." : "URL is required.";
    toast.show({
      title: newsForm.id ? "URL and title are required." : "URL is required.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return;
  }
  newsSaveError.value = "";
  newsSaving.value = true;
  try {
    const body = {
      url,
      ...(title ? { title } : {}),
      description: newsForm.description.trim() || null,
      webhook_ids: newsForm.webhookIds,
      ...(newsForm.id ? { reanalyze: newsForm.reanalyze } : {}),
    };
    await request(newsForm.id ? `/news-sites/${newsForm.id}` : "/news-sites", {
      method: newsForm.id ? "PATCH" : "POST",
      body: JSON.stringify(body),
    });
    const wasEditing = Boolean(newsForm.id);
    newsSaveError.value = "";
    newsModalOpen.value = false;
    resetNewsForm();
    await Promise.all([loadNewsSites(), refreshSidebarCatalog(true)]);
    toast.show({
      title: wasEditing
        ? "Custom news site updated."
        : "Custom news site analyzed, tested, and registered.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    newsSaveError.value =
      err instanceof Error ? err.message : "The custom news site could not be analyzed.";
    toast.show({
      title: newsForm.id
        ? "Failed to update custom news site."
        : "Failed to register custom news site.",
      description: newsSaveError.value,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    newsSaving.value = false;
  }
};

const executeNewsSite = async (site: NewsSiteResponse) => {
  executingNewsSiteId.value = site.id;
  try {
    const result = await request<NewsSiteExecuteResponse>(`/news-sites/${site.id}/execute`, {
      method: "POST",
    });
    toast.show({
      title: "Custom news site executed.",
      description: result.message ?? `Delivered to ${result.delivered_count} webhook(s).`,
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to execute custom news site.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    executingNewsSiteId.value = null;
  }
};

const toggleNewsWebhookNotification = async (site: NewsSiteResponse) => {
  try {
    const updated = await request<NewsSiteResponse>(`/news-sites/${site.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        notify_webhook_enabled: !site.notify_webhook_enabled,
      }),
    });
    newsSites.value = newsSites.value.map((item) => (item.id === updated.id ? updated : item));
    toast.show({
      title: updated.notify_webhook_enabled
        ? "Custom-site notifications enabled."
        : "Custom-site notifications disabled.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to update custom-site notifications.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

const askDeleteNewsSite = (site: NewsSiteResponse) => {
  pendingNewsSite.value = site;
  newsDeleteOpen.value = true;
};

const confirmDeleteNewsSite = async () => {
  if (!pendingNewsSite.value) return;
  newsDeleting.value = true;
  try {
    await request(`/news-sites/${pendingNewsSite.value.id}`, { method: "DELETE" });
    pendingNewsSite.value = null;
    newsDeleteOpen.value = false;
    await Promise.all([loadNewsSites(), refreshSidebarCatalog(true)]);
    toast.show({
      title: "Custom news site deleted.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to delete custom news site.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    newsDeleting.value = false;
  }
};

const loadRssExecution = async () => {
  rssExecutionLoading.value = true;
  try {
    const response = await request<SettingsRssExecutionResponse>("/settings/rss-execution");
    rssExecutionEnabled.value = response.enabled;
  } catch (err) {
    toast.show({
      title: "Failed to load RSS execution setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    rssExecutionLoading.value = false;
  }
};

const loadRssWebhookNotification = async () => {
  rssWebhookNotificationLoading.value = true;
  try {
    const response = await request<SettingsRssWebhookNotificationResponse>(
      "/settings/rss-webhook-notification",
    );
    rssWebhookNotificationEnabled.value = response.enabled;
  } catch (err) {
    toast.show({
      title: "Failed to load RSS webhook notification setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    rssWebhookNotificationLoading.value = false;
  }
};

watch(rssExecutionEnabled, async (enabled, previous) => {
  if (rssExecutionLoading.value || enabled === previous) return;
  rssExecutionSaving.value = true;
  try {
    const response = await request<SettingsRssExecutionResponse>("/settings/rss-execution", {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    });
    rssExecutionEnabled.value = response.enabled;
    toast.show({
      title: response.enabled
        ? "RSS periodic execution enabled."
        : "RSS periodic execution disabled.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    rssExecutionEnabled.value = previous;
    toast.show({
      title: "Failed to update RSS execution setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    rssExecutionSaving.value = false;
  }
});

watch(rssWebhookNotificationEnabled, async (enabled, previous) => {
  if (rssWebhookNotificationLoading.value || enabled === previous) return;
  rssWebhookNotificationSaving.value = true;
  try {
    const response = await request<SettingsRssWebhookNotificationResponse>(
      "/settings/rss-webhook-notification",
      {
        method: "PUT",
        body: JSON.stringify({ enabled }),
      },
    );
    rssWebhookNotificationEnabled.value = response.enabled;
    toast.show({
      title: response.enabled
        ? "RSS webhook notifications enabled."
        : "RSS webhook notifications disabled.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    rssWebhookNotificationEnabled.value = previous;
    toast.show({
      title: "Failed to update RSS webhook notification setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    rssWebhookNotificationSaving.value = false;
  }
});

type LoadToastKind = "loaded" | "refreshed";

const loadFeeds = async (showToast = true, toastKind: LoadToastKind = "loaded") => {
  loading.value = true;
  loadError.value = "";
  try {
    const response = await request<RSSFeedListResponse>(`/rss-feeds?page=${page.value}`);
    feedList.value = response;
    page.value = response.page;
    if (showToast) {
      toast.show({
        title: toastKind === "loaded" ? "RSS feeds loaded." : "RSS feeds refreshed.",
        color: "success",
        icon: "i-lucide-check",
      });
    }
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load RSS feeds.";
    toast.show({
      title: "Failed to load RSS feeds.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    loading.value = false;
  }
};

const refreshFeeds = async () => {
  await loadFeeds(true, "refreshed");
};

const setPage = async (nextPage: number) => {
  page.value = Math.min(Math.max(nextPage, 1), pageCount.value);
  await loadFeeds();
};

const saveFeed = async () => {
  const url = feedForm.url.trim();
  const title = feedForm.title.trim();
  if (!url || !title) {
    toast.show({
      title: "URL and title are required.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return;
  }

  saving.value = true;
  try {
    const body = {
      url,
      title,
      description: feedForm.description.trim() || null,
      webhook_ids: feedForm.webhookIds,
    };
    if (feedForm.id) {
      await request(`/rss-feeds/${feedForm.id}`, { method: "PATCH", body: JSON.stringify(body) });
      await refreshSidebarCatalog(true);
      toast.show({
        title: "RSS feed updated.",
        color: "success",
        icon: "i-lucide-check",
      });
    } else {
      await request("/rss-feeds", { method: "POST", body: JSON.stringify(body) });
      await refreshSidebarCatalog(true);
    }
    closeModal();
    await loadFeeds(false);
    toast.show({
      title: feedForm.id ? "RSS feed updated." : "RSS feed created.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: feedForm.id ? "Failed to update RSS feed." : "Failed to create RSS feed.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
};

const askDelete = (feed: RSSFeedResponse) => {
  pendingFeed.value = feed;
  deleteOpen.value = true;
};

const executeFeed = async (feed: RSSFeedResponse) => {
  executingFeedId.value = feed.id;
  try {
    const result = await request<RSSFeedExecuteResponse>(`/rss-feeds/${feed.id}/execute`, {
      method: "POST",
    });
    toast.show({
      title: "RSS feed executed.",
      description: result.message ?? `Delivered to ${result.delivered_count} webhook(s).`,
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to execute RSS feed.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    executingFeedId.value = null;
  }
};

const toggleWebhookNotification = async (feed: RSSFeedResponse) => {
  try {
    const updated = await request<RSSFeedResponse>(`/rss-feeds/${feed.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        notify_webhook_enabled: !feed.notify_webhook_enabled,
      }),
    });
    feedList.value.items = feedList.value.items.map((item) =>
      item.id === updated.id ? updated : item,
    );
    if (pendingFeed.value?.id === updated.id) {
      pendingFeed.value = updated;
    }
    await refreshSidebarCatalog(true);
    toast.show({
      title: updated.notify_webhook_enabled
        ? "Webhook notification enabled."
        : "Webhook notification disabled.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to update webhook notification setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

const confirmDelete = async () => {
  if (!pendingFeed.value) return;
  deleting.value = true;
  try {
    await request(`/rss-feeds/${pendingFeed.value.id}`, { method: "DELETE" });
    await refreshSidebarCatalog(true);
    deleteOpen.value = false;
    pendingFeed.value = null;
    await loadFeeds(false);
    toast.show({
      title: "RSS feed deleted.",
      color: "success",
      icon: "i-lucide-check",
    });
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

onMounted(async () => {
  await Promise.all([
    loadFeeds(),
    loadWebhooks(),
    loadRssExecution(),
    loadRssWebhookNotification(),
    loadLlmStatus(),
    loadNewsSites(),
  ]);
});
</script>
