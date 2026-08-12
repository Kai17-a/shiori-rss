<template>
  <UModal v-model:open="openModel" :title="title" :description="description">
    <template #content="{ close }">
      <form
        class="max-h-[calc(100dvh-2rem)] space-y-4 overflow-y-auto p-6 sm:max-h-[calc(100dvh-4rem)]"
        @submit.prevent="emit('save')"
      >
        <UTabs
          v-model="form.configurationMode"
          :items="configurationModes"
          :content="false"
          class="w-full"
          aria-label="Custom RSS configuration method"
        />

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
          :description="titleDescription"
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

        <FeedIconField :form="form" />

        <div v-if="form.configurationMode === 'manual'" class="space-y-4 rounded-lg border border-default p-4">
          <div>
            <p class="text-sm font-semibold text-default">CSS selectors</p>
            <p class="text-sm text-muted">
              Select each article container first, then fields relative to that container.
            </p>
          </div>
          <UFormField label="Article item selector" required>
            <UInput v-model="form.itemSelector" placeholder="article.news-item" class="w-full" />
          </UFormField>
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField label="Title selector" required>
              <UInput v-model="form.titleSelector" placeholder="h2 a" class="w-full" />
            </UFormField>
            <UFormField label="Link selector" required>
              <UInput v-model="form.linkSelector" placeholder="h2 a" class="w-full" />
            </UFormField>
            <UFormField label="Link attribute" description="Usually href.">
              <UInput v-model="form.linkAttribute" placeholder="href" class="w-full" />
            </UFormField>
            <UFormField label="Summary selector" description="Optional.">
              <UInput v-model="form.summarySelector" placeholder=".summary" class="w-full" />
            </UFormField>
            <UFormField label="Published date selector" description="Optional.">
              <UInput v-model="form.publishedSelector" placeholder="time" class="w-full" />
            </UFormField>
            <UFormField label="Published date attribute" description="Optional, for example datetime.">
              <UInput v-model="form.publishedAttribute" placeholder="datetime" class="w-full" />
            </UFormField>
          </div>
        </div>

        <UFormField
          v-if="form.id && form.configurationMode === 'ai'"
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
          :description="registrationTestDescription"
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
    id: string;
    title: string;
    url: string;
    description: string;
    webhookIds: number[];
    reanalyze: boolean;
    iconUrl: string;
    iconFile: File | null;
    existingIconUrl: string;
    removeIcon: boolean;
    configurationMode: "ai" | "manual";
    itemSelector: string;
    titleSelector: string;
    linkSelector: string;
    linkAttribute: string;
    summarySelector: string;
    publishedSelector: string;
    publishedAttribute: string;
  };
  webhooks: SettingsWebhookResponse[];
  title: string;
  description: string;
  saving?: boolean;
  error?: string;
}>();
const emit = defineEmits<{ save: [] }>();

const configurationModes = [
  { label: "AI setup", value: "ai", icon: "i-lucide-sparkles" },
  { label: "Manual setup", value: "manual", icon: "i-lucide-sliders-horizontal" },
];
const titleDescription = computed(() => {
  if (props.form.id) return undefined;
  return props.form.configurationMode === "ai"
    ? "Optional. The LLM-detected site title is used when left blank."
    : "Optional. The site's hostname is used when left blank.";
});
const registrationTestDescription = computed(() => props.form.configurationMode === "ai"
  ? "The page HTML is analyzed by the configured LLM and at least one title and link must be extracted before the site is saved."
  : "The configured selectors are tested against the live page without calling an LLM. At least one title and link must be extracted.");
const submitLabel = computed(() => {
  if (props.form.id) return "Save site";
  return props.form.configurationMode === "ai" ? "Analyze and register" : "Test and register";
});

const toggleWebhook = (webhookId: number, checked: boolean | string) => {
  const selected = new Set(props.form.webhookIds);
  if (checked === true) selected.add(webhookId);
  else selected.delete(webhookId);
  props.form.webhookIds = [...selected];
};
</script>
