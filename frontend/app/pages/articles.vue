<template>
  <UDashboardPanel id="articles" class="min-w-0">
    <template #header>
      <PageHeaderActions title="Articles" />
    </template>

    <template #body>
      <div class="mx-auto w-full min-w-0 max-w-7xl space-y-6 pb-10">
        <UPageCard
          class="w-full min-w-0 max-w-full overflow-hidden"
          :ui="{ body: 'w-full min-w-0 max-w-full space-y-5 overflow-hidden' }"
        >
          <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
                Article archive
              </p>
              <h1 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">All articles</h1>
              <p class="mt-1 text-sm text-muted">
                Every article ever fetched across your RSS feeds and custom sites.
              </p>
            </div>
            <RefreshButton :loading="loading" @click="loadArticles(true)" />
          </div>

          <div class="grid gap-3 border-b border-default pb-5 md:grid-cols-[minmax(0,1fr)_16rem]">
            <UInput
              v-model="search"
              icon="i-lucide-search"
              placeholder="Search article titles"
              class="w-full"
            />
            <USelectMenu
              v-model="sourceFilters"
              :items="sourceOptions"
              multiple
              clear
              placeholder="All sources"
              class="w-full"
            />
          </div>

          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-xs uppercase tracking-[0.08em] text-muted">
              {{ articles.total }} article{{ articles.total === 1 ? "" : "s" }} · Page
              {{ articles.page }} of {{ pageCount }}
            </p>
            <ListPagination
              :page="articles.page"
              :total-pages="pageCount"
              :loading="loading"
              @update:page="setPage"
            />
          </div>

          <UAlert
            v-if="loadError"
            title="Failed to load articles"
            :description="loadError"
            color="error"
            variant="soft"
          />

          <div
            v-else-if="articles.items.length"
            class="divide-y divide-default overflow-hidden rounded-2xl border border-default bg-default"
          >
            <article
              v-for="article in articles.items"
              :key="`${article.source_type}:${article.article_id}`"
              class="group flex min-w-0 items-start gap-3 p-4 transition hover:bg-elevated/50 sm:gap-4 sm:p-5"
            >
              <span
                class="mt-0.5 grid size-9 shrink-0 place-items-center overflow-hidden rounded-xl bg-primary/10 text-primary"
              >
                <img
                  v-if="article.source_icon_url"
                  :src="article.source_icon_url"
                  :alt="`${article.source_title} icon`"
                  class="block size-full object-cover"
                />
                <UIcon
                  v-else
                  :name="article.source_type === 'rss' ? 'i-lucide-rss' : 'i-lucide-wand-sparkles'"
                  class="size-4"
                />
              </span>
              <div class="min-w-0 flex-1 space-y-2">
                <a
                  :href="article.url"
                  target="_blank"
                  rel="noreferrer"
                  class="block max-w-full text-base font-semibold leading-6 text-highlighted [overflow-wrap:anywhere] group-hover:text-primary"
                >
                  {{ article.title || article.url }}
                </a>
                <p
                  v-if="article.summary"
                  class="line-clamp-2 max-w-full text-sm leading-6 text-muted [overflow-wrap:anywhere]"
                >
                  {{ formatArticleSummary(article.summary) }}
                </p>
                <div class="flex min-w-0 flex-wrap items-center gap-2">
                  <UButton
                    :to="sourcePath(article)"
                    :label="article.source_title"
                    :icon="
                      article.source_type === 'rss' ? 'i-lucide-radio-tower' : 'i-lucide-sparkles'
                    "
                    size="xs"
                    color="neutral"
                    variant="soft"
                    class="max-w-full"
                  />
                  <span class="text-xs text-muted">
                    {{ formatDateTime(article.published || article.created_at) }}
                  </span>
                  <UBadge
                    v-if="!article.webhook_notified"
                    label="Webhook pending"
                    color="warning"
                    variant="soft"
                    size="sm"
                  />
                </div>
              </div>
            </article>
          </div>

          <UEmpty
            v-else
            :icon="loading ? 'i-lucide-loader-circle' : 'i-lucide-newspaper'"
            :title="loading ? 'Loading articles…' : 'No articles found'"
            description="Fetch a feed, or broaden the current search and filters."
            :ui="{ leadingIcon: loading ? 'animate-spin' : '' }"
          />
        </UPageCard>
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { ArticleListItem, ArticleListResponse } from "~/types";
import { formatArticleSummary } from "~/utils/articleSummary";
import { formatDateTime } from "~/utils/dateTime";
import { refreshSidebarCatalogSafely } from "~/utils/sidebarCatalog";

const { request } = useApi();
const toast = useSingleToast();
const { rssFeeds, customFeeds, refresh: refreshSidebarCatalog } = useSidebarCatalog();

const loading = ref(false);
const loadError = ref("");
const search = ref("");
const sourceFilters = ref<Array<{ label: string; value: string }>>([]);
const page = ref(1);
const articles = ref<ArticleListResponse>({
  items: [],
  total: 0,
  page: 1,
  per_page: 20,
  total_pages: 0,
});

const sourceOptions = computed(() => [
  [
    { type: "label" as const, label: "RSS feeds" },
    ...rssFeeds.value.map((feed) => ({ label: feed.title, value: `rss:${feed.id}` })),
  ],
  [
    { type: "label" as const, label: "Custom RSS" },
    ...customFeeds.value.map((feed) => ({ label: feed.title, value: `custom:${feed.id}` })),
  ],
]);

const pageCount = computed(() => Math.max(articles.value.total_pages, 1));

const sourcePath = (article: ArticleListItem) =>
  article.source_type === "rss" ? `/feeds/${article.source_id}` : `/custom-feeds/${article.source_id}`;

let latestRequestId = 0;

const loadArticles = async (showToast = false) => {
  const requestId = ++latestRequestId;
  loading.value = true;
  loadError.value = "";
  try {
    const params = new URLSearchParams({ page: String(page.value), per_page: "20" });
    const query = search.value.trim();
    if (query) params.set("q", query);
    for (const source of sourceFilters.value) {
      params.append("source", source.value);
    }
    const result = await request<ArticleListResponse>(`/articles?${params.toString()}`);
    if (requestId !== latestRequestId) return;
    articles.value = result;
    page.value = result.page;
    if (showToast) {
      toast.show({ title: "Articles refreshed.", color: "success", icon: "i-lucide-check" });
    }
  } catch (error) {
    if (requestId !== latestRequestId) return;
    loadError.value = error instanceof Error ? error.message : "Failed to load articles.";
    toast.show({
      title: "Failed to load articles.",
      description: loadError.value,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    if (requestId === latestRequestId) loading.value = false;
  }
};

const setPage = async (nextPage: number) => {
  page.value = Math.min(Math.max(nextPage, 1), pageCount.value);
  await loadArticles();
};

let searchDebounceTimer: ReturnType<typeof setTimeout> | undefined;

watch(search, () => {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    page.value = 1;
    void loadArticles();
  }, 350);
});

watch(sourceFilters, async () => {
  page.value = 1;
  await loadArticles();
});

onMounted(async () => {
  await Promise.all([loadArticles(), refreshSidebarCatalogSafely(refreshSidebarCatalog)]);
});
</script>
