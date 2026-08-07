<template>
  <UDashboardPanel id="settings">
    <template #header>
      <PageHeaderActions title="Settings" />
    </template>

    <template #body>
      <div class="space-y-6">
        <UPageCard
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

      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { TabsItem } from "@nuxt/ui";
import type {
  SettingsWebhookListResponse,
  SettingsWebhookPingResponse,
  SettingsWebhookResponse,
  SettingsWebhookSummaryResponse,
} from "~/types";

const colorMode = useColorMode();
const { request } = useApi();
const toast = useSingleToast();

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
  await Promise.all([loadWebhooks(), loadWebhookSummary()]);
});
</script>
