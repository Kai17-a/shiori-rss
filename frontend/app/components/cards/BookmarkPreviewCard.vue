<template>
  <UCard
    :ui="{
      body: 'space-y-4',
      header: 'space-y-2',
    }"
  >
    <template #header>
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <NuxtLink
            :to="bookmark.url"
            external
            target="_blank"
            rel="noreferrer"
            class="block truncate text-base font-semibold text-default hover:underline"
          >
            {{ bookmark.title }}
          </NuxtLink>
          <p class="mt-1 break-all text-sm text-muted">
            {{ bookmark.url }}
          </p>
        </div>

        <UBadge size="xs" variant="soft">#{{ bookmark.id }}</UBadge>
      </div>
    </template>

    <p v-if="bookmark.description" class="text-sm text-default">
      {{ bookmark.description }}
    </p>

    <div v-if="showTags" class="flex flex-wrap gap-2">
      <UBadge
        v-for="tag in visibleTags"
        :key="tag.id"
        size="xs"
        color="neutral"
        variant="subtle"
        :ui="{ rounded: 'rounded-full' }"
      >
        {{ tag.name }}
      </UBadge>
      <span v-if="remainingTagCount > 0" class="self-center text-xs text-muted">
        +{{ remainingTagCount }}
      </span>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { BookmarkResponse } from "~/types";

const props = defineProps<{
  bookmark: BookmarkResponse;
  maxTags?: number;
}>();

const visibleTags = computed(() => props.bookmark.tags.slice(0, props.maxTags ?? 4));

const showTags = computed(() => (props.maxTags ?? 4) > 0 && props.bookmark.tags.length > 0);

const remainingTagCount = computed(() => props.bookmark.tags.length - visibleTags.value.length);
</script>
