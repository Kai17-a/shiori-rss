<template>
  <UDashboardPanel id="news-site-detail">
    <template #header>
      <PageHeaderActions title="Custom RSS feed" />
    </template>

    <template #body>
      <div class="space-y-6">
        <UPageCard>
          <UAlert
            v-if="state === 'error'"
            title="Failed to load custom RSS feed"
            :description="loadError"
            color="error"
            variant="soft"
          />
          <UAlert
            v-else-if="state === 'not-found'"
            title="Custom RSS feed not found"
            description="The requested custom source does not exist."
            color="warning"
            variant="soft"
          />
          <DetailPageHeader v-else-if="site">
            <template #title>
              <div class="flex flex-wrap items-center gap-2">
                <h1 class="text-2xl font-semibold text-default">{{ site.title }}</h1>
                <UBadge color="info" variant="soft">LLM-assisted scraping</UBadge>
              </div>
            </template>
            <template #description>
              <p v-if="site.description" class="text-sm leading-6 text-default/90">
                {{ site.description }}
              </p>
              <p v-else class="text-sm text-muted">No description provided.</p>
            </template>
            <div class="space-y-1 pt-1">
              <p class="text-xs font-medium uppercase tracking-wide text-muted">Site URL</p>
              <a
                :href="site.url"
                target="_blank"
                rel="noreferrer"
                class="break-all text-sm text-primary hover:underline"
              >
                {{ site.url }}
              </a>
            </div>
            <template #actions>
              <IconButton
                label="Run"
                icon="i-lucide-play"
                color="primary"
                variant="soft"
                :loading="executing"
                @click="executeSite"
              />
              <IconButton label="Edit" icon="i-lucide-pencil" @click="openEditModal" />
              <IconButton
                label="Delete"
                icon="i-lucide-trash-2"
                color="error"
                variant="soft"
                @click="deleteOpen = true"
              />
            </template>
          </DetailPageHeader>
        </UPageCard>

        <UPageCard
          title="Articles"
          description="Articles extracted from this source are saved independently of webhook delivery."
          :ui="{ body: 'space-y-4' }"
        >
          <div class="flex flex-wrap items-center justify-between gap-3">
            <UInput
              v-model="searchTitle"
              placeholder="Search article titles"
              class="w-full sm:max-w-md"
            />
            <RefreshButton :loading="articlesLoading" @click="loadArticles(true)" />
          </div>

          <div v-if="articleList.items.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <article
              v-for="article in articleList.items"
              :key="article.id"
              class="space-y-2 rounded-2xl border border-default p-4"
            >
              <a
                :href="article.url"
                target="_blank"
                rel="noreferrer"
                class="block text-base font-semibold text-default hover:underline"
              >
                {{ article.title || article.url }}
              </a>
              <p v-if="article.summary" class="line-clamp-3 text-sm leading-6 text-muted">
                {{ formatArticleSummary(article.summary) }}
              </p>
              <p class="text-xs text-muted">
                Published {{ formatDateTime(article.published || article.created_at) }}
              </p>
            </article>
          </div>
          <div
            v-else
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            <p v-if="articlesLoading">Loading articles...</p>
            <p v-else>No articles recorded yet.</p>
          </div>

          <div class="flex items-center justify-between gap-3 border-t border-default pt-4">
            <p class="text-xs uppercase tracking-[0.08em] text-muted">
              Total {{ articleList.total }} articles · Page {{ articleList.page }} of
              {{ pageCount }}
            </p>
            <div class="flex gap-2">
              <UButton
                size="sm"
                variant="ghost"
                color="neutral"
                :disabled="page <= 1 || articlesLoading"
                @click="setPage(page - 1)"
              >
                Prev
              </UButton>
              <UButton
                size="sm"
                variant="ghost"
                color="neutral"
                :disabled="page >= pageCount || articlesLoading"
                @click="setPage(page + 1)"
              >
                Next
              </UButton>
            </div>
          </div>
        </UPageCard>

        <NewsSiteEditorModal
          v-model:open="modalOpen"
          :form="form"
          :webhooks="webhooks"
          title="Edit custom RSS feed"
          description="Changing the URL triggers a new LLM analysis and extraction test."
          :saving="saving"
          :error="saveError"
          @save="saveSite"
        />

        <DeleteConfirmModal
          v-model:open="deleteOpen"
          title="Delete custom RSS feed"
          :subject="site?.title"
          confirm-label="Delete site"
          :loading="deleting"
          @confirm="deleteSite"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type {
  NewsSiteArticleListResponse,
  NewsSiteExecuteResponse,
  NewsSiteResponse,
  SettingsWebhookListResponse,
  SettingsWebhookResponse,
} from "~/types";
import { formatArticleSummary } from "~/utils/articleSummary";
import { formatDateTime } from "~/utils/dateTime";

