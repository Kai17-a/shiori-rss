<template>
  <UDashboardPanel id="settings">
    <template #header>
      <PageHeaderActions title="Preferences" />
    </template>

    <template #body>
      <div class="mx-auto w-full max-w-5xl space-y-6 pb-10">
        <UTabs
          v-model="activeCategory"
          :items="settingsCategories"
          class="w-full"
          color="primary"
          variant="link"
          :content="false"
          :ui="{
            list: 'w-full border-b border-default',
            trigger: 'min-w-0 flex-1 px-2 py-3 sm:px-4',
          }"
        />

        <UPageCard
          v-if="activeCategory === 'general'"
          title="Theme"
          description="Switch the app appearance between light, dark, and system"
          :ui="{ body: 'space-y-5' }"
        >
          <div class="space-y-3">
            <div>
              <p class="text-sm font-medium text-default">Appearance</p>
              <p class="text-sm text-muted">
                Changes apply immediately and are saved in your browser.
              </p>
            </div>

            <UTabs
              v-model="selectedTheme"
              :items="themeOptions"
              class="w-full max-w-sm"
              color="primary"
              variant="soft"
              orientation="horizontal"
              :ui="{
                list: 'bg-default/60 p-1 rounded-full gap-1',
                trigger:
                  'rounded-full px-4 py-2 text-sm font-medium text-muted transition-colors data-[state=active]:bg-primary data-[state=active]:text-inverted data-[state=active]:shadow-sm',
                indicator: 'hidden',
              }"
            />
          </div>
        </UPageCard>

        <UPageCard
          v-if="activeCategory === 'automation'"
          title="Automation"
          description="Control how Shiori Feed checks and delivers your feeds"
          icon="i-lucide-zap"
          :ui="{ body: 'grid gap-3 md:grid-cols-2' }"
        >
          <div class="flex items-start justify-between gap-4 rounded-2xl bg-elevated/60 p-4">
            <div class="space-y-1">
              <p class="text-sm font-semibold text-default">Scheduled refresh</p>
              <p class="text-sm text-muted">Check enabled feeds on the server schedule.</p>
            </div>
            <USwitch
              :model-value="rssExecutionEnabled"
              :loading="rssExecutionLoading || rssExecutionSaving"
              aria-label="Scheduled refresh"
              @update:model-value="setRssExecution"
            />
          </div>
          <div class="flex items-start justify-between gap-4 rounded-2xl bg-elevated/60 p-4">
            <div class="space-y-1">
              <p class="text-sm font-semibold text-default">Webhook delivery</p>
              <p class="text-sm text-muted">Send newly discovered articles to your channels.</p>
            </div>
            <USwitch
              :model-value="rssWebhookNotificationEnabled"
              :loading="rssWebhookNotificationLoading || rssWebhookNotificationSaving"
              aria-label="Webhook delivery"
              @update:model-value="setRssWebhookNotification"
            />
          </div>
        </UPageCard>

        <UPageCard
          v-if="activeCategory === 'llm'"
          title="LLM connection"
          description="Configure and verify an Ollama, vLLM, or OpenAI-compatible endpoint"
          :ui="{ body: 'space-y-5' }"
        >
          <UAlert
            v-if="!llmConfigured && !llmLoading"
            title="LLM settings are not configured"
            description="Test and save a connection to make it available to the application."
            color="warning"
            variant="soft"
          />

          <form class="grid gap-4 lg:grid-cols-2" @submit.prevent="saveLlmSettings">
            <UFormField label="Provider" required class="w-full">
              <USelect
                v-model="llmForm.provider"
                :items="llmProviderOptions"
                value-key="value"
                label-key="label"
                class="w-full"
              />
            </UFormField>

            <UFormField label="Model" required class="w-full">
              <UInput
                v-model="llmForm.model"
                class="w-full"
                placeholder="e.g. llama3.2 or gpt-4.1-mini"
              />
            </UFormField>

            <UFormField
              label="Base URL"
              required
              description="For vLLM and OpenAI-compatible servers, include the /v1 path."
              class="w-full lg:col-span-2"
            >
              <UInput
                v-model="llmForm.baseUrl"
                class="w-full"
                placeholder="http://127.0.0.1:11434"
              />
            </UFormField>

            <UFormField
              label="API key"
              :description="llmApiKeyDescription"
              class="w-full lg:col-span-2"
            >
              <UInput
                v-model="llmForm.apiKey"
                type="password"
                autocomplete="new-password"
                class="w-full"
                placeholder="Optional for local servers"
              />
            </UFormField>

            <UCheckbox
              v-if="llmSettings?.api_key_configured"
              v-model="llmForm.clearApiKey"
              label="Remove the saved API key"
              class="lg:col-span-2"
            />

            <div class="flex flex-wrap items-center gap-3 lg:col-span-2">
              <UButton
                type="button"
                color="warning"
                variant="ghost"
                icon="i-lucide-plug-zap"
                :loading="llmTesting"
                @click="testLlmSettings"
              >
                Test
              </UButton>
              <UButton type="submit" icon="i-lucide-save" :loading="llmSaving">
                Save LLM settings
              </UButton>
              <UButton
                v-if="llmConfigured"
                type="button"
                color="error"
                variant="ghost"
                icon="i-lucide-trash-2"
                @click="llmDeleteOpen = true"
              >
                Delete
              </UButton>
            </div>
          </form>
        </UPageCard>

        <UPageCard
          v-if="activeCategory === 'webhooks'"
          title="Webhooks"
          description="Register the Discord, Slack, or Microsoft Teams webhooks used by RSS execution"
          :ui="{ body: 'space-y-5' }"
        >
          <div class="flex items-center justify-between gap-4 rounded-lg border border-default p-4">
            <div>
              <p class="font-medium text-highlighted">Include article summaries</p>
              <p class="text-sm text-muted">
                Include available summaries in all RSS webhook notifications.
              </p>
            </div>
            <USwitch
              :model-value="webhookSummaryEnabled"
              :loading="webhookSummaryLoading || webhookSummarySaving"
              aria-label="Include article summaries"
              @update:model-value="setWebhookSummary"
            />
          </div>

          <form class="space-y-4" @submit.prevent="addWebhook">
            <UFormField
              label="Name"
              description="A label that tells you which webhook this is at a glance."
              class="w-full"
            >
              <UInput
                v-model="webhookForm.name"
                class="w-full"
                placeholder="e.g. Team alerts (Discord)"
              />
            </UFormField>

            <UFormField
              label="Webhook URL"
              description="Every registered webhook receives RSS notifications."
              class="w-full"
            >
              <UInput
                v-model="webhookForm.webhookUrl"
                class="w-full"
                placeholder="Discord, Slack, or Microsoft Teams webhook URL"
              />
            </UFormField>

            <div class="flex flex-wrap items-center gap-3">
              <UButton
                type="button"
                color="warning"
                variant="ghost"
                icon="i-lucide-bell-ring"
                :loading="testingNewWebhook"
                @click="pingWebhook(webhookForm.webhookUrl.trim(), 'new')"
              >
                Test
              </UButton>
              <UButton type="submit" icon="i-lucide-plus" :loading="webhookSaving">
                Add webhook
              </UButton>
            </div>
          </form>

          <div class="space-y-3">
            <div
              v-for="webhook in webhooks"
              :key="webhook.id"
              class="flex flex-col gap-3 rounded-xl border border-default p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div class="min-w-0">
                <p class="text-sm font-medium text-default">{{ webhook.name }}</p>
                <p class="break-all text-xs text-muted">{{ webhook.webhook_url }}</p>
              </div>
              <div class="flex shrink-0 items-center gap-2">
                <USwitch
                  :model-value="webhook.enabled"
                  :loading="updatingWebhookId === webhook.id"
                  :aria-label="`${webhook.enabled ? 'Disable' : 'Enable'} ${webhook.name}`"
                  @update:model-value="setWebhookEnabled(webhook, $event)"
                />
                <UButton
                  size="sm"
                  color="warning"
                  variant="ghost"
                  icon="i-lucide-bell-ring"
                  :loading="testingWebhookId === webhook.id"
                  @click="pingWebhook(webhook.webhook_url, webhook.id)"
                >
                  Test
                </UButton>
                <UButton
                  size="sm"
                  color="error"
                  variant="ghost"
                  icon="i-lucide-trash-2"
                  @click="askDeleteWebhook(webhook)"
                >
                  Delete
                </UButton>
              </div>
            </div>
            <p v-if="!webhooks.length" class="text-sm text-muted">
              <span v-if="webhookLoading">Loading webhooks...</span>
              <span v-else>No webhooks are registered yet.</span>
            </p>
          </div>
        </UPageCard>

        <DeleteConfirmModal
          v-model:open="deleteOpen"
          title="Delete webhook"
          :subject="pendingWebhook?.name"
          confirm-label="Delete webhook"
          :loading="deleting"
          @cancel="pendingWebhook = null"
          @confirm="confirmDeleteWebhook"
        />

        <DeleteConfirmModal
          v-model:open="llmDeleteOpen"
          title="Delete LLM settings"
          subject="the saved LLM connection"
          confirm-label="Delete settings"
          :loading="llmDeleting"
          @confirm="deleteLlmSettings"
        />

      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { TabsItem } from "@nuxt/ui";
