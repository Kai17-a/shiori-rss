<template>
  <div class="mx-auto w-full max-w-6xl space-y-6 pb-10">
    <UPageCard class="overflow-hidden" :ui="{ body: 'feed-detail-hero' }">
      <UAlert
        v-if="state === 'error'"
        :title="errorTitle"
        :description="errorDescription"
        color="error"
        variant="soft"
      />

      <UAlert
        v-else-if="state === 'not-found'"
        :title="notFoundTitle"
        :description="notFoundDescription"
        color="warning"
        variant="soft"
      />

      <DetailPageHeader v-else-if="state === 'ready'">
        <template #title><slot name="title" /></template>
        <template #description><slot name="description" /></template>
        <slot name="meta" />
        <template #actions><slot name="actions" /></template>
      </DetailPageHeader>
    </UPageCard>

    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  state: "loading" | "ready" | "error" | "not-found";
  errorTitle: string;
  errorDescription: string;
  notFoundTitle: string;
  notFoundDescription: string;
}>();
</script>
