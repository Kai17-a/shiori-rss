<template>
  <UTooltip :delay-duration="0" :text="label">
    <UButton
      type="button"
      :size="size"
      :variant="variant"
      :color="color"
      :icon="icon"
      :loading="loading"
      :aria-label="label"
      v-bind="$attrs"
      @click="$emit('click', $event)"
    />
  </UTooltip>
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

withDefaults(
  defineProps<{
    icon: string;
    label: string;
    color?: "primary" | "secondary" | "success" | "info" | "warning" | "error" | "neutral";
    variant?: "solid" | "soft" | "subtle" | "outline" | "ghost";
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    loading?: boolean;
  }>(),
  {
    color: "neutral",
    variant: "ghost",
    size: "xs",
    loading: false,
  },
);

defineEmits<{
  click: [event: MouseEvent];
}>();
</script>
