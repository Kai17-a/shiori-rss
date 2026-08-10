<template>
  <article class="group relative overflow-hidden rounded-3xl border border-default bg-default p-5 transition duration-200 hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-lg hover:shadow-primary/5">
    <div class="absolute inset-y-0 left-0 w-1 bg-primary opacity-0 transition group-hover:opacity-100" />

    <div class="flex items-start gap-4">
      <NuxtLink
        :to="to"
        class="grid size-11 shrink-0 place-items-center rounded-2xl bg-primary/10 text-primary transition group-hover:bg-primary group-hover:text-inverted"
        :aria-label="`Open ${feed.title}`"
      >
        <img v-if="feed.icon_url" :src="feed.icon_url" alt="" class="size-full rounded-2xl object-cover" />
        <UIcon v-else name="i-lucide-rss" class="size-5" />
      </NuxtLink>

      <div class="min-w-0 flex-1">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <NuxtLink :to="to" class="block truncate text-lg font-bold tracking-tight text-highlighted hover:text-primary">
              {{ feed.title }}
            </NuxtLink>
            <p class="mt-1 truncate text-xs text-muted">{{ feedHost }}</p>
          </div>
          <UBadge
            :color="feed.notify_webhook_enabled ? 'success' : 'neutral'"
            variant="soft"
            size="sm"
            :icon="feed.notify_webhook_enabled ? 'i-lucide-bell-ring' : 'i-lucide-bell-off'"
            :label="feed.notify_webhook_enabled ? 'Live' : 'Muted'"
          />
        </div>

        <p class="mt-4 line-clamp-2 min-h-10 text-sm leading-5 text-muted">
          {{ feed.description || "No description yet. Open the feed to browse its saved articles." }}
        </p>

        <div class="mt-5 flex items-center justify-between gap-3 border-t border-default pt-4">
          <NuxtLink :to="to" class="inline-flex items-center gap-1.5 text-sm font-semibold text-primary">
            Browse articles
            <UIcon name="i-lucide-arrow-right" class="size-4 transition group-hover:translate-x-0.5" />
          </NuxtLink>

          <div class="flex items-center gap-1">
            <IconButton
              :color="feed.notify_webhook_enabled ? 'warning' : 'neutral'"
              :icon="feed.notify_webhook_enabled ? 'i-lucide-bell' : 'i-lucide-bell-off'"
              :label="feed.notify_webhook_enabled ? 'Mute feed delivery' : 'Enable feed delivery'"
              :loading="notificationLoading"
              @click.stop="$emit('toggleWebhook', feed)"
            />
            <IconButton
              label="Fetch now"
              icon="i-lucide-refresh-cw"
              color="primary"
              :loading="running"
              @click.stop="$emit('execute', feed)"
            />
            <IconButton label="Edit feed" icon="i-lucide-pencil" @click.stop="$emit('edit', feed)" />
            <IconButton label="Delete feed" icon="i-lucide-trash-2" color="error" @click.stop="$emit('remove', feed)" />
          </div>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { RSSFeedResponse } from "~/types";

const props = defineProps<{
  feed: RSSFeedResponse;
  to: string;
  running?: boolean;
  notificationLoading?: boolean;
}>();

defineEmits<{
  edit: [feed: RSSFeedResponse];
  execute: [feed: RSSFeedResponse];
  toggleWebhook: [feed: RSSFeedResponse];
  remove: [feed: RSSFeedResponse];
}>();

const feedHost = computed(() => {
  try {
    return new URL(props.feed.url).hostname.replace(/^www\./, "");
  } catch {
    return props.feed.url;
  }
});
</script>
