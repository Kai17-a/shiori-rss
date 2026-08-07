<template>
  <UPageCard
    :title="title"
    :to="to"
    variant="subtle"
    :ui="{
      container: 'gap-y-1.5',
      wrapper: 'items-start',
      leading: 'p-2.5 rounded-full bg-primary/10 ring ring-inset ring-primary/25 flex-col',
      title: 'font-normal text-muted text-xs uppercase tracking-[0.2em]',
    }"
    class="rounded-2xl"
  >
    <span class="text-3xl font-semibold text-highlighted">
      {{ value }}
    </span>
  </UPageCard>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  value: number | string;
  to?: string;
}>();
</script>
