<template>
  <div class="space-y-6">
    <UPageCard
      title="Find an article"
      description="Search this feed by title or published date"
      icon="i-lucide-search"
      :ui="{ body: 'space-y-4' }"
    >
      <form class="grid gap-3 lg:grid-cols-[4fr_1fr]">
        <UInput v-model="searchTitle" placeholder="Search article title" />
        <UInputDate ref="inputDate" v-model="publishedRange" range>
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
          <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            Reading queue
          </p>
          <h2 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">Articles</h2>
          <p class="mt-1 text-sm text-muted">The latest entries discovered from this feed.</p>
        </div>
        <RefreshButton :loading="loading" @click="$emit('refresh')" />
      </div>

      <div
        class="flex flex-col gap-3 border-b border-default pb-4 md:flex-row md:items-center md:justify-between"
      >
        <p class="text-xs uppercase tracking-[0.08em] text-muted">Total {{ total }} articles</p>
        <ListPagination
          :page="currentPage"
          :total-pages="pageCount"
          :loading="loading"
          @update:page="$emit('page', $event)"
        />
      </div>

      <div
        v-if="items.length"
        class="divide-y divide-default overflow-hidden rounded-2xl border border-default bg-default"
      >
        <article
          v-for="article in items"
          :key="article.id"
          class="group flex items-start gap-4 p-5 transition hover:bg-elevated/50"
        >
          <span
            class="mt-0.5 grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary"
          >
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
          <UIcon
            name="i-lucide-arrow-up-right"
            class="mt-1 size-4 shrink-0 text-dimmed transition group-hover:text-primary"
          />
        </article>
      </div>
      <div
        v-else
        class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
      >
        <p v-if="loading">Loading articles...</p>
        <p v-else-if="hasFilters">No articles match your search.</p>
        <p v-else>No articles recorded for this feed yet.</p>
      </div>
    </UPageCard>
  </div>
</template>

<script setup lang="ts">
import type { DateRange } from "reka-ui";
import { formatArticleSummary } from "~/utils/articleSummary";
import { formatDateTime } from "~/utils/dateTime";

interface ArticleListItem {
  id: number;
  url: string;
  title: string | null;
  summary: string | null;
  published: string | null;
  created_at: string;
  webhook_notified: boolean;
}

const props = defineProps<{
  items: ArticleListItem[];
  total: number;
  currentPage: number;
  totalPages: number;
  loading: boolean;
}>();

defineEmits<{
  refresh: [];
  page: [page: number];
}>();

const searchTitle = defineModel<string>("searchTitle", { required: true });
const publishedRange = defineModel<DateRange | undefined>("publishedRange");
const inputDate = useTemplateRef("inputDate");
const calendarPublishedRange = computed<DateRange | null>({
  get: () => publishedRange.value ?? null,
  set: (value) => {
    publishedRange.value = value ?? undefined;
  },
});
const pageCount = computed(() => Math.max(props.totalPages, 1));
const hasFilters = computed(
  () => Boolean(searchTitle.value || publishedRange.value?.start || publishedRange.value?.end),
);
</script>
