<template>
  <UFormField
    label="Feed icon"
    description="Use an uploaded image or a public image URL. PNG, JPEG, GIF, or WebP; maximum 1 MB."
    class="w-full"
  >
    <div class="space-y-3">
      <div v-if="form.existingIconUrl && !form.removeIcon" class="flex items-center gap-3">
        <img :src="form.existingIconUrl" alt="Current feed icon" class="size-10 rounded-xl object-cover" />
        <span class="text-xs text-muted">Current icon</span>
      </div>
      <UInput
        v-model="form.iconUrl"
        type="url"
        placeholder="https://example.com/icon.png"
        class="w-full"
        @update:model-value="onUrlInput"
      />
      <input
        type="file"
        accept="image/png,image/jpeg,image/gif,image/webp"
        class="block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-elevated file:px-3 file:py-2 file:text-sm file:font-medium file:text-default"
        @change="onFileChange"
      />
      <div class="flex items-center justify-between gap-3">
        <p class="text-xs text-muted">
          {{ form.iconFile?.name || (form.removeIcon ? "The current icon will be removed." : "Upload takes priority over URL.") }}
        </p>
        <UButton
          v-if="form.existingIconUrl || form.iconUrl || form.iconFile"
          type="button"
          label="Remove icon"
          color="neutral"
          variant="ghost"
          size="xs"
          @click="removeIcon"
        />
      </div>
    </div>
  </UFormField>
</template>

<script setup lang="ts">
type IconForm = {
  iconUrl: string;
  iconFile: File | null;
  existingIconUrl: string;
  removeIcon: boolean;
};

const props = defineProps<{ form: IconForm }>();

const onUrlInput = () => {
  props.form.iconFile = null;
  props.form.removeIcon = false;
};

const onFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  props.form.iconFile = input.files?.[0] || null;
  if (props.form.iconFile) {
    props.form.iconUrl = "";
    props.form.removeIcon = false;
  }
};

const removeIcon = () => {
  props.form.iconUrl = "";
  props.form.iconFile = null;
  props.form.removeIcon = true;
};
</script>
