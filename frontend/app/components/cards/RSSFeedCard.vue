<template>
  <article class="rounded-2xl border border-default bg-elevated/40 p-4 space-y-4">
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <NuxtLink
          :to="to"
          class="block truncate text-base font-semibold text-default hover:underline"
        >
          {{ feed.title }}
        </NuxtLink>
        <p class="mt-1 break-all text-sm text-muted">
          {{ feed.url }}
        </p>
      </div>

      <div class="hidden shrink-0 items-center gap-2 sm:flex">
        <IconButton
          class="shrink-0 px-1"
          :color="feed.notify_webhook_enabled ? 'warning' : 'neutral'"
          :icon="feed.notify_webhook_enabled ? 'i-lucide-bell' : 'i-lucide-bell-off'"
          :label="feed.notify_webhook_enabled ? 'Disable webhook notification' : 'Enable webhook notification'"
          @click.stop="$emit('toggleWebhook', feed)"
        />
        <IconButton
          label="Run feed"
          icon="i-lucide-play"
          variant="soft"
          color="primary"
          :loading="running"
          @click.stop="$emit('execute', feed)"
        />
        <IconButton label="Edit" icon="i-lucide-pencil" @click.stop="$emit('edit', feed)" />
        <IconButton
          label="Delete"
          icon="i-lucide-trash-2"
          color="error"
          variant="soft"
          @click.stop="$emit('remove', feed)"
        />
      </div>
    </div>

    <p v-if="feed.description" class="text-sm text-default">
      {{ feed.description }}
    </p>
    <p v-else class="text-sm text-muted">No description.</p>

    <div class="flex justify-end gap-2 sm:hidden">
      <IconButton
        class="shrink-0 px-1"
        :color="feed.notify_webhook_enabled ? 'warning' : 'neutral'"
        :icon="feed.notify_webhook_enabled ? 'i-lucide-bell' : 'i-lucide-bell-off'"
        :label="feed.notify_webhook_enabled ? 'Disable webhook notification' : 'Enable webhook notification'"
        @click.stop="$emit('toggleWebhook', feed)"
      />
      <UButton
        type="button"
        size="xs"
        variant="soft"
        color="primary"
        icon="i-lucide-play"
        :loading="running"
        @click.stop="$emit('execute', feed)"
      >
        Run
      </UButton>
      <IconButton label="Edit" icon="i-lucide-pencil" @click.stop="$emit('edit', feed)" />
      <IconButton
        label="Delete"
        icon="i-lucide-trash-2"
        color="error"
        variant="soft"
        @click.stop="$emit('remove', feed)"
      />
    </div>
  </article>
</template>

<script setup lang="ts">
import type { RSSFeedResponse } from "~/types";

defineProps<{
  feed: RSSFeedResponse;
  to: string;
  running?: boolean;
}>();

defineEmits<{
  edit: [feed: RSSFeedResponse];
  execute: [feed: RSSFeedResponse];
  toggleWebhook: [feed: RSSFeedResponse];
  remove: [feed: RSSFeedResponse];
}>();
</script>
