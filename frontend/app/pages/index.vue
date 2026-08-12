<template>
  <UDashboardPanel id="home" class="min-w-0">
    <template #header>
      <PageHeaderActions title="Home" />
    </template>

    <template #body>
      <div class="mx-auto w-full min-w-0 max-w-7xl space-y-6 overflow-hidden pb-10">
        <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <UPageCard
            v-for="item in summaryItems"
            :key="item.label"
            :title="item.label"
            :icon="item.icon"
            variant="subtle"
          >
            <p class="text-3xl font-bold tracking-tight text-highlighted">{{ item.value }}</p>
          </UPageCard>
        </div>

        <UPageCard
          class="min-w-0 max-w-full overflow-hidden"
          :ui="{ body: 'min-w-0 max-w-full space-y-4 overflow-hidden' }"
        >
          <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
                {{ accessDateLabel }}
              </p>
              <h2 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">Last 24 hours</h2>
              <p class="mt-1 text-sm text-muted">Articles published or discovered in the previous 24 hours.</p>
            </div>
            <RefreshButton :loading="loading" @click="loadDashboard(true)" />
          </div>

          <UAlert
            v-if="loadError"
            title="Failed to load Home"
            :description="loadError"
            color="error"
            variant="soft"
          />

          <div
            v-else-if="dashboard.articles.length"
            class="divide-y divide-default overflow-hidden rounded-2xl border border-default bg-default"
          >
            <article
              v-for="article in dashboard.articles"
              :key="`${article.source_type}-${article.source_id}-${article.url}`"
              class="group flex min-w-0 items-start gap-3 p-4 transition hover:bg-elevated/50 sm:gap-4 sm:p-5"
            >
              <span class="mt-0.5 grid size-9 shrink-0 place-items-center overflow-hidden rounded-xl bg-primary/10 text-primary">
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
                <p v-if="article.summary" class="line-clamp-2 max-w-full text-sm leading-6 text-muted [overflow-wrap:anywhere]">
                  {{ article.summary }}
                </p>
                <div class="flex min-w-0 flex-wrap items-center gap-2">
                  <UButton
                    :to="sourcePath(article)"
                    :label="article.source_title"
                    :icon="article.source_type === 'rss' ? 'i-lucide-radio-tower' : 'i-lucide-sparkles'"
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

          <div
            v-else
            class="grid min-h-56 place-items-center rounded-2xl border border-dashed border-default p-8 text-center"
          >
            <div>
              <UIcon
                :name="loading ? 'i-lucide-loader-circle' : 'i-lucide-newspaper'"
                class="mx-auto size-7 text-muted"
                :class="{ 'animate-spin': loading }"
              />
              <p class="mt-3 font-semibold text-default">
                {{ loading ? "Loading recent news…" : "No news in the last 24 hours" }}
              </p>
              <p v-if="!loading" class="mt-1 text-sm text-muted">
                Fetch a feed to add articles to this rolling news window.
              </p>
            </div>
          </div>
        </UPageCard>
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { DashboardArticle, DashboardResponse } from "~/types";
import { formatDateTime } from "~/utils/dateTime";

const { request } = useApi();
const toast = useSingleToast();
const loading = ref(false);
const loadError = ref("");
const accessDate = new Date();
const accessDateLabel = new Intl.DateTimeFormat("en-US", {
  dateStyle: "full",
}).format(accessDate);
const dashboard = ref<DashboardResponse>({
  generated_at: accessDate.toISOString(),
  window_started_at: new Date(accessDate.getTime() - 24 * 60 * 60 * 1000).toISOString(),
  summary: {
    rss_feed_count: 0,
    custom_feed_count: 0,
    recent_article_count: 0,
    pending_notification_count: 0,
  },
  articles: [],
});

const summaryItems = computed(() => [
  { label: "RSS feeds", value: dashboard.value.summary.rss_feed_count, icon: "i-lucide-rss" },
  {
    label: "Custom RSS",
    value: dashboard.value.summary.custom_feed_count,
    icon: "i-lucide-wand-sparkles",
  },
  {
    label: "Recent articles",
    value: dashboard.value.summary.recent_article_count,
    icon: "i-lucide-newspaper",
  },
  {
    label: "Webhook pending",
    value: dashboard.value.summary.pending_notification_count,
    icon: "i-lucide-clock-arrow-up",
  },
]);

const sourcePath = (article: DashboardArticle) =>
  article.source_type === "rss"
    ? `/feeds/${article.source_id}`
    : `/custom-feeds/${article.source_id}`;

const loadDashboard = async (showToast = false) => {
  loading.value = true;
  loadError.value = "";
  try {
    dashboard.value = await request<DashboardResponse>("/dashboard");
    if (showToast) {
      toast.show({ title: "Home refreshed.", color: "success", icon: "i-lucide-check" });
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "Failed to load Home.";
  } finally {
    loading.value = false;
  }
};

onMounted(() => loadDashboard());
</script>