const route = useRoute();
const router = useRouter();
const { request } = useApi();
const toast = useSingleToast();
const { refresh: refreshSidebarCatalog } = useSidebarCatalog();

const state = ref<"loading" | "ready" | "error" | "not-found">("loading");
const loadError = ref("");
const site = ref<NewsSiteResponse | null>(null);
const webhooks = ref<SettingsWebhookResponse[]>([]);
const executing = ref(false);
const saving = ref(false);
const saveError = ref("");
const deleting = ref(false);
const articlesLoading = ref(false);
const modalOpen = ref(false);
const deleteOpen = ref(false);
const searchTitle = ref("");
const page = ref(1);
const articleList = ref<NewsSiteArticleListResponse>({
  items: [],
  total: 0,
  page: 1,
  per_page: 20,
  total_pages: 0,
});
const form = reactive({
  id: "",
  title: "",
  url: "",
  description: "",
  webhookIds: [] as number[],
  reanalyze: false,
});
const pageCount = computed(() => Math.max(articleList.value.total_pages, 1));

const loadSite = async () => {
  try {
    site.value = await request<NewsSiteResponse>(`/news-sites/${route.params.id}`);
    state.value = "ready";
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to load custom RSS feed.";
    loadError.value = message;
    state.value = message.includes("not found") ? "not-found" : "error";
  }
};

const loadWebhooks = async () => {
  try {
    webhooks.value = (await request<SettingsWebhookListResponse>("/settings/webhooks")).items;
  } catch (err) {
    toast.show({
      title: "Failed to load webhooks.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

const loadArticles = async (showToast = false) => {
  articlesLoading.value = true;
  try {
    const params = new URLSearchParams({ page: String(page.value) });
    if (searchTitle.value.trim()) params.set("q", searchTitle.value.trim());
    articleList.value = await request<NewsSiteArticleListResponse>(
      `/news-sites/${route.params.id}/articles?${params}`,
    );
    page.value = articleList.value.page;
    if (showToast) {
      toast.show({
        title: "Articles refreshed.",
        color: "success",
        icon: "i-lucide-check",
      });
    }
  } catch (err) {
    toast.show({
      title: "Failed to load articles.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    articlesLoading.value = false;
  }
};

const setPage = async (nextPage: number) => {
  page.value = Math.min(Math.max(nextPage, 1), pageCount.value);
  await loadArticles();
};

watch(searchTitle, async () => {
  page.value = 1;
  await loadArticles();
});

const openEditModal = () => {
  if (!site.value) return;
  saveError.value = "";
  form.id = String(site.value.id);
  form.title = site.value.title;
  form.url = site.value.url;
  form.description = site.value.description || "";
  form.webhookIds = [...site.value.webhook_ids];
  form.reanalyze = false;
  modalOpen.value = true;
};

const saveSite = async () => {
  if (!form.url.trim() || !form.title.trim()) {
    saveError.value = "URL and title are required.";
    return;
  }
  saveError.value = "";
  saving.value = true;
  try {
    site.value = await request<NewsSiteResponse>(`/news-sites/${route.params.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        url: form.url.trim(),
        title: form.title.trim(),
        description: form.description.trim() || null,
        webhook_ids: form.webhookIds,
        reanalyze: form.reanalyze,
      }),
    });
    saveError.value = "";
    modalOpen.value = false;
    await refreshSidebarCatalog(true);
    toast.show({
      title: "Custom RSS feed updated.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    saveError.value =
      err instanceof Error ? err.message : "The custom RSS feed could not be analyzed.";
    toast.show({
      title: "Failed to update custom RSS feed.",
      description: saveError.value,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
};

const executeSite = async () => {
  if (!site.value) return;
  executing.value = true;
  try {
    const result = await request<NewsSiteExecuteResponse>(
      `/news-sites/${site.value.id}/execute`,
      { method: "POST" },
    );
    await loadArticles();
    toast.show({
      title: "Custom RSS feed executed.",
      description: result.message ?? `Delivered to ${result.delivered_count} webhook(s).`,
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to execute custom RSS feed.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    executing.value = false;
  }
};

const deleteSite = async () => {
  if (!site.value) return;
  deleting.value = true;
  try {
    await request(`/news-sites/${site.value.id}`, { method: "DELETE" });
    await refreshSidebarCatalog(true);
    await router.push("/");
  } catch (err) {
    toast.show({
      title: "Failed to delete custom RSS feed.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    deleting.value = false;
  }
};

onMounted(async () => {
  await Promise.all([loadSite(), loadArticles(), loadWebhooks()]);
});
</script>
