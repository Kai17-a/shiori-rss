<template>
  <article class="group relative overflow-hidden rounded-3xl border border-default bg-default p-5 transition duration-200 hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-lg hover:shadow-primary/5">
    <div class="absolute inset-y-0 left-0 w-1 bg-primary opacity-0 transition group-hover:opacity-100" />

    <div class="flex items-start gap-4">
      <NuxtLink
        :to="`/custom-feeds/${site.id}`"
        class="grid size-11 shrink-0 place-items-center overflow-hidden rounded-2xl bg-primary/10 text-primary transition group-hover:bg-primary group-hover:text-inverted"
        :aria-label="`Open ${site.title}`"
      >
        <img v-if="site.icon_url" :src="site.icon_url" alt="" class="size-full object-cover" />
        <UIcon v-else name="i-lucide-wand-sparkles" class="size-5" />
      </NuxtLink>

      <div class="min-w-0 flex-1">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <NuxtLink
              :to="`/custom-feeds/${site.id}`"
              class="block truncate text-lg font-bold tracking-tight text-highlighted hover:text-primary"
            >
              {{ site.title }}
            </NuxtLink>
            <p class="mt-1 truncate text-xs text-muted" :title="site.url">{{ site.url }}</p>
          </div>
          <UBadge
            :color="site.notify_webhook_enabled ? 'success' : 'neutral'"
            variant="soft"
            size="sm"
            :icon="site.notify_webhook_enabled ? 'i-lucide-bell-ring' : 'i-lucide-bell-off'"
            :label="site.notify_webhook_enabled ? 'Live' : 'Muted'"
          />
        </div>

        <p class="mt-4 line-clamp-2 min-h-10 text-sm leading-5 text-muted">
          {{ site.description || "No description yet. Open the source to browse its saved articles." }}
        </p>

        <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-default pt-4">
          <NuxtLink :to="`/custom-feeds/${site.id}`" class="inline-flex items-center gap-1.5 text-sm font-semibold text-primary">
            Browse articles
            <UIcon name="i-lucide-arrow-right" class="size-4 transition group-hover:translate-x-0.5" />
          </NuxtLink>

          <div class="flex flex-wrap items-center gap-1">
            <IconButton
              :color="site.notify_webhook_enabled ? 'warning' : 'neutral'"
              :icon="site.notify_webhook_enabled ? 'i-lucide-bell' : 'i-lucide-bell-off'"
              :label="site.notify_webhook_enabled ? 'Disable webhook notification' : 'Enable webhook notification'"
              :loading="notificationLoading"
              @click.stop="$emit('toggleWebhook', site)"
            />
            <IconButton
              label="Fetch now"
              icon="i-lucide-play"
              color="primary"
              :loading="running"
              @click.stop="$emit('execute', site)"
            />
            <IconButton label="Edit" icon="i-lucide-pencil" @click.stop="$emit('edit', site)" />
            <IconButton label="Delete" icon="i-lucide-trash-2" color="error" @click.stop="$emit('remove', site)" />
          </div>
        </div>
      </div>
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
