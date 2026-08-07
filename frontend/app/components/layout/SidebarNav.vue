<template>
  <div class="flex h-full flex-col gap-4">
    <UNavigationMenu
      :collapsed="collapsed"
      :items="primaryLinks"
      :model-value="primaryModelValue"
      orientation="vertical"
      tooltip
      popover
    />
    <UNavigationMenu
      :collapsed="collapsed"
      :items="secondaryLinks"
      orientation="vertical"
      tooltip
      class="mt-auto"
    />
  </div>
</template>

<script setup lang="ts">
import type { NavigationMenuItem } from "@nuxt/ui";

defineProps<{
  collapsed: boolean;
  primaryLinks: NavigationMenuItem[];
  secondaryLinks: NavigationMenuItem[];
  primaryModelValue: string[];
}>();
</script>
