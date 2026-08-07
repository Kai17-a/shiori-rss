<template>
  <UModal v-model:open="openModel" :title="title" :description="description">
    <template #content="{ close }">
      <form class="space-y-4 p-6" @submit.prevent="emit('save')">
        <UFormField
          label="Site URL"
          required
          description="The page that lists the latest news articles."
          class="w-full"
        >
          <UInput
            v-model="form.url"
            placeholder="https://example.com/news"
            class="w-full"
          />
        </UFormField>

        <UFormField
          label="Title"
          :description="form.id ? undefined : 'Optional. The LLM-detected site title is used when left blank.'"
          class="w-full"
        >
          <UInput v-model="form.title" placeholder="Optional site title" class="w-full" />
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
            placeholder="Optional description"
            :rows="4"
            class="w-full"
          />
        </UFormField>

        <UFormField
          v-if="form.id"
          label="Site analysis"
          description="Use this after the target site's layout changes. For an unchanged URL, saving without this option keeps the current selectors."
          class="w-full"
        >
          <UCheckbox
            v-model="form.reanalyze"
            label="Re-analyze with LLM when saving"
          />
        </UFormField>

        <UAlert
          v-if="!form.id"
          title="Registration includes a live extraction test"
          description="The page HTML is analyzed by the configured LLM and at least one title and link must be extracted before the site is saved."
          color="info"
          variant="soft"
        />

        <UAlert
          v-if="error"
          title="Analysis or extraction failed"
          :description="error"
          color="error"
          variant="soft"
          icon="i-lucide-circle-alert"
        />

        <div class="flex justify-end gap-3">
          <UButton type="button" color="neutral" variant="ghost" @click="close">
            Cancel
          </UButton>
          <UButton type="submit" :loading="saving">
            {{ form.id ? "Save site" : "Analyze and register" }}
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
    id: string;
    title: string;
    url: string;
    description: string;
    webhookIds: number[];
    reanalyze: boolean;
  };
  webhooks: SettingsWebhookResponse[];
  title: string;
  description: string;
  saving?: boolean;
  error?: string;
}>();
const emit = defineEmits<{ save: [] }>();

const toggleWebhook = (webhookId: number, checked: boolean | string) => {
  const selected = new Set(props.form.webhookIds);
  if (checked === true) selected.add(webhookId);
  else selected.delete(webhookId);
  props.form.webhookIds = [...selected];
};
</script>
