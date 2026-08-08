<template>
  <div class="flex h-full flex-col gap-4">
    <UNavigationMenu
      :collapsed="collapsed"
      :items="primaryLinks"
      :model-value="primaryModelValue"
      @update:model-value="updatePrimaryModelValue"
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

const primaryModelValue = defineModel<string[]>("primaryModelValue", { required: true });
const emit = defineEmits<{ primaryToggle: [value: string] }>();

const updatePrimaryModelValue = (value: string | string[] | undefined) => {
  const nextValue = value === undefined ? [] : Array.isArray(value) ? value : [value];
  const changedValue = [...primaryModelValue.value, ...nextValue].find(
    (item) => primaryModelValue.value.includes(item) !== nextValue.includes(item),
  );
  primaryModelValue.value = nextValue;
  if (changedValue) emit("primaryToggle", changedValue);
};

defineProps<{
  collapsed: boolean;
  primaryLinks: NavigationMenuItem[];
  secondaryLinks: NavigationMenuItem[];
}>();
</script>
