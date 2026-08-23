<template>
  <div class="flex flex-wrap items-center justify-end gap-2">
    <UButton
      size="sm"
      variant="ghost"
      color="neutral"
      :disabled="page <= 1 || loading"
      @click="emit('update:page', page - 1)"
    >
      Prev
    </UButton>
    <template
      v-for="(item, index) in items"
      :key="`${item.type}-${index}-${item.type === 'page' ? item.value : 'ellipsis'}`"
    >
      <UButton
        v-if="item.type === 'page'"
        size="sm"
        :color="item.value === page ? 'primary' : 'neutral'"
        :variant="item.value === page ? 'solid' : 'ghost'"
        :disabled="loading"
        @click="emit('update:page', item.value)"
      >
        {{ item.label }}
      </UButton>
      <UButton v-else size="sm" variant="ghost" color="neutral" disabled> ... </UButton>
    </template>
    <UButton
      size="sm"
      variant="ghost"
      color="neutral"
      :disabled="page >= totalPages || loading"
      @click="emit('update:page', page + 1)"
    >
      Next
    </UButton>
  </div>
</template>

<script setup lang="ts">
import { buildPaginationItems } from "~/utils/pagination";

const props = defineProps<{
  page: number;
  totalPages: number;
  loading?: boolean;
}>();

const emit = defineEmits<{
  "update:page": [page: number];
}>();

const items = computed(() => buildPaginationItems(props.page, Math.max(props.totalPages, 1)));
</script>
