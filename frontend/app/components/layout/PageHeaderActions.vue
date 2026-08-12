<template>
  <UDashboardNavbar :title="title" class="border-b border-default/70 bg-default/80 backdrop-blur" :ui="{ right: 'gap-3' }">
    <template #leading>
      <UDashboardSidebarCollapse />
    </template>
    <template v-if="$slots.default" #right>
      <slot />
    </template>
  </UDashboardNavbar>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>