import type {
  LLMProvider,
  LLMSettingsResponse,
  LLMSettingsTestResponse,
  SettingsWebhookListResponse,
  SettingsWebhookPingResponse,
  SettingsWebhookResponse,
  SettingsWebhookSummaryResponse,
  SettingsRssExecutionResponse,
  SettingsRssWebhookNotificationResponse,
} from "~/types";

const colorMode = useColorMode();
const { request } = useApi();
const toast = useSingleToast();
const route = useRoute();
const router = useRouter();

type SettingsCategory = "general" | "automation" | "webhooks" | "llm";

const isSettingsCategory = (value: unknown): value is SettingsCategory =>
  typeof value === "string" && ["general", "automation", "webhooks", "llm"].includes(value);
const activeCategory = ref<SettingsCategory>(
  isSettingsCategory(route.query.tab) ? route.query.tab : "general",
);
const settingsCategories: TabsItem[] = [
  { label: "General", value: "general", icon: "i-lucide-palette" },
  { label: "Automation", value: "automation", icon: "i-lucide-zap" },
  { label: "Webhooks", value: "webhooks", icon: "i-lucide-webhook" },
  { label: "LLM", value: "llm", icon: "i-lucide-bot" },
];

watch(activeCategory, async (category) => {
  await router.replace({ query: { ...route.query, tab: category === "general" ? undefined : category } });
});

