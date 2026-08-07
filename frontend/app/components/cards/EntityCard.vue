<template>
  <UCard
    :ui="{
      body: 'space-y-4',
      header: 'space-y-2',
    }"
  >
    <template v-if="body" #body>
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <NuxtLink :to="to" class="truncate text-base font-semibold text-default hover:underline">
            {{ body }}
          </NuxtLink>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <IconButton label="Edit" icon="i-lucide-pencil" @click="$emit('edit')" />
          <IconButton
            label="Delete"
            icon="i-lucide-trash-2"
            color="error"
            variant="soft"
            @click="$emit('remove')"
          />
        </div>
      </div>
    </template>

    <template v-else #header>
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <NuxtLink :to="to" class="truncate text-base font-semibold text-default hover:underline">
            {{ title }}
          </NuxtLink>
          <p class="mt-1 text-sm text-muted">
            {{ meta }}
          </p>
          <p v-if="description" class="mt-2 text-sm text-default">
            {{ description }}
          </p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <IconButton label="Edit" icon="i-lucide-pencil" @click="$emit('edit')" />
          <IconButton
            label="Delete"
            icon="i-lucide-trash-2"
            color="error"
            variant="soft"
            @click="$emit('remove')"
          />
        </div>
      </div>
    </template>
  </UCard>
</template>

<script setup lang="ts">
defineProps<{
  to: string;
  title?: string;
  meta?: string;
  description?: string;
  body?: string;
}>();

defineEmits<{
  edit: [];
  remove: [];
}>();
</script>
