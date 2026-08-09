<template>
  <UDashboardPanel id="feed-detail">
    <template #header>
      <PageHeaderActions title="Feed" />
    </template>

    <template #body>
      <div class="mx-auto w-full max-w-6xl space-y-6 pb-10">
        <UPageCard class="overflow-hidden" :ui="{ body: 'feed-detail-hero' }">
          <UAlert
            v-if="state === 'error'"
            title="Failed to load RSS feed"
            :description="loadError"
            color="error"
            variant="soft"
          />

          <UAlert
            v-else-if="state === 'not-found'"
            title="RSS feed not found"
            description="The requested feed does not exist."
            color="warning"
            variant="soft"
          />

          <div v-else-if="feed" class="space-y-5">
            <DetailPageHeader>
              <template #title>
                <div class="flex items-center gap-3">
                  <span class="grid size-12 shrink-0 place-items-center rounded-2xl bg-primary text-inverted shadow-sm">
                    <UIcon name="i-lucide-rss" class="size-6" />
                  </span>
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Feed channel</p>
                    <h1 class="mt-1 text-3xl font-bold tracking-tight text-highlighted">{{ feed.title }}</h1>
                  </div>
                </div>
              </template>

              <template #description>
                <p v-if="feed.description" class="max-w-2xl text-sm leading-6 text-muted">
                  {{ feed.description }}
                </p>
                <p v-else class="text-sm text-muted">No description provided.</p>
              </template>

              <div class="flex flex-wrap items-center gap-3 pt-2">
                <a
                  :href="feed.url"
                  target="_blank"
                  rel="noreferrer"
                  class="inline-flex max-w-full items-center gap-2 rounded-full bg-elevated px-3 py-1.5 text-xs text-muted hover:text-primary"
                >
                  <UIcon name="i-lucide-external-link" class="size-3.5 shrink-0" />
                  <span class="truncate">{{ feed.url }}</span>
                </a>
                <UBadge
                  :color="feed.notify_webhook_enabled ? 'success' : 'neutral'"
                  variant="soft"
                  :icon="feed.notify_webhook_enabled ? 'i-lucide-bell-ring' : 'i-lucide-bell-off'"
                  :label="feed.notify_webhook_enabled ? 'Delivery enabled' : 'Delivery muted'"
                />
              </div>

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
            </DetailPageHeader>
          </div>
        </UPageCard>

        <UPageCard title="Find an article" description="Search this feed by title or published date" icon="i-lucide-search" :ui="{ body: 'space-y-4' }">
          <form class="grid gap-3 lg:grid-cols-[4fr_1fr]">
            <UInput v-model="searchTitle" placeholder="Search article title" />
            <UInputDate ref="inputDate" v-model="selectedPublishedRange" range>
              <template #trailing>
                <UPopover :reference="inputDate?.inputsRef[0]?.$el">
                  <UButton
                    color="neutral"
                    variant="link"
                    size="sm"
                    icon="i-lucide-calendar"
                    aria-label="Select a published date range"
                    class="px-0"
                  />

                  <template #content>
                    <UCalendar
                      v-model="calendarPublishedRange"
                      class="p-2"
                      :number-of-months="2"
                      range
                    />
                  </template>
                </UPopover>
              </template>
            </UInputDate>
          </form>
        </UPageCard>

        <UPageCard :ui="{ body: 'space-y-3' }">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Reading queue</p>
              <h2 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">Articles</h2>
              <p class="mt-1 text-sm text-muted">The latest entries discovered from this feed.</p>
            </div>
            <div class="flex items-center gap-2">
              <RefreshButton :loading="articlesLoading" @click="loadArticles(true)" />
            </div>
          </div>

          <div
            class="flex flex-col gap-3 border-b border-default pb-4 md:flex-row md:items-center md:justify-between"
          >
            <p class="text-xs uppercase tracking-[0.08em] text-muted">
              Total {{ articleList.total }} articles
            </p>
            <div class="flex items-center gap-2">
              <UButton
                size="sm"
                variant="ghost"
                color="neutral"
                :disabled="articlePage <= 1 || articlesLoading"
                @click="setArticlePage(articlePage - 1)"
              >
                Prev
              </UButton>
              <template
                v-for="(item, index) in articlePaginationItems"
                :key="`${item.type}-${index}-${item.type === 'page' ? item.value : 'ellipsis'}`"
              >
                <UButton
                  v-if="item.type === 'page'"
                  size="sm"
                  :color="item.value === articlePage ? 'primary' : 'neutral'"
                  :variant="item.value === articlePage ? 'solid' : 'ghost'"
                  :disabled="articlesLoading"
                  @click="setArticlePage(item.value)"
                >
                  {{ item.label }}
                </UButton>
                <UButton v-else size="sm" variant="ghost" color="neutral" disabled> ... </UButton>
              </template>
              <UButton
                size="sm"
                variant="ghost"
                color="neutral"
                :disabled="articlePage >= articlePageCount || articlesLoading"
                @click="setArticlePage(articlePage + 1)"
              >
                Next
              </UButton>
            </div>
          </div>

          <div v-if="articleList.items.length" class="divide-y divide-default overflow-hidden rounded-2xl border border-default bg-default">
            <article
              v-for="article in articleList.items"
              :key="article.id"
              class="group flex items-start gap-4 p-5 transition hover:bg-elevated/50"
            >
              <span class="mt-0.5 grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                <UIcon name="i-lucide-newspaper" class="size-4" />
              </span>
              <div class="min-w-0 flex-1 space-y-1.5">
              <a
                :href="article.url"
                target="_blank"
                rel="noreferrer"
                class="block text-base font-semibold leading-6 text-highlighted group-hover:text-primary"
              >
                {{ article.title || article.url }}
              </a>
              <p v-if="article.summary" class="line-clamp-3 text-sm leading-6 text-muted">
                {{ formatArticleSummary(article.summary) }}
              </p>
              <div class="flex flex-wrap items-center gap-2">
                <p class="flex items-center gap-1.5 text-xs text-muted">
                  <UIcon name="i-lucide-clock-3" class="size-3.5" />
                  Published {{ formatDateTime(article.published || article.created_at) }}
                </p>
                <UBadge
                  v-if="!article.webhook_notified"
                  label="Webhook pending"
                  icon="i-lucide-clock-arrow-up"
                  color="warning"
                  variant="soft"
                  size="sm"
                />
              </div>
              </div>
              <UIcon name="i-lucide-arrow-up-right" class="mt-1 size-4 shrink-0 text-dimmed transition group-hover:text-primary" />
            </article>
          </div>
          <div
            v-else
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            <p v-if="articlesLoading">Loading articles...</p>
            <p v-else-if="searchTitle || selectedPublishedRange?.start || selectedPublishedRange?.end">
              No articles match your search.
            </p>
            <p v-else>No articles recorded for this feed yet.</p>
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

        <DeleteConfirmModal
          v-model:open="deleteOpen"
          title="Delete RSS feed"
          :subject="feed?.title"
          confirm-label="Delete feed"
          :loading="deleting"
          @cancel="deleteOpen = false"
          @confirm="confirmDelete"
        />
      </div>
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
import { formatArticleSummary } from "~/utils/articleSummary";
import { formatDateTime } from "~/utils/dateTime";

type PaginationItem = { type: "page"; label: string; value: number } | { type: "ellipsis" };

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
const inputDate = useTemplateRef("inputDate");
const selectedPublishedRange = shallowRef<DateRange>();
const calendarPublishedRange = computed<DateRange | null>({
  get: () => selectedPublishedRange.value ?? null,
  set: (value) => {
    selectedPublishedRange.value = value ?? undefined;
  },
});
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
const articlePaginationItems = computed<PaginationItem[]>(() => {
  const total = articlePageCount.value;
  const current = articlePage.value;
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
  modalOpen.value = true;
};

const closeModal = () => {
  modalOpen.value = false;
  feedForm.id = "";
  feedForm.title = "";
  feedForm.url = "";
  feedForm.description = "";
  feedForm.webhookIds = [];
};

const saveFeed = async () => {
  const url = feedForm.url.trim();
  const title = feedForm.title.trim();
  if (!url || !title) return;

  saving.value = true;
  try {
    await request(`/rss-feeds/${feedForm.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        url,
        title,
        description: feedForm.description || null,
        webhook_ids: feedForm.webhookIds,
      }),
    });
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