const themeOptions: TabsItem[] = [
  { label: "System", value: "system", icon: "i-lucide-monitor" },
  { label: "Light", value: "light", icon: "i-lucide-sun-medium" },
  { label: "Dark", value: "dark", icon: "i-lucide-moon-star" },
];

const selectedTheme = computed({
  get: () => colorMode.preference,
  set: (value) => {
    colorMode.preference = value;
  },
});

const webhooks = ref<SettingsWebhookResponse[]>([]);
const webhookLoading = ref(false);
const webhookSaving = ref(false);
const testingNewWebhook = ref(false);
const testingWebhookId = ref<number | null>(null);
const updatingWebhookId = ref<number | null>(null);
const deleteOpen = ref(false);
const deleting = ref(false);
const pendingWebhook = ref<SettingsWebhookResponse | null>(null);
const webhookForm = reactive({ name: "", webhookUrl: "" });
const webhookSummaryEnabled = ref(true);
const webhookSummaryLoading = ref(false);
const webhookSummarySaving = ref(false);
const rssExecutionEnabled = ref(false);
const rssExecutionLoading = ref(false);
const rssExecutionSaving = ref(false);
const rssWebhookNotificationEnabled = ref(false);
const rssWebhookNotificationLoading = ref(false);
const rssWebhookNotificationSaving = ref(false);
const llmSettings = ref<LLMSettingsResponse | null>(null);
const llmLoading = ref(false);
const llmSaving = ref(false);
const llmTesting = ref(false);
const llmDeleting = ref(false);
const llmDeleteOpen = ref(false);
const llmForm = reactive({
  provider: "ollama" as LLMProvider,
  baseUrl: "http://127.0.0.1:11434",
  model: "",
  apiKey: "",
  clearApiKey: false,
});
const llmProviderOptions = [
  { label: "Ollama", value: "ollama" as const },
  { label: "vLLM", value: "vllm" as const },
  { label: "OpenAI-compatible", value: "openai" as const },
];
const llmConfigured = computed(() => llmSettings.value !== null);
const llmApiKeyDescription = computed(() =>
  llmSettings.value?.api_key_configured
    ? "An API key is saved. Leave this blank to keep it unchanged."
    : "Optional for local servers that do not require authentication.",
);

