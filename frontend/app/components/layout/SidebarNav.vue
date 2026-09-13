<template>
  <div class="flex h-full flex-col gap-4">
    <UNavigationMenu
      :collapsed="collapsed"
      :items="browsingLinks"
      orientation="vertical"
      tooltip
      aria-label="Browse"
    />
    <UNavigationMenu
      :collapsed="collapsed"
      :items="sourceLinks"
      orientation="vertical"
      tooltip
      aria-label="Sources"
    />
    <UNavigationMenu
      :collapsed="collapsed"
      :items="managementLinks"
      orientation="vertical"
      tooltip
      aria-label="Manage"
    />
  </div>
</template>

<script setup lang="ts">
import type { NavigationMenuItem } from "@nuxt/ui";

defineProps<{
  collapsed: boolean;
  browsingLinks: NavigationMenuItem[];
  sourceLinks: NavigationMenuItem[];
  managementLinks: NavigationMenuItem[];
}>();
</script>
