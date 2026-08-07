<template>
  <UModal v-model:open="openModel" :title="title" :description="description">
    <template #content="{ close }">
      <form class="space-y-4 p-6" @submit.prevent="emit('save')">
        <UFormField label="Title" required class="w-full">
          <UInput v-model="form.title" placeholder="Bookmark title" class="w-full" />
        </UFormField>

        <UFormField label="URL" required class="w-full">
          <UInput v-model="form.url" placeholder="https://example.com" class="w-full" />
        </UFormField>

        <UFormField label="Description" class="w-full">
          <UTextarea
            v-model="form.description"
            placeholder="Optional description"
            :rows="4"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Folder" class="w-full">
          <USelectMenu
            v-model="selectedFolderModel"
            :items="folderOptions"
            placeholder="No folder"
            class="w-full"
          />
        </UFormField>

        <UFormField
          label="Tags"
          description="Attach one or more tags to this bookmark."
          class="w-full"
        >
          <USelectMenu
            v-model="form.tag_ids"
            :items="tagOptions"
            placeholder="No tags"
            multiple
            value-key="value"
            class="w-full"
          />
        </UFormField>

        <div class="flex justify-end gap-3">
          <UButton color="neutral" variant="ghost" @click="close"> Cancel </UButton>
          <UButton type="submit" :loading="saving">
            {{ submitLabel }}
          </UButton>
        </div>
      </form>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import type { BookmarkFormState, SelectOption } from "~/utils/bookmarkList";

const openModel = defineModel<boolean>("open", { required: true });
const selectedFolderModel = defineModel<SelectOption | undefined>("selectedFolder", {
  required: true,
});

defineProps<{
  form: BookmarkFormState;
  folderOptions: SelectOption[];
  tagOptions: SelectOption[];
  title: string;
  description: string;
  submitLabel: string;
  saving?: boolean;
}>();

const emit = defineEmits<{
  save: [];
}>();
</script>
