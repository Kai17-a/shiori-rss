<template>
  <UDashboardPanel id="news-site-detail">
    <template #header>
      <PageHeaderActions title="Custom RSS feed" />
    </template>

    <template #body>
      <FeedDetailLayout
        :state="state"
        error-title="Failed to load custom RSS feed"
        :error-description="loadError"
        not-found-title="Custom RSS feed not found"
        not-found-description="The requested custom source does not exist."
      >
        <template #title>
          <div class="flex items-center gap-3">
            <UAvatar
              :src="site?.icon_url || undefined"
              :alt="site?.title || 'Custom RSS feed'"
              icon="i-lucide-sparkles"
              size="2xl"
              color="primary"
              class="shrink-0 rounded-2xl shadow-sm"
              :ui="{ icon: 'size-6' }"
            />
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Custom feed channel</p>
              <h1 class="mt-1 text-3xl font-bold tracking-tight text-highlighted">{{ site?.title }}</h1>
            </div>
          </div>
        </template>
        <template #description>
          <p v-if="site?.description" class="max-w-2xl text-sm leading-6 text-muted">
            {{ site.description }}
          </p>
          <p v-else class="text-sm text-muted">No description provided.</p>
        </template>
        <template #meta>
          <div class="flex flex-wrap items-center gap-3 pt-2">
            <a
              :href="site?.url"
              target="_blank"
              rel="noreferrer"
              class="inline-flex max-w-full items-center gap-2 rounded-full bg-elevated px-3 py-1.5 text-xs text-muted hover:text-primary"
            >
              <UIcon name="i-lucide-external-link" class="size-3.5 shrink-0" />
              <span class="truncate">{{ site?.url }}</span>
            </a>
            <UBadge
              color="info"
              variant="soft"
              icon="i-lucide-wand-sparkles"
              label="LLM-assisted scraping"
            />
          </div>
        </template>
        <template #actions>
          <IconButton
            size="sm"
            label="Fetch now"
            icon="i-lucide-refresh-cw"
            color="primary"
            variant="soft"
            :loading="executing"
            @click="executeSite"
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
          description="Choose AI setup or maintain the extraction selectors manually."
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
      </FeedDetailLayout>
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
  iconUrl: "",
  iconFile: null as File | null,
  existingIconUrl: "",
  removeIcon: false,
  configurationMode: "ai" as "ai" | "manual",
  itemSelector: "",
  titleSelector: "",
  linkSelector: "",
  linkAttribute: "href",
  summarySelector: "",
  publishedSelector: "",
  publishedAttribute: "",
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
  form.iconUrl = site.value.icon_uploaded ? "" : (site.value.icon_url || "");
  form.iconFile = null;
  form.existingIconUrl = site.value.icon_url || "";
  form.removeIcon = false;
  form.configurationMode = site.value.configuration_mode;
  form.itemSelector = site.value.scrape_config?.item_selector || "";
  form.titleSelector = site.value.scrape_config?.title_selector || "";
  form.linkSelector = site.value.scrape_config?.link_selector || "";
  form.linkAttribute = site.value.scrape_config?.link_attribute || "href";
  form.summarySelector = site.value.scrape_config?.summary_selector || "";
  form.publishedSelector = site.value.scrape_config?.published_selector || "";
  form.publishedAttribute = site.value.scrape_config?.published_attribute || "";
  modalOpen.value = true;
};

const saveSite = async () => {
  if (!form.url.trim() || !form.title.trim()) {
    saveError.value = "URL and title are required.";
    return;
  }
  if (
    form.configurationMode === "manual"
    && (!form.itemSelector.trim() || !form.titleSelector.trim() || !form.linkSelector.trim())
  ) {
    saveError.value = "Item, title, and link selectors are required in manual mode.";
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
        configuration_mode: form.configurationMode,
        ...(form.configurationMode === "manual" ? {
          scrape_config: {
            item_selector: form.itemSelector.trim(),
            title_selector: form.titleSelector.trim(),
            link_selector: form.linkSelector.trim(),
            link_attribute: form.linkAttribute.trim() || "href",
            summary_selector: form.summarySelector.trim() || null,
            published_selector: form.publishedSelector.trim() || null,
            published_attribute: form.publishedAttribute.trim() || null,
          },
        } : {}),
        ...(form.iconUrl.trim() ? { icon_url: form.iconUrl.trim() } : {}),
      }),
    });
    if (form.iconFile) {
      const body = new FormData();
      body.append("file", form.iconFile);
      body.append("public_url", `${window.location.origin}/api/news-sites/${site.value.id}/icon`);
      await request(`/news-sites/${site.value.id}/icon`, { method: "PUT", body });
      await loadSite();
    } else if (form.removeIcon) {
      await request(`/news-sites/${site.value.id}/icon`, { method: "DELETE" });
      await loadSite();
    }
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
