<template>
  <UButton
    type="button"
    icon="i-lucide-refresh-cw"
    color="neutral"
    variant="ghost"
    size="sm"
    :loading="loading"
    :disabled="disabled"
    @click="$emit('click')"
  >
    <slot>Refresh</slot>
  </UButton>
</template>

<script setup lang="ts">
defineProps<{
  loading?: boolean;
  disabled?: boolean;
}>();

defineEmits<{
  click: [];
}>();
</script>
