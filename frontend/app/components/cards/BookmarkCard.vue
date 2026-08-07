<template>
  <article class="rounded-2xl border border-default bg-elevated/40 p-4 space-y-4 min-w-full">
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <div class="flex items-center gap-1.5">
          <IconButton
            class="shrink-0 px-1"
            :color="bookmark.is_favorite ? 'warning' : 'neutral'"
            :icon="bookmark.is_favorite ? 'i-lucide-star' : 'i-lucide-star-off'"
            :label="bookmark.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
            @click.stop="$emit('favorite', bookmark)"
          />
          <NuxtLink
            :to="bookmark.url"
            external
            target="_blank"
            rel="noreferrer"
            class="block truncate text-base font-semibold text-default hover:underline"
          >
            {{ bookmark.title }}
          </NuxtLink>
        </div>
        <p class="mt-1 break-all text-sm text-muted">
          {{ bookmark.url }}
        </p>
      </div>

      <div class="hidden shrink-0 items-center gap-2 sm:flex">
        <IconButton label="Edit" icon="i-lucide-pencil" @click.stop="$emit('edit', bookmark)" />
        <IconButton
          label="Delete"
          icon="i-lucide-trash-2"
          color="error"
          variant="soft"
          @click.stop="$emit('remove', bookmark)"
        />
      </div>
    </div>

    <p v-if="bookmark.description" class="text-sm text-default">
      {{ bookmark.description }}
    </p>

    <div v-if="showFolder || (showTags && bookmark.tags.length)" class="space-y-3">
      <div v-if="showFolder && bookmark.folder_name" class="flex flex-wrap gap-2">
        <UBadge size="sm" color="success" variant="soft" icon="i-lucide-folder">
          {{ bookmark.folder_name }}
        </UBadge>
      </div>

      <div v-if="showTags && bookmark.tags.length" class="flex flex-wrap gap-2">
        <UBadge
          v-for="tag in bookmark.tags"
          :key="tag.id"
          size="sm"
          color="neutral"
          variant="subtle"
          :ui="{ rounded: 'rounded-full' }"
        >
          {{ tag.name }}
        </UBadge>
      </div>
    </div>

    <div class="flex justify-end gap-2 sm:hidden">
      <IconButton label="Edit" icon="i-lucide-pencil" @click.stop="$emit('edit', bookmark)" />
      <IconButton
        label="Delete"
        icon="i-lucide-trash-2"
        color="error"
        variant="soft"
        @click.stop="$emit('remove', bookmark)"
      />
    </div>
  </article>
</template>

<script setup lang="ts">
import type { BookmarkResponse } from "~/types";

defineProps<{
  bookmark: BookmarkResponse & { folder_name?: string | null };
  showFolder?: boolean;
  showTags?: boolean;
}>();

defineEmits<{
  edit: [bookmark: BookmarkResponse & { folder_name?: string | null }];
  remove: [bookmark: BookmarkResponse & { folder_name?: string | null }];
  favorite: [bookmark: BookmarkResponse & { folder_name?: string | null }];
}>();
</script>
