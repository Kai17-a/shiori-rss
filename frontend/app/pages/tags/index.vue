<template>
  <UDashboardPanel id="tags">
    <template #header>
      <PageHeaderActions title="Tags" />
    </template>

    <template #body>
      <div class="space-y-6">
        <UPageCard
          title="Create tag"
          description="Add a new tag for organizing bookmarks"
          :ui="{ body: 'space-y-4' }"
        >
          <form class="space-y-3" @submit.prevent="createTag">
            <UInput v-model="tagName" placeholder="New tag name" class="w-full" />
            <UTextarea
              v-model="tagDescription"
              placeholder="Optional tag description"
              :rows="3"
              class="w-full"
            />
            <div class="flex justify-end">
              <UButton type="submit" icon="i-lucide-plus"> Add tag </UButton>
            </div>
          </form>
        </UPageCard>

        <UPageCard :ui="{ body: 'space-y-3' }">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold text-default">Tag list</h2>
            </div>
            <RefreshButton :loading="refreshing" @click="refresh" />
          </div>

          <div v-if="tags.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <EntityCard
              v-for="tag in tags"
              :key="tag.id"
              :title="tag.name"
              :to="`/tags/${tag.id}`"
              :description="tag.description || undefined"
              @edit="openEdit(tag)"
              @remove="askDelete(tag)"
            />
          </div>
          <div
            v-else
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            No tags yet.
          </div>
        </UPageCard>

        <EntityEditorModal
          v-model:open="editOpen"
          :form="editForm"
          title="Edit tag"
          description="Rename the selected tag."
          name-label="Tag name"
          name-placeholder="Tag name"
          description-label="Description"
          description-placeholder="Optional tag description"
          submit-label="Save changes"
          :saving="saving"
          @save="saveEdit"
        />

        <DeleteConfirmModal
          v-model:open="confirmOpen"
          title="Delete tag"
          :subject="pendingTag?.name"
          confirm-label="Delete tag"
          @cancel="pendingTag = null"
          @confirm="confirmDelete"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { TagResponse } from "~/types";

const { request } = useBookmarkApi();
const sidebarCatalog = useSidebarCatalog();
const { refresh: refreshSidebarCatalog } = sidebarCatalog;
const toast = useSingleToast();

const tags = computed<TagResponse[]>(() => sidebarCatalog.tags.value);
const tagName = ref("");
const tagDescription = ref("");
const refreshing = ref(false);
const editOpen = ref(false);
const saving = ref(false);
const confirmOpen = ref(false);
const pendingTag = ref<TagResponse | null>(null);
const editForm = reactive({ id: "", name: "", description: "" });

const refresh = async (force = false) => {
  refreshing.value = true;
  try {
    await refreshSidebarCatalog(force);
    toast.show({
      title: "Tags loaded.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to load tags.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    refreshing.value = false;
  }
};

const createTag = async () => {
  const name = tagName.value.trim();
  if (!name) {
    toast.show({
      title: "Tag name is required.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return;
  }
  try {
    await request("/tags", {
      method: "POST",
      body: JSON.stringify({
        name,
        description: tagDescription.value || null,
      }),
    });
    tagName.value = "";
    tagDescription.value = "";
    await refresh(true);
  } catch (err) {
    toast.show({
      title: "Failed to create tag.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

const openEdit = (tag: TagResponse) => {
  editForm.id = String(tag.id);
  editForm.name = tag.name;
  editForm.description = tag.description || "";
  editOpen.value = true;
};

const closeEdit = () => {
  editOpen.value = false;
  editForm.id = "";
  editForm.name = "";
  editForm.description = "";
};

const saveEdit = async () => {
  const name = editForm.name.trim();
  if (!name) return;
  saving.value = true;
  try {
    await request(`/tags/${editForm.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        name,
        description: editForm.description || null,
      }),
    });
    closeEdit();
    await refresh(true);
  } catch (err) {
    toast.show({
      title: "Failed to update tag.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
};

const askDelete = (tag: TagResponse) => {
  pendingTag.value = tag;
  confirmOpen.value = true;
};

const confirmDelete = async () => {
  if (!pendingTag.value) return;
  try {
    await request(`/tags/${pendingTag.value.id}`, { method: "DELETE" });
    confirmOpen.value = false;
    pendingTag.value = null;
    await refresh(true);
  } catch (err) {
    toast.show({
      title: "Failed to delete tag.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

onMounted(refresh);
</script>
