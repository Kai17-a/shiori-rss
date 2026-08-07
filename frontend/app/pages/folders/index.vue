<template>
  <UDashboardPanel id="folders">
    <template #header>
      <PageHeaderActions title="Folders" />
    </template>

    <template #body>
      <div class="space-y-6">
        <UPageCard
          title="Create folder"
          description="Add a new folder to organize bookmarks"
          :ui="{ body: 'space-y-4' }"
        >
          <form class="space-y-3" @submit.prevent="createFolder">
            <UInput v-model="folderName" placeholder="New folder name" class="w-full" />
            <UTextarea
              v-model="folderDescription"
              placeholder="Optional folder description"
              :rows="3"
              class="w-full"
            />
            <div class="flex justify-end">
              <UButton type="submit" icon="i-lucide-plus"> Add folder </UButton>
            </div>
          </form>
        </UPageCard>

        <UPageCard :ui="{ body: 'space-y-3' }">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold text-default">Folder list</h2>
              <p class="text-sm text-muted">Browse and manage every folder in one place</p>
            </div>
            <RefreshButton :loading="refreshing" @click="refresh" />
          </div>

          <div v-if="folders.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <EntityCard
              v-for="folder in folders"
              :key="folder.id"
              :title="folder.name"
              :to="`/folders/${folder.id}`"
              :description="folder.description || undefined"
              @edit="openEdit(folder)"
              @remove="askDelete(folder)"
            />
          </div>
          <div
            v-else
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            No folders yet.
          </div>
        </UPageCard>

        <EntityEditorModal
          v-model:open="editOpen"
          :form="editForm"
          title="Edit folder"
          description="Rename the selected folder."
          name-label="Folder name"
          name-placeholder="Folder name"
          description-label="Description"
          description-placeholder="Optional folder description"
          submit-label="Save changes"
          :saving="saving"
          @save="saveEdit"
        />

        <DeleteConfirmModal
          v-model:open="confirmOpen"
          title="Delete folder"
          :subject="pendingFolder?.name"
          confirm-label="Delete folder"
          @cancel="pendingFolder = null"
          @confirm="confirmDelete"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { FolderResponse } from "~/types";

const { request } = useBookmarkApi();
const sidebarCatalog = useSidebarCatalog();
const { refresh: refreshSidebarCatalog } = sidebarCatalog;
const toast = useSingleToast();

const folders = computed<FolderResponse[]>(() => sidebarCatalog.folders.value);
const folderName = ref("");
const folderDescription = ref("");
const refreshing = ref(false);
const editOpen = ref(false);
const saving = ref(false);
const confirmOpen = ref(false);
const pendingFolder = ref<FolderResponse | null>(null);
const editForm = reactive({ id: "", name: "", description: "" });

const refresh = async (force = false) => {
  refreshing.value = true;
  try {
    await refreshSidebarCatalog(force);
    toast.show({
      title: "Folders loaded.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to load folders.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    refreshing.value = false;
  }
};

const createFolder = async () => {
  const name = folderName.value.trim();
  if (!name) {
    toast.show({
      title: "Folder name is required.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return;
  }
  try {
    await request("/folders", {
      method: "POST",
      body: JSON.stringify({
        name,
        description: folderDescription.value || null,
      }),
    });
    folderName.value = "";
    folderDescription.value = "";
    await refresh(true);
  } catch (err) {
    toast.show({
      title: "Failed to create folder.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

const openEdit = (folder: FolderResponse) => {
  editForm.id = String(folder.id);
  editForm.name = folder.name;
  editForm.description = folder.description || "";
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
    await request(`/folders/${editForm.id}`, {
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
      title: "Failed to update folder.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
};

const askDelete = (folder: FolderResponse) => {
  pendingFolder.value = folder;
  confirmOpen.value = true;
};

const confirmDelete = async () => {
  if (!pendingFolder.value) return;
  try {
    await request(`/folders/${pendingFolder.value.id}`, {
      method: "DELETE",
    });
    confirmOpen.value = false;
    pendingFolder.value = null;
    await refresh(true);
  } catch (err) {
    toast.show({
      title: "Failed to delete folder.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

onMounted(refresh);
</script>
