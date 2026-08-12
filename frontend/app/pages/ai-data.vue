<template>
  <UDashboardPanel id="ai-data" class="min-w-0">
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
      <div class="mx-auto w-full min-w-0 max-w-7xl space-y-6 pb-10">
        <UPageCard
          class="w-full min-w-0 max-w-full overflow-hidden"
          :ui="{ body: 'w-full min-w-0 max-w-full space-y-5 overflow-hidden' }"
        >
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
            <div class="flex flex-wrap items-center gap-2">
              <RefreshButton :loading="loading" @click="loadAnalyses(true)" />
              <UButton
                :label="analysisRunning ? 'Analysis running' : 'Run analysis now'"
                aria-label="Run analysis now"
                icon="i-lucide-play"
                loading-icon="i-lucide-loader-circle"
                :loading="analysisRunning"
                :disabled="analysisRunning"
                @click="runAnalysis"
              />
            </div>
          </div>

          <UAlert
            v-if="analysisRunning"
            role="status"
            aria-live="polite"
            title="Article analysis is running"
            :description="analysisProgressDescription"
            color="info"
            variant="soft"
            icon="i-lucide-loader-circle"
            :ui="{ leadingIcon: 'animate-spin' }"
          />

          <div
            v-if="analysisRunning && analysisStatus.total > 0"
            class="space-y-3 rounded-2xl border border-default bg-elevated/30 p-4"
          >
            <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span class="font-semibold text-default">
                {{ analysisStatus.processed }} / {{ analysisStatus.total }} articles
              </span>
              <span class="text-muted">{{ analysisProgressPercent }}%</span>
            </div>
            <UProgress
              :model-value="analysisStatus.processed"
              :max="analysisStatus.total"
              color="primary"
              size="md"
              role="progressbar"
              aria-label="Article analysis progress"
              :aria-valuenow="analysisStatus.processed"
              aria-valuemin="0"
              :aria-valuemax="analysisStatus.total"
            />
            <p v-if="analysisStatus.current_article_title" class="truncate text-sm text-default">
              Current: {{ analysisStatus.current_article_title }}
            </p>
            <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
              <span>{{ analysisStatus.succeeded }} succeeded</span>
              <span>{{ analysisStatus.failed }} failed</span>
              <span>{{ analysisStatus.skipped_current }} already current</span>
              <span v-if="analysisStatus.daily_token_limit">
                {{ analysisStatus.tokens_used_today.toLocaleString() }} /
                {{ analysisStatus.daily_token_limit.toLocaleString() }} tokens today
              </span>
            </div>
          </div>

          <UAlert
            v-if="analysisRunError"
            role="alert"
            title="Article analysis stopped"
            :description="analysisRunError"
            color="error"
            variant="soft"
            icon="i-lucide-circle-alert"
          >
            <template #actions>
              <UButton
                label="Dismiss"
                color="error"
                variant="ghost"
                size="xs"
                @click="analysisRunError = ''"
              />
            </template>
          </UAlert>

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

          <div
            v-if="analyses.items.length"
            class="w-full min-w-0 max-w-full space-y-4 overflow-hidden"
          >
            <article
              v-for="analysis in analyses.items"
              :key="analysis.id"
              class="w-full min-w-0 max-w-full space-y-4 overflow-hidden rounded-2xl border border-default bg-elevated/30 p-4 sm:p-5"
            >
              <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div class="min-w-0 flex-1">
                  <a
                    :href="analysis.article_url"
                    target="_blank"
                    rel="noreferrer"
                    class="block max-w-full font-semibold text-highlighted [overflow-wrap:anywhere] hover:text-primary hover:underline"
                  >
                    {{ analysis.article_title }}
                  </a>
                  <p class="mt-1 max-w-full text-sm text-muted [overflow-wrap:anywhere]">
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

              <p
                v-if="analysis.ai_summary"
                class="w-full max-w-full whitespace-pre-wrap text-sm leading-6 text-default [overflow-wrap:anywhere]"
              >
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
                <li v-for="point in analysis.key_points" :key="point" class="flex min-w-0 gap-2">
                  <span aria-hidden="true">-</span>
                  <span class="min-w-0 [overflow-wrap:anywhere]">{{ point }}</span>
                </li>
              </ul>

              <div v-if="analysis.topics.length || analysis.keywords.length || analysis.entities.length" class="flex min-w-0 flex-wrap gap-2">
                <UBadge v-for="topic in analysis.topics" :key="`topic-${topic}`" class="max-w-full whitespace-normal text-left [overflow-wrap:anywhere]" color="primary" variant="soft">
                  {{ topic }}
                </UBadge>
                <UBadge v-for="keyword in analysis.keywords" :key="`keyword-${keyword}`" class="max-w-full whitespace-normal text-left [overflow-wrap:anywhere]" color="neutral" variant="outline">
                  {{ keyword }}
                </UBadge>
                <UBadge v-for="entity in analysis.entities" :key="`entity-${entity}`" class="max-w-full whitespace-normal text-left [overflow-wrap:anywhere]" color="info" variant="soft">
                  {{ entity }}
                </UBadge>
              </div>

              <div class="flex min-w-0 flex-wrap gap-x-5 gap-y-1 border-t border-default pt-3 text-xs text-muted">
                <span class="max-w-full [overflow-wrap:anywhere]">Model: {{ analysis.model }}</span>
                <span class="max-w-full [overflow-wrap:anywhere]">Prompt: {{ analysis.prompt_version }}</span>
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
  SettingsAIArticleAnalysisRunResponse,
  SettingsAIArticleAnalysisStatusResponse,
} from "~/types";

