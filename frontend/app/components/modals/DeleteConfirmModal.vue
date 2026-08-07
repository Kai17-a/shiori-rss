<template>
  <UModal v-model:open="openModel" :title="title" :description="description">
    <template #content>
      <div class="space-y-4 p-6">
        <slot>
          <p class="text-sm text-default">
            {{ confirmText }}
          </p>
        </slot>
        <div class="flex justify-end gap-3">
          <UButton color="neutral" variant="ghost" @click="close"> Cancel </UButton>
          <UButton color="error" :loading="loading" @click="emit('confirm')">
            {{ confirmLabel }}
          </UButton>
        </div>
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
const openModel = defineModel<boolean>("open", { required: true });

const props = withDefaults(
  defineProps<{
    title: string;
    description?: string;
    subject?: string;
    confirmLabel: string;
    loading?: boolean;
    prompt?: string;
  }>(),
  {
    description: "This action cannot be undone.",
    loading: false,
    prompt: "and remove it from the list?",
  },
);

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

const confirmText = computed(() => {
  if (props.subject) {
    return `Delete ${props.subject} ${props.prompt}`.trim();
  }

  return props.prompt;
});

const close = () => {
  openModel.value = false;
};

watch(openModel, (value, previous) => {
  if (previous && !value) {
    emit("cancel");
  }
});
</script>
