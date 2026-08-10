<template>
  <UDashboardPanel id="ai-data">
    <template #header>
      <PageHeaderActions title="AI analysis data">
        <UButton
          to="/settings?tab=llm"
          label="Analysis settings"
          icon="i-lucide-settings"
          color="neutral"
          variant="ghost"
        />
      </PageHeaderActions>
    </template>

    <template #body>
      <div class="mx-auto w-full max-w-7xl space-y-6 pb-10">
        <UPageCard :ui="{ body: 'space-y-5' }">
          <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">AI index</p>
              <h1 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">
                Analyzed articles
              </h1>
              <p class="mt-1 text-sm text-muted">
                Inspect the summaries and metadata saved by the article analysis batch.
              </p>
            </div>
            <RefreshButton :loading="loading" @click="loadAnalyses(true)" />
          </div>

          <div class="grid gap-3 border-b border-default pb-5 md:grid-cols-[minmax(0,1fr)_12rem_12rem]">
            <UInput
              v-model="search"
              icon="i-lucide-search"
              placeholder="Search articles, sources, or summaries"
              class="w-full"
            />
            <USelect v-model="sourceType" :items="sourceOptions" class="w-full" />
            <USelect v-model="status" :items="statusOptions" class="w-full" />
          </div>

          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-xs uppercase tracking-[0.08em] text-muted">
              {{ analyses.total }} records · Page {{ analyses.page }} of {{ pageCount }}
            </p>
            <div class="flex items-center gap-2">
              <UButton
                label="Prev"
                size="sm"
                color="neutral"
                variant="ghost"
                :disabled="analyses.page <= 1 || loading"
                @click="setPage(analyses.page - 1)"
              />
              <UButton
                label="Next"
                size="sm"
                color="neutral"
                variant="ghost"
                :disabled="analyses.page >= pageCount || loading"
                @click="setPage(analyses.page + 1)"
              />
            </div>
          </div>

          <div v-if="analyses.items.length" class="space-y-4">
            <article
              v-for="analysis in analyses.items"
              :key="analysis.id"
              class="space-y-4 rounded-2xl border border-default bg-elevated/30 p-5"
            >
              <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div class="min-w-0">
                  <a
                    :href="analysis.article_url"
                    target="_blank"
                    rel="noreferrer"
                    class="font-semibold text-highlighted hover:text-primary hover:underline"
                  >
                    {{ analysis.article_title }}
                  </a>
                  <p class="mt-1 text-sm text-muted">
                    {{ analysis.source_title }} · {{ formatDateTime(analysis.analyzed_at) }}
                  </p>
                </div>
                <div class="flex shrink-0 flex-wrap gap-2">
                  <UBadge
                    :color="analysis.status === 'completed' ? 'success' : 'error'"
                    variant="soft"
                  >
                    {{ analysis.status }}
                  </UBadge>
                  <UBadge color="neutral" variant="soft">
                    {{ analysis.source_type === 'rss' ? 'RSS feed' : 'Custom RSS' }}
                  </UBadge>
                </div>
              </div>

              <p v-if="analysis.ai_summary" class="text-sm leading-6 text-default">
                {{ analysis.ai_summary }}
              </p>
              <UAlert
                v-if="analysis.error_message"
                title="Analysis failed"
                :description="analysis.error_message"
                color="error"
                variant="soft"
              />

              <ul v-if="analysis.key_points.length" class="space-y-1 text-sm text-muted">
                <li v-for="point in analysis.key_points" :key="point" class="flex gap-2">
                  <span aria-hidden="true">-</span><span>{{ point }}</span>
                </li>
              </ul>

              <div v-if="analysis.topics.length || analysis.keywords.length || analysis.entities.length" class="flex flex-wrap gap-2">
                <UBadge v-for="topic in analysis.topics" :key="`topic-${topic}`" color="primary" variant="soft">
                  {{ topic }}
                </UBadge>
                <UBadge v-for="keyword in analysis.keywords" :key="`keyword-${keyword}`" color="neutral" variant="outline">
                  {{ keyword }}
                </UBadge>
                <UBadge v-for="entity in analysis.entities" :key="`entity-${entity}`" color="info" variant="soft">
                  {{ entity }}
                </UBadge>
              </div>

              <div class="flex flex-wrap gap-x-5 gap-y-1 border-t border-default pt-3 text-xs text-muted">
                <span>Model: {{ analysis.model }}</span>
                <span>Prompt: {{ analysis.prompt_version }}</span>
                <span>Tokens: {{ analysis.input_tokens }} in / {{ analysis.output_tokens }} out</span>
                <span>Attempts: {{ analysis.attempt_count }}</span>
              </div>
            </article>
          </div>

          <UEmpty
            v-else
            :icon="loading ? 'i-lucide-loader-circle' : 'i-lucide-database'"
            :title="loading ? 'Loading analysis data…' : 'No analysis data found'"
            :description="loadError || 'Run article analysis or broaden the current filters.'"
            :ui="{ leadingIcon: loading ? 'animate-spin' : '' }"
          />
        </UPageCard>
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type {
  AIAnalysisSourceType,
  AIAnalysisStatus,
  AIArticleAnalysisListResponse,
} from "~/types";

const { request } = useApi();
const toast = useSingleToast();
const loading = ref(false);
const loadError = ref("");
const search = ref("");
const sourceType = ref<AIAnalysisSourceType | "all">("all");
const status = ref<AIAnalysisStatus | "all">("all");
const page = ref(1);
const analyses = ref<AIArticleAnalysisListResponse>({
  items: [],
  total: 0,
  page: 1,
  per_page: 20,
  total_pages: 0,
});

const sourceOptions = [
  { label: "All sources", value: "all" },
  { label: "RSS feeds", value: "rss" },
  { label: "Custom RSS", value: "custom" },
];
const statusOptions = [
  { label: "All statuses", value: "all" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
];
const pageCount = computed(() => Math.max(analyses.value.total_pages, 1));

const formatDateTime = (value: string) => {
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`;
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(normalized),
  );
};

const loadAnalyses = async (showToast = false) => {
  loading.value = true;
  loadError.value = "";
  try {
    const params = new URLSearchParams({ page: String(page.value), per_page: "20" });
    if (search.value.trim()) params.set("q", search.value.trim());
    if (sourceType.value !== "all") params.set("source_type", sourceType.value);
    if (status.value !== "all") params.set("status", status.value);
    analyses.value = await request<AIArticleAnalysisListResponse>(
      `/ai/article-analyses?${params.toString()}`,
    );
    page.value = analyses.value.page;
    if (showToast) toast.show({ title: "AI analysis data refreshed.", color: "success" });
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "Failed to load AI analysis data.";
    toast.show({ title: "Failed to load AI analysis data.", description: loadError.value, color: "error" });
  } finally {
    loading.value = false;
  }
};

const setPage = async (nextPage: number) => {
  page.value = Math.min(Math.max(nextPage, 1), pageCount.value);
  await loadAnalyses();
};

watch([search, sourceType, status], async () => {
  page.value = 1;
  await loadAnalyses();
});

onMounted(() => loadAnalyses());
</script>
