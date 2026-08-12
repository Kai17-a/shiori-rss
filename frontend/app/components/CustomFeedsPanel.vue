<template>
  <UPageCard :ui="{ body: 'space-y-5' }">
    <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">LLM sources</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">Custom RSS</h2>
        <p class="mt-1 text-sm text-muted">
          Turn an article listing page into a feed using your configured LLM.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <RefreshButton :loading="loading" @click="loadSites(true)" />
        <UButton label="Add custom RSS" icon="i-lucide-wand-sparkles" @click="openCreate" />
      </div>
    </div>

    <div v-if="sites.items.length" class="grid gap-4 lg:grid-cols-2">
      <NewsSiteCard
        v-for="site in sites.items"
        :key="site.id"
        :site="site"
        :running="executingId === site.id"
        :notification-loading="updatingNotificationId === site.id"
        @edit="openEdit"
        @execute="executeSite"
        @toggle-webhook="toggleWebhook"
        @remove="askDelete"
      />
    </div>
    <div
      v-else
      class="rounded-3xl border border-dashed border-default bg-elevated/20 p-8 text-center"
    >
      <p class="font-semibold text-default">
        {{ loading ? "Loading custom RSS…" : "No custom RSS sources yet" }}
      </p>
      <p class="mt-2 text-sm text-muted">
        Register a page URL and the LLM will identify its article selectors.
      </p>
    </div>

    <NewsSiteEditorModal
      v-model:open="modalOpen"
      :form="form"
      :webhooks="webhooks"
      :title="form.id ? 'Edit custom RSS' : 'Register custom RSS'"
      description="The configured LLM analyzes the page and verifies article extraction."
      :saving="saving"
      :error="saveError"
      @save="saveSite"
    />

    <DeleteConfirmModal
      v-model:open="deleteOpen"
      title="Delete custom RSS"
      :subject="pendingSite?.title"
      confirm-label="Delete source"
      :loading="deleting"
      @cancel="pendingSite = null"
      @confirm="confirmDelete"
    />
  </UPageCard>
</template>

<script setup lang="ts">
import type {
  NewsSiteExecuteResponse,
  NewsSiteListResponse,
  NewsSiteResponse,
  SettingsWebhookResponse,
} from "~/types";

defineProps<{ webhooks: SettingsWebhookResponse[] }>();

