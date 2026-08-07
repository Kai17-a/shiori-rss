<template>
  <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
    <div class="min-w-0 space-y-1">
      <slot name="title">
        <h1 v-if="title" class="text-2xl font-semibold text-default">
          {{ title }}
        </h1>
      </slot>

      <slot name="description">
        <p v-if="description" class="text-sm leading-6 text-default/90">
          {{ description }}
        </p>
      </slot>

      <slot />
    </div>

    <div class="flex flex-wrap gap-3 self-start">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
  description?: string;
}>();
</script>