const loadRssExecution = async () => {
  rssExecutionLoading.value = true;
  try {
    const response = await request<SettingsRssExecutionResponse>("/settings/rss-execution");
    rssExecutionEnabled.value = response.enabled;
  } catch (err) {
    toast.show({
      title: "Failed to load RSS execution setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    rssExecutionLoading.value = false;
  }
};

const setRssExecution = async (enabled: boolean) => {
  const previous = rssExecutionEnabled.value;
  rssExecutionEnabled.value = enabled;
  rssExecutionSaving.value = true;
  try {
    const response = await request<SettingsRssExecutionResponse>("/settings/rss-execution", {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    });
    rssExecutionEnabled.value = response.enabled;
    toast.show({
      title: response.enabled ? "RSS periodic execution enabled." : "RSS periodic execution disabled.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    rssExecutionEnabled.value = previous;
    toast.show({
      title: "Failed to update RSS execution setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    rssExecutionSaving.value = false;
  }
};

const loadRssWebhookNotification = async () => {
  rssWebhookNotificationLoading.value = true;
  try {
    const response = await request<SettingsRssWebhookNotificationResponse>(
      "/settings/rss-webhook-notification",
    );
    rssWebhookNotificationEnabled.value = response.enabled;
  } catch (err) {
    toast.show({
      title: "Failed to load RSS webhook notification setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    rssWebhookNotificationLoading.value = false;
  }
};

const setRssWebhookNotification = async (enabled: boolean) => {
  const previous = rssWebhookNotificationEnabled.value;
  rssWebhookNotificationEnabled.value = enabled;
  rssWebhookNotificationSaving.value = true;
  try {
    const response = await request<SettingsRssWebhookNotificationResponse>(
      "/settings/rss-webhook-notification",
      { method: "PUT", body: JSON.stringify({ enabled }) },
    );
    rssWebhookNotificationEnabled.value = response.enabled;
    toast.show({
      title: response.enabled
        ? "RSS webhook notifications enabled."
        : "RSS webhook notifications disabled.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    rssWebhookNotificationEnabled.value = previous;
    toast.show({
      title: "Failed to update RSS webhook notification setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    rssWebhookNotificationSaving.value = false;
  }
};

const loadLlmSettings = async () => {
  llmLoading.value = true;
  try {
    const response = await request<LLMSettingsResponse>("/settings/llm");
    llmSettings.value = response;
    llmForm.provider = response.provider as LLMProvider;
    llmForm.baseUrl = response.base_url;
    llmForm.model = response.model;
    llmForm.apiKey = "";
    llmForm.clearApiKey = false;
  } catch (err) {
    if (!(err instanceof Error) || !err.message.includes("not configured")) {
      toast.show({
        title: "Failed to load LLM settings.",
        description: err instanceof Error ? err.message : undefined,
        color: "error",
        icon: "i-lucide-circle-alert",
      });
    }
    llmSettings.value = null;
  } finally {
    llmLoading.value = false;
  }
};

const buildLlmBody = () => ({
  provider: llmForm.provider,
  base_url: llmForm.baseUrl.trim(),
  model: llmForm.model.trim(),
  ...(llmForm.apiKey.trim() ? { api_key: llmForm.apiKey.trim() } : {}),
  clear_api_key: llmForm.clearApiKey,
});

const validateLlmForm = () => {
  if (llmForm.baseUrl.trim() && llmForm.model.trim()) return true;
  toast.show({
    title: "Base URL and model are required.",
    color: "error",
    icon: "i-lucide-circle-alert",
  });
  return false;
};

const testLlmSettings = async () => {
  if (!validateLlmForm()) return;
  llmTesting.value = true;
  try {
    await request<LLMSettingsTestResponse>("/settings/llm/test", {
      method: "POST",
      body: JSON.stringify(buildLlmBody()),
    });
    toast.show({
      title: "LLM connection is working.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "LLM connection test failed.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    llmTesting.value = false;
  }
};

const saveLlmSettings = async () => {
  if (!validateLlmForm()) return;
  llmSaving.value = true;
  try {
    llmSettings.value = await request<LLMSettingsResponse>("/settings/llm", {
      method: "PUT",
      body: JSON.stringify(buildLlmBody()),
    });
    llmForm.apiKey = "";
    llmForm.clearApiKey = false;
    toast.show({
      title: "LLM settings tested and saved.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to save LLM settings.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    llmSaving.value = false;
  }
};

const deleteLlmSettings = async () => {
  llmDeleting.value = true;
  try {
    await request("/settings/llm", { method: "DELETE" });
    llmSettings.value = null;
    llmForm.apiKey = "";
    llmForm.clearApiKey = false;
    llmDeleteOpen.value = false;
    toast.show({
      title: "LLM settings deleted.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to delete LLM settings.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    llmDeleting.value = false;
  }
};

const loadWebhooks = async () => {
  webhookLoading.value = true;
  try {
    const response = await request<SettingsWebhookListResponse>("/settings/webhooks");
    webhooks.value = response.items;
  } catch (err) {
    toast.show({
      title: "Failed to load webhooks.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    webhookLoading.value = false;
  }
};

const loadWebhookSummary = async () => {
  webhookSummaryLoading.value = true;
  try {
    const response = await request<SettingsWebhookSummaryResponse>(
      "/settings/webhook-summary",
    );
    webhookSummaryEnabled.value = response.enabled;
  } catch (err) {
    toast.show({
      title: "Failed to load webhook summary setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    webhookSummaryLoading.value = false;
  }
};

const setWebhookSummary = async (enabled: boolean) => {
  const previous = webhookSummaryEnabled.value;
  webhookSummaryEnabled.value = enabled;
  webhookSummarySaving.value = true;
  try {
    const response = await request<SettingsWebhookSummaryResponse>(
      "/settings/webhook-summary",
      {
        method: "PUT",
        body: JSON.stringify({ enabled }),
      },
    );
    webhookSummaryEnabled.value = response.enabled;
    toast.show({
      title: "Webhook summary setting updated.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    webhookSummaryEnabled.value = previous;
    toast.show({
      title: "Failed to update webhook summary setting.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    webhookSummarySaving.value = false;
  }
};

const addWebhook = async () => {
  const name = webhookForm.name.trim();
  const webhookUrl = webhookForm.webhookUrl.trim();
  if (!name) {
    toast.show({
      title: "Name is required.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return;
  }
  if (!webhookUrl) {
    toast.show({
      title: "Webhook URL is required.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return;
  }

  webhookSaving.value = true;
  try {
    const response = await request<SettingsWebhookResponse>("/settings/webhooks", {
      method: "POST",
      body: JSON.stringify({ name, webhook_url: webhookUrl }),
    });
    webhooks.value = [...webhooks.value, response];
    webhookForm.name = "";
    webhookForm.webhookUrl = "";
    toast.show({
      title: "Webhook added.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to add webhook.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    webhookSaving.value = false;
  }
};

const pingWebhook = async (webhookUrl: string, target: "new" | number) => {
  if (!webhookUrl) {
    toast.show({
      title: "Webhook URL is required.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return;
  }

  if (target === "new") {
    testingNewWebhook.value = true;
  } else {
    testingWebhookId.value = target;
  }
  try {
    await request<SettingsWebhookPingResponse>("/settings/webhook/ping", {
      method: "POST",
      body: JSON.stringify({ webhook_url: webhookUrl }),
    });
    toast.show({
      title: "Webhook endpoint is reachable.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to ping webhook.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    if (target === "new") {
      testingNewWebhook.value = false;
    } else {
      testingWebhookId.value = null;
    }
  }
};

const setWebhookEnabled = async (
  webhook: SettingsWebhookResponse,
  enabled: boolean,
) => {
  updatingWebhookId.value = webhook.id;
  try {
    const updated = await request<SettingsWebhookResponse>(
      `/settings/webhooks/${webhook.id}`,
      {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      },
    );
    webhooks.value = webhooks.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
    toast.show({
      title: updated.enabled ? "Webhook enabled." : "Webhook disabled.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to update webhook.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    updatingWebhookId.value = null;
  }
};

const askDeleteWebhook = (webhook: SettingsWebhookResponse) => {
  pendingWebhook.value = webhook;
  deleteOpen.value = true;
};

const confirmDeleteWebhook = async () => {
  if (!pendingWebhook.value) return;
  const webhookId = pendingWebhook.value.id;
  deleting.value = true;
  try {
    await request(`/settings/webhooks/${webhookId}`, { method: "DELETE" });
    webhooks.value = webhooks.value.filter((item) => item.id !== webhookId);
    deleteOpen.value = false;
    pendingWebhook.value = null;
    toast.show({
      title: "Webhook deleted.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to delete webhook.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    deleting.value = false;
  }
};

onMounted(async () => {
  await Promise.all([
    loadLlmSettings(),
    loadWebhooks(),
    loadWebhookSummary(),
    loadRssExecution(),
    loadRssWebhookNotification(),
  ]);
});
</script>
