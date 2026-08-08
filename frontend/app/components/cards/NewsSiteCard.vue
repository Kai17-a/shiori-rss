<template>
  <article class="space-y-4 rounded-2xl border border-default bg-elevated/40 p-4">
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <NuxtLink
          :to="`/custom-feeds/${site.id}`"
          class="block truncate text-base font-semibold text-default hover:underline"
        >
          {{ site.title }}
        </NuxtLink>
        <p class="mt-1 break-all text-sm text-muted">{{ site.url }}</p>
      </div>
      <UBadge color="info" variant="soft">LLM Custom RSS</UBadge>
    </div>

    <p v-if="site.description" class="text-sm text-default">{{ site.description }}</p>
    <p v-else class="text-sm text-muted">No description.</p>

    <div class="flex flex-wrap justify-end gap-2">
      <IconButton
        :color="site.notify_webhook_enabled ? 'warning' : 'neutral'"
        :icon="site.notify_webhook_enabled ? 'i-lucide-bell' : 'i-lucide-bell-off'"
        :label="site.notify_webhook_enabled ? 'Disable webhook notification' : 'Enable webhook notification'"
        @click="$emit('toggleWebhook', site)"
      />
      <IconButton
        label="Fetch now"
        icon="i-lucide-play"
        color="primary"
        variant="soft"
        :loading="running"
        @click="$emit('execute', site)"
      />
      <IconButton label="Edit" icon="i-lucide-pencil" @click="$emit('edit', site)" />
      <IconButton
        label="Delete"
        icon="i-lucide-trash-2"
        color="error"
        variant="soft"
        @click="$emit('remove', site)"
      />
    </div>
  </article>
</template>

<script setup lang="ts">
import type { NewsSiteResponse } from "~/types";

defineProps<{ site: NewsSiteResponse; running?: boolean }>();
defineEmits<{
  edit: [site: NewsSiteResponse];
  execute: [site: NewsSiteResponse];
  toggleWebhook: [site: NewsSiteResponse];
  remove: [site: NewsSiteResponse];
}>();
</script>
