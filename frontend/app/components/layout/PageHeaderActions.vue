<template>
  <UDashboardNavbar :title="title" :ui="{ right: 'gap-3' }">
    <template #leading>
      <UDashboardSidebarCollapse />
    </template>

    <!-- <template #right>
      <UButton
        to="https://github.com/Kai17-a/browser-bookmark-manager"
        target="_blank"
        rel="noopener noreferrer"
        icon="i-simple-icons-github"
        label="GitHub"
        color="neutral"
        variant="ghost"
        size="sm"
      />
      <slot name="actions" />
    </template> -->
  </UDashboardNavbar>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>
