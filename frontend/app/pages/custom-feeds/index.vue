<template>
  <UDashboardPanel id="custom-feeds-list">
    <template #header>
      <PageHeaderActions title="Custom RSS" />
    </template>

    <template #body>
      <div class="mx-auto w-full max-w-7xl pb-10">
        <CustomFeedsPanel :webhooks="webhooks" />
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { SettingsWebhookListResponse, SettingsWebhookResponse } from "~/types";

const { request } = useApi();
const toast = useSingleToast();
const webhooks = ref<SettingsWebhookResponse[]>([]);

onMounted(async () => {
  try {
    webhooks.value = (await request<SettingsWebhookListResponse>("/settings/webhooks")).items;
  } catch (error) {
    toast.show({
      title: "Failed to load webhooks.",
      description: error instanceof Error ? error.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
});
</script>

