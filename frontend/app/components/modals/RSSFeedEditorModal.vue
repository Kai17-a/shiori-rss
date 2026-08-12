<template>
  <UModal v-model:open="openModel" :title="title" :description="description">
    <template #content="{ close }">
      <form class="space-y-4 p-6" @submit.prevent="emit('save')">
        <UFormField label="Title" required class="w-full">
          <UInput v-model="form.title" :placeholder="titlePlaceholder" class="w-full" />
        </UFormField>

        <UFormField label="URL" required class="w-full">
          <UInput v-model="form.url" :placeholder="urlPlaceholder" class="w-full" />
        </UFormField>

        <UFormField
          label="Notification webhooks"
          description="When none are selected, all registered webhooks are notified."
          class="w-full"
        >
          <div v-if="webhooks.length" class="space-y-2">
            <UCheckbox
              v-for="webhook in webhooks"
              :key="webhook.id"
              :model-value="form.webhookIds.includes(webhook.id)"
              :label="webhook.name"
              @update:model-value="toggleWebhook(webhook.id, $event)"
            />
          </div>
          <p v-else class="text-sm text-muted">
            No webhooks are registered yet. Add them from the Settings page.
          </p>
        </UFormField>

        <UFormField label="Description" class="w-full">
          <UTextarea
            v-model="form.description"
            :placeholder="descriptionPlaceholder"
            :rows="4"
            class="w-full"
          />
        </UFormField>

        <FeedIconField :form="form" />

        <div class="flex justify-end gap-3">
          <UButton type="button" color="neutral" variant="ghost" @click="close"> Cancel </UButton>
          <UButton
            type="submit"
            :loading="saving"
            loading-icon="i-lucide-loader-circle"
          >
            {{ submitLabel }}
          </UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import type { SettingsWebhookResponse } from "~/types";

const openModel = defineModel<boolean>("open", { required: true });

const props = defineProps<{
  form: {
    title: string;
    url: string;
    description: string;
    webhookIds: number[];
    iconUrl: string;
    iconFile: File | null;
    existingIconUrl: string;
    removeIcon: boolean;
  };
  webhooks: SettingsWebhookResponse[];
  title: string;
  description: string;
  titlePlaceholder: string;
  urlPlaceholder: string;
  descriptionPlaceholder: string;
  submitLabel: string;
  saving?: boolean;
}>();

const emit = defineEmits<{
  save: [];
}>();

const toggleWebhook = (webhookId: number, checked: boolean | string) => {
  const selected = new Set(props.form.webhookIds);
  if (checked === true) {
    selected.add(webhookId);
  } else {
    selected.delete(webhookId);
  }
  props.form.webhookIds = [...selected];
};
</script>