const { request } = useApi();
const toast = useSingleToast();
const loading = ref(false);
const analysisRunning = ref(false);
const analysisRequestRunning = ref(false);
const emptyAnalysisStatus = (): SettingsAIArticleAnalysisStatusResponse => ({
  running: false,
  total: 0,
  processed: 0,
  succeeded: 0,
  failed: 0,
  skipped_current: 0,
  current_article_title: null,
  tokens_used_today: 0,
  daily_token_limit: 0,
  started_at: null,
});
const analysisStatus = ref<SettingsAIArticleAnalysisStatusResponse>(emptyAnalysisStatus());
const analysisRunError = ref("");
let statusPoll: ReturnType<typeof setInterval> | undefined;
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
const analysisProgressPercent = computed(() => analysisStatus.value.total
  ? Math.round((analysisStatus.value.processed / analysisStatus.value.total) * 100)
  : 0);
const analysisProgressDescription = computed(() => analysisStatus.value.total
  ? `Analyzing saved articles: ${analysisStatus.value.processed} of ${analysisStatus.value.total} processed.`
  : "Preparing saved articles for analysis. This page updates automatically.");

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

const loadAnalysisStatus = async () => {
  try {
    const response = await request<SettingsAIArticleAnalysisStatusResponse>(
      "/settings/ai-article-analysis/status",
    );
    analysisStatus.value = response;
    analysisRunning.value = analysisRequestRunning.value || response.running;
  } catch {
    // Keep the last known state when a background status check fails.
  }
};

const runAnalysis = async () => {
  if (analysisRunning.value) return;
  analysisRunError.value = "";
  analysisRequestRunning.value = true;
  analysisRunning.value = true;
  try {
    const response = await request<SettingsAIArticleAnalysisRunResponse>(
      "/settings/ai-article-analysis/execute",
      { method: "POST" },
    );
    const description = `${response.succeeded} succeeded, ${response.failed} failed, ${response.skipped_current} already current.`;
    toast.show({
      title: response.stopped_by_token_limit
        ? "Analysis stopped at the daily token limit."
        : response.processed
          ? "Article analysis completed."
          : "All eligible articles are already analyzed.",
      description,
      color: response.failed || response.stopped_by_token_limit ? "warning" : "success",
      icon: response.failed || response.stopped_by_token_limit
        ? "i-lucide-triangle-alert"
        : "i-lucide-check",
    });
    await loadAnalyses();
  } catch (error) {
    analysisRunError.value =
      error instanceof Error ? error.message : "Article analysis stopped unexpectedly.";
    toast.show({
      title: "Failed to run article analysis.",
      description: analysisRunError.value,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    analysisRequestRunning.value = false;
    analysisRunning.value = false;
    analysisStatus.value = emptyAnalysisStatus();
  }
};

watch([search, sourceType, status], async () => {
  page.value = 1;
  await loadAnalyses();
});

onMounted(async () => {
  await Promise.all([loadAnalyses(), loadAnalysisStatus()]);
  statusPoll = setInterval(loadAnalysisStatus, 3000);
});

onBeforeUnmount(() => {
  if (statusPoll) clearInterval(statusPoll);
});
</script>
