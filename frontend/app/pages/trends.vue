<template>
  <UDashboardPanel id="it-trends" class="min-w-0">
    <template #header>
      <PageHeaderActions title="IT trends">
        <RefreshButton :loading="loading" @click="loadTrends(true)" />
      </PageHeaderActions>
    </template>

    <template #body>
      <div class="mx-auto w-full min-w-0 max-w-7xl space-y-6 pb-10">
        <UPageCard :ui="{ body: 'space-y-5' }">
          <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div class="max-w-3xl">
              <div class="flex flex-wrap items-center gap-2">
                <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                  Global technology signals
                </p>
                <UBadge
                  :label="trends.ai_summarized ? 'AI summarized' : 'Live ranking'"
                  :color="trends.ai_summarized ? 'primary' : 'neutral'"
                  variant="soft"
                  size="sm"
                />
              </div>
              <h1 class="mt-2 text-2xl font-bold tracking-tight text-highlighted">
                What the IT world is talking about
              </h1>
              <p class="mt-2 text-sm leading-6 text-muted">
                Live signals from Hacker News and GitHub are ranked by activity and recency,
                then grouped and summarized by your configured AI model.
              </p>
            </div>

            <UFormField label="Category" class="w-full sm:w-56">
              <USelect
                v-model="selectedCategory"
                :items="categoryOptions"
                aria-label="Filter IT trends by category"
                class="w-full"
              />
            </UFormField>
          </div>

          <div class="flex min-w-0 flex-wrap gap-x-5 gap-y-2 border-t border-default pt-4 text-xs text-muted">
            <span class="inline-flex items-center gap-1.5">
              <UIcon name="i-lucide-globe-2" class="size-3.5" />
              {{ trends.region }}
            </span>
            <span class="inline-flex items-center gap-1.5">
              <UIcon name="i-lucide-clock-3" class="size-3.5" />
              {{ trends.window_hours }}-hour window
            </span>
            <span v-if="trends.generated_at" class="inline-flex items-center gap-1.5">
              <UIcon name="i-lucide-refresh-cw" class="size-3.5" />
              Updated {{ formatDateTime(trends.generated_at) }}
            </span>
          </div>
        </UPageCard>

        <UAlert
          v-if="trends.stale"
          title="Showing the last successful update"
          description="External sources could not be refreshed. The cached ranking remains available."
          color="warning"
          variant="soft"
          icon="i-lucide-history"
        />

        <UAlert
          v-if="loadError"
          title="Could not load IT trends"
          :description="loadError"
          color="error"
          variant="soft"
          icon="i-lucide-circle-alert"
        >
          <template #actions>
            <UButton label="Try again" color="error" variant="soft" size="xs" @click="loadTrends()" />
          </template>
        </UAlert>

        <div v-if="loading && !trends.items.length" class="space-y-3" aria-live="polite">
          <USkeleton v-for="index in 4" :key="index" class="h-40 w-full rounded-2xl" />
        </div>

        <div
          v-else-if="filteredTrends.length"
          class="divide-y divide-default overflow-hidden rounded-2xl border border-default bg-default"
        >
          <article
            v-for="trend in filteredTrends"
            :key="trend.id"
            class="grid min-w-0 gap-4 p-4 sm:grid-cols-[3rem_minmax(0,1fr)] sm:p-5"
          >
            <div class="flex items-center gap-3 sm:block">
              <span class="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-lg font-bold text-primary">
                {{ trend.rank }}
              </span>
              <span class="text-xs font-medium text-muted sm:mt-2 sm:block sm:text-center">
                Score {{ trend.score }}
              </span>
            </div>

            <div class="min-w-0 space-y-4">
              <div class="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <UBadge :label="trend.category" color="neutral" variant="soft" size="sm" />
                    <UBadge
                      :label="momentumLabel(trend.momentum)"
                      :color="trend.momentum === 'surging' ? 'error' : trend.momentum === 'rising' ? 'warning' : 'neutral'"
                      variant="subtle"
                      size="sm"
                    />
                  </div>
                  <h2 class="mt-2 text-lg font-semibold leading-7 text-highlighted [overflow-wrap:anywhere]">
                    {{ trend.title }}
                  </h2>
                  <p class="mt-1 max-w-4xl text-sm leading-6 text-muted [overflow-wrap:anywhere]">
                    {{ trend.summary }}
                  </p>
                </div>

                <div class="flex shrink-0 gap-4 text-xs text-muted lg:text-right">
                  <span><strong class="block text-sm text-default">{{ trend.source_count }}</strong>sources</span>
                  <span><strong class="block text-sm text-default">{{ trend.mention_count }}</strong>reactions</span>
                </div>
              </div>

              <div class="flex min-w-0 flex-wrap gap-2">
                <UBadge
                  v-for="source in trend.sources"
                  :key="source"
                  :label="source"
                  color="neutral"
                  variant="outline"
                  size="sm"
                />
              </div>

              <div class="flex min-w-0 flex-wrap gap-x-4 gap-y-2 border-t border-default pt-3">
                <a
                  v-for="link in trend.related_links"
                  :key="`${trend.id}-${link.source}`"
                  :href="link.url"
                  target="_blank"
                  rel="noreferrer"
                  class="inline-flex max-w-full items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                >
                  <span class="truncate">{{ link.title }}</span>
                  <UIcon name="i-lucide-external-link" class="size-3.5 shrink-0" />
                </a>
              </div>
            </div>
          </article>
        </div>

        <div
          v-else-if="!loadError"
          class="grid min-h-56 place-items-center rounded-2xl border border-dashed border-default p-8 text-center"
        >
          <div>
            <UIcon name="i-lucide-radar" class="mx-auto size-7 text-muted" />
            <p class="mt-3 font-semibold text-default">No trends in this category</p>
            <p class="mt-1 text-sm text-muted">Choose another category or refresh the external sources.</p>
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { ITTrendMomentum, ITTrendResponse } from "~/types";
import { formatDateTime } from "~/utils/dateTime";

const { request } = useApi();

const emptyTrends = (): ITTrendResponse => ({
  generated_at: "",
  window_hours: 24,
  region: "Global",
  sources: [],
  ai_summarized: false,
  stale: false,
  items: [],
});

const trends = ref<ITTrendResponse>(emptyTrends());
const loading = ref(false);
const loadError = ref("");
const selectedCategory = ref("all");

const categoryOptions = computed(() => [
  { label: "All categories", value: "all" },
  ...Array.from(new Set(trends.value.items.map((trend) => trend.category)))
    .sort()
    .map((category) => ({ label: category, value: category })),
]);

const filteredTrends = computed(() => selectedCategory.value === "all"
  ? trends.value.items
  : trends.value.items.filter((trend) => trend.category === selectedCategory.value));

const momentumLabel = (momentum: ITTrendMomentum) => ({
  surging: "Surging",
  rising: "Rising",
  steady: "Steady",
})[momentum];

const loadTrends = async (force = false) => {
  loading.value = true;
  loadError.value = "";
  try {
    trends.value = await request<ITTrendResponse>(force ? "/it-trends/refresh" : "/it-trends", {
      method: force ? "POST" : "GET",
    });
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "The trends could not be loaded.";
  } finally {
    loading.value = false;
  }
};

onMounted(() => loadTrends());
</script>
