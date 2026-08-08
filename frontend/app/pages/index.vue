<template>
  <UDashboardPanel id="feeds">
    <template #header>
      <PageHeaderActions title="Feeds" />
    </template>

    <template #body>
      <div class="mx-auto w-full max-w-7xl space-y-6 pb-10">
        <UTabs
          v-model="activeFeedType"
          :items="feedTypeTabs"
          class="w-full"
          color="primary"
          variant="link"
          :content="false"
          :ui="{
            list: 'w-full border-b border-default',
            trigger: 'min-w-0 flex-1 px-3 py-3 sm:flex-none sm:px-6',
          }"
        />

        <UPageCard v-if="activeFeedType === 'rss'" :ui="{ body: 'space-y-5' }">
          <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Library</p>
              <h2 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">Your feeds</h2>
              <p class="mt-1 text-sm text-muted">Every source you follow, ready when you are.</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <RefreshButton :loading="loading" @click="refreshFeeds" />
              <UButton label="Add feed" icon="i-lucide-plus" @click="openCreateModal" />
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

          <div v-if="feedList.items.length" class="grid gap-4 lg:grid-cols-2">
            <RSSFeedCard
              v-for="feed in feedList.items"
              :key="feed.id"
              :feed="feed"
              :to="`/feeds/${feed.id}`"
              :running="executingFeedId === feed.id"
              @edit="openEditModal"
              @execute="executeFeed"
              @toggle-webhook="toggleWebhookNotification"
              @remove="askDelete"
            />
          </div>

          <div
            v-else
            class="grid min-h-64 place-items-center rounded-3xl border border-dashed border-default bg-elevated/20 p-8 text-center"
          >
            <div class="max-w-sm space-y-3">
              <span class="mx-auto grid size-12 place-items-center rounded-2xl bg-primary/10 text-primary">
                <UIcon :name="loading ? 'i-lucide-loader-circle' : 'i-lucide-radio-tower'" class="size-6" :class="{ 'animate-spin': loading }" />
              </span>
              <p class="font-semibold text-default">{{ loading ? 'Tuning in…' : loadError ? 'Could not load feeds' : 'Your feed library is empty' }}</p>
              <p class="text-sm text-muted">{{ loadError || 'Add an RSS or Atom URL to start following the web.' }}</p>
              <UButton v-if="!loading && !loadError" label="Add your first feed" icon="i-lucide-plus" @click="openCreateModal" />
            </div>
          </div>
        </UPageCard>

        <CustomFeedsPanel v-else :webhooks="webhooks" />

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
          :subject="pendingFeed?.title"
          confirm-label="Delete feed"
          :loading="deleting"
          @cancel="pendingFeed = null"
          @confirm="confirmDelete"
        />

      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type {
  RSSFeedExecuteResponse,
  RSSFeedListResponse,
  RSSFeedResponse,
  SettingsWebhookListResponse,
  SettingsWebhookResponse,
} from "~/types";

type PaginationItem = { type: "page"; label: string; value: number } | { type: "ellipsis" };
type FeedType = "rss" | "custom";

const { request } = useApi();
const toast = useSingleToast();
const { refresh: refreshSidebarCatalog } = useSidebarCatalog();

const activeFeedType = ref<FeedType>("rss");
const feedTypeTabs = [
  { label: "RSS feeds", value: "rss", icon: "i-lucide-rss" },
  { label: "Custom RSS", value: "custom", icon: "i-lucide-wand-sparkles" },
];

const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const executingFeedId = ref<number | null>(null);
const loadError = ref("");
const modalOpen = ref(false);
const deleteOpen = ref(false);
const pendingFeed = ref<RSSFeedResponse | null>(null);
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

type LoadToastKind = "loaded" | "refreshed";

const loadFeeds = async (showToast = false, toastKind: LoadToastKind = "loaded") => {
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
  await Promise.all([loadFeeds(), loadWebhooks()]);
});
</script>