const { request } = useApi();
const toast = useSingleToast();
const { refresh: refreshSidebarCatalog } = useSidebarCatalog();
const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const executingId = ref<number | null>(null);
const updatingNotificationId = ref<number | null>(null);
const modalOpen = ref(false);
const deleteOpen = ref(false);
const saveError = ref("");
const pendingSite = ref<NewsSiteResponse | null>(null);
const sites = ref<NewsSiteListResponse>({
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

const resetForm = () => {
  form.id = "";
  form.title = "";
  form.url = "";
  form.description = "";
  form.webhookIds = [];
  form.reanalyze = false;
  form.iconUrl = "";
  form.iconFile = null;
  form.existingIconUrl = "";
  form.removeIcon = false;
  form.configurationMode = "ai";
  form.itemSelector = "";
  form.titleSelector = "";
  form.linkSelector = "";
  form.linkAttribute = "href";
  form.summarySelector = "";
  form.publishedSelector = "";
  form.publishedAttribute = "";
  saveError.value = "";
};

const openCreate = () => {
  resetForm();
  modalOpen.value = true;
};

const openEdit = (site: NewsSiteResponse) => {
  form.id = String(site.id);
  form.title = site.title;
  form.url = site.url;
  form.description = site.description || "";
  form.webhookIds = [...site.webhook_ids];
  form.reanalyze = false;
  form.iconUrl = site.icon_uploaded ? "" : (site.icon_url || "");
  form.iconFile = null;
  form.existingIconUrl = site.icon_url || "";
  form.removeIcon = false;
  form.configurationMode = site.configuration_mode;
  form.itemSelector = site.scrape_config?.item_selector || "";
  form.titleSelector = site.scrape_config?.title_selector || "";
  form.linkSelector = site.scrape_config?.link_selector || "";
  form.linkAttribute = site.scrape_config?.link_attribute || "href";
  form.summarySelector = site.scrape_config?.summary_selector || "";
  form.publishedSelector = site.scrape_config?.published_selector || "";
  form.publishedAttribute = site.scrape_config?.published_attribute || "";
  saveError.value = "";
  modalOpen.value = true;
};

const loadSites = async (showToast = false) => {
  loading.value = true;
  try {
    sites.value = await request<NewsSiteListResponse>("/news-sites");
    if (showToast) {
      toast.show({ title: "Custom RSS refreshed.", color: "success", icon: "i-lucide-check" });
    }
  } catch (error) {
    toast.show({
      title: "Failed to load custom RSS.",
      description: error instanceof Error ? error.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    loading.value = false;
  }
};

const saveSite = async () => {
  if (!form.url.trim()) {
    saveError.value = "Page URL is required.";
    return;
  }
  if (
    form.configurationMode === "manual"
    && (!form.itemSelector.trim() || !form.titleSelector.trim() || !form.linkSelector.trim())
  ) {
    saveError.value = "Item, title, and link selectors are required in manual mode.";
    return;
  }
  saving.value = true;
  saveError.value = "";
  try {
    const body = {
      url: form.url.trim(),
      title: form.title.trim() || null,
      description: form.description.trim() || null,
      webhook_ids: form.webhookIds,
      ...(form.id ? { reanalyze: form.reanalyze } : {}),
      ...(form.iconUrl.trim() ? { icon_url: form.iconUrl.trim() } : {}),
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
    };
    const saved = await request<NewsSiteResponse>(form.id ? `/news-sites/${form.id}` : "/news-sites", {
      method: form.id ? "PATCH" : "POST",
      body: JSON.stringify(body),
    });
    if (form.iconFile) {
      const iconBody = new FormData();
      iconBody.append("file", form.iconFile);
      iconBody.append("public_url", `${window.location.origin}/api/news-sites/${saved.id}/icon`);
      await request(`/news-sites/${saved.id}/icon`, { method: "PUT", body: iconBody });
    } else if (form.removeIcon && form.id) {
      await request(`/news-sites/${saved.id}/icon`, { method: "DELETE" });
    }
    modalOpen.value = false;
    await Promise.all([loadSites(), refreshSidebarCatalog(true)]);
    toast.show({
      title: form.id ? "Custom RSS updated." : "Custom RSS created.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : "Custom RSS analysis failed.";
  } finally {
    saving.value = false;
  }
};

const executeSite = async (site: NewsSiteResponse) => {
  executingId.value = site.id;
  try {
    const result = await request<NewsSiteExecuteResponse>(`/news-sites/${site.id}/execute`, {
      method: "POST",
    });
    toast.show({
      title: "Custom RSS fetched.",
      description: result.message || undefined,
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (error) {
    toast.show({
      title: "Failed to fetch custom RSS.",
      description: error instanceof Error ? error.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    executingId.value = null;
  }
};

const toggleWebhook = async (site: NewsSiteResponse) => {
  updatingNotificationId.value = site.id;
  try {
    const updated = await request<NewsSiteResponse>(`/news-sites/${site.id}`, {
      method: "PATCH",
      body: JSON.stringify({ notify_webhook_enabled: !site.notify_webhook_enabled }),
    });
    sites.value.items = sites.value.items.map((item) => item.id === updated.id ? updated : item);
  } catch (error) {
    toast.show({
      title: "Failed to update webhook notification setting.",
      description: error instanceof Error ? error.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    updatingNotificationId.value = null;
  }
};

const askDelete = (site: NewsSiteResponse) => {
  pendingSite.value = site;
  deleteOpen.value = true;
};

const confirmDelete = async () => {
  if (!pendingSite.value) return;
  deleting.value = true;
  try {
    await request(`/news-sites/${pendingSite.value.id}`, { method: "DELETE" });
    deleteOpen.value = false;
    pendingSite.value = null;
    await Promise.all([loadSites(), refreshSidebarCatalog(true)]);
    toast.show({ title: "Custom RSS deleted.", color: "success", icon: "i-lucide-check" });
  } finally {
    deleting.value = false;
  }
};

onMounted(() => loadSites());
</script>
