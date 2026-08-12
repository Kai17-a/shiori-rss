<template>
  <article class="min-w-0 max-w-full space-y-4 rounded-2xl border border-default bg-elevated/40 p-4">
    <div class="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <div class="flex min-w-0 items-start gap-3">
        <NuxtLink
          :to="`/custom-feeds/${site.id}`"
          class="grid size-11 shrink-0 place-items-center overflow-hidden rounded-2xl bg-primary/10 text-primary"
          :aria-label="`Open ${site.title}`"
        >
          <img v-if="site.icon_url" :src="site.icon_url" alt="" class="size-full object-cover" />
          <UIcon v-else name="i-lucide-wand-sparkles" class="size-4" />
        </NuxtLink>
        <div class="min-w-0">
          <NuxtLink
            :to="`/custom-feeds/${site.id}`"
            class="block truncate text-base font-semibold text-default hover:underline"
          >
            {{ site.title }}
          </NuxtLink>
          <p class="mt-1 break-all text-sm text-muted">{{ site.url }}</p>
        </div>
      </div>
      <UBadge class="self-start" color="info" variant="soft">LLM Custom RSS</UBadge>
    </div>

    <p v-if="site.description" class="max-w-full text-sm text-default [overflow-wrap:anywhere]">{{ site.description }}</p>
    <p v-else class="text-sm text-muted">No description.</p>

    <div class="flex flex-wrap justify-end gap-2">
      <IconButton
        :color="site.notify_webhook_enabled ? 'warning' : 'neutral'"
        :icon="site.notify_webhook_enabled ? 'i-lucide-bell' : 'i-lucide-bell-off'"
        :label="site.notify_webhook_enabled ? 'Disable webhook notification' : 'Enable webhook notification'"
        :loading="notificationLoading"
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

defineProps<{
  site: NewsSiteResponse;
  running?: boolean;
  notificationLoading?: boolean;
}>();
defineEmits<{
  edit: [site: NewsSiteResponse];
  execute: [site: NewsSiteResponse];
  toggleWebhook: [site: NewsSiteResponse];
  remove: [site: NewsSiteResponse];
}>();
</script>
