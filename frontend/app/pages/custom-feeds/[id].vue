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

        <ArticleHistoryPanel
          v-model:search-title="searchTitle"
          v-model:published-range="selectedPublishedRange"
          :items="articleList.items"
          :total="articleList.total"
          :current-page="articlePage"
          :total-pages="articleList.total_pages"
          :loading="articlesLoading"
          @page="setArticlePage"
          @refresh="loadArticles(true)"
        />

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
import type { DateRange } from "reka-ui";
import type {
  NewsSiteArticleListResponse,
  NewsSiteExecuteResponse,
  NewsSiteResponse,
  SettingsWebhookListResponse,
  SettingsWebhookResponse,
} from "~/types";

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
const selectedPublishedRange = shallowRef<DateRange>();
const articlePage = ref(1);
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
    articleList.value = await request<NewsSiteArticleListResponse>(
      `/news-sites/${route.params.id}/articles?${buildArticleQuery()}`,
    );
    articlePage.value = articleList.value.page;
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

const setArticlePage = async (nextPage: number) => {
  articlePage.value = Math.min(Math.max(nextPage, 1), articlePageCount.value);
  await loadArticles();
};

watch(searchTitle, async () => {
  articlePage.value = 1;
  await loadArticles();
});

watch(selectedPublishedRange, async () => {
  articlePage.value = 1;
  await loadArticles();
}, { deep: true });

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
