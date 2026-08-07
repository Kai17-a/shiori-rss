<template>
  <UDashboardPanel id="folder-detail">
    <template #header>
      <PageHeaderActions title="Folder" />
    </template>

    <template #body>
      <div class="space-y-6">
        <UPageCard :ui="{ body: 'space-y-4' }">
          <UAlert
            v-if="state === 'error'"
            title="Failed to load folder"
            :description="errorMessage"
            color="error"
            variant="soft"
          />

          <UAlert
            v-else-if="state === 'not-found'"
            title="Folder not found"
            description="The requested folder does not exist."
            color="warning"
            variant="soft"
          />

          <div v-else-if="folder" class="space-y-3">
            <DetailPageHeader>
              <template #title>
                <h1 class="text-2xl font-semibold text-default">
                  {{ folder.name }}
                </h1>
              </template>

              <template #description>
                <p v-if="folder.description" class="text-sm leading-6 text-default/90">
                  {{ folder.description }}
                </p>
                <p v-else class="text-sm text-muted">No description provided.</p>
              </template>

              <div class="flex flex-wrap items-center gap-2 pt-1">
                <span class="text-sm text-muted">
                  {{ bookmarkTotal }} bookmark{{ bookmarkTotal === 1 ? "" : "s" }}
                </span>
              </div>

              <template #actions>
                <IconButton
                  size="sm"
                  label="Edit"
                  icon="i-lucide-pencil"
                  color="neutral"
                  variant="soft"
                  @click="openEdit"
                />
                <IconButton
                  size="sm"
                  label="Delete"
                  icon="i-lucide-trash-2"
                  color="error"
                  variant="soft"
                  @click="confirmOpen = true"
                />
              </template>
            </DetailPageHeader>
          </div>
        </UPageCard>

        <UPageCard :ui="{ body: 'space-y-3' }">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold text-default">Bookmarks in this folder</h2>
              <p class="text-sm text-muted">Bookmarks associated with the selected folder</p>
            </div>
            <RefreshButton :loading="refreshing" @click="loadFolder(true)" />
          </div>

          <div v-if="bookmarks.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <BookmarkCard
              v-for="bookmark in bookmarks"
              :key="bookmark.id"
              :bookmark="bookmark"
              :show-folder="true"
              :show-tags="true"
              @edit="loadBookmarkForm"
              @remove="askDeleteBookmark"
              @favorite="toggleFavorite"
            />
          </div>
          <div v-if="bookmarkPageCount > 1" class="flex items-center justify-between gap-3">
            <p class="text-sm text-muted">Page {{ bookmarkPage }} of {{ bookmarkPageCount }}</p>
            <div class="flex gap-2">
              <UButton
                color="neutral"
                variant="soft"
                :disabled="bookmarkPage <= 1 || refreshing"
                @click="setBookmarkPage(bookmarkPage - 1)"
              >
                Previous
              </UButton>
              <UButton
                color="neutral"
                variant="soft"
                :disabled="bookmarkPage >= bookmarkPageCount || refreshing"
                @click="setBookmarkPage(bookmarkPage + 1)"
              >
                Next
              </UButton>
            </div>
          </div>
          <div
            v-else
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            <p v-if="state === 'loading' || refreshing">Loading bookmarks</p>
            <p v-else>No bookmarks in this folder.</p>
          </div>
        </UPageCard>

        <EntityEditorModal
          v-model:open="editOpen"
          :form="editForm"
          title="Edit folder"
          description="Rename this folder."
          name-label="Folder name"
          name-placeholder="Folder name"
          description-label="Description"
          description-placeholder="Optional folder description"
          submit-label="Save changes"
          :saving="saving"
          @save="saveFolder"
        />

        <UModal
          v-model:open="editBookmarkOpen"
          title="Edit bookmark"
          description="Update the bookmark details."
        >
          <template #content="{ close }">
            <form class="space-y-4 p-6" @submit.prevent="saveBookmark">
              <UFormField label="URL" required class="w-full">
                <UInput v-model="bookmarkForm.url" class="w-full" />
              </UFormField>

              <UFormField label="Title" required class="w-full">
                <UInput v-model="bookmarkForm.title" class="w-full" />
              </UFormField>

              <UFormField label="Description" class="w-full">
                <UTextarea v-model="bookmarkForm.description" :rows="4" class="w-full" />
              </UFormField>

              <UFormField label="Folder" class="w-full">
                <USelectMenu
                  v-model="selectedBookmarkFolder"
                  :items="bookmarkFolderOptions"
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
                  v-model="bookmarkForm.tag_ids"
                  :items="bookmarkTagOptions"
                  placeholder="No tags"
                  multiple
                  value-key="value"
                  class="w-full"
                />
              </UFormField>

              <div class="flex justify-end gap-3">
                <UButton color="neutral" variant="ghost" @click="close"> Cancel </UButton>
                <UButton type="submit" :loading="saving"> Save bookmark </UButton>
              </div>
            </form>
          </template>
        </UModal>

        <DeleteConfirmModal
          v-model:open="deleteBookmarkOpen"
          title="Delete bookmark"
          :subject="pendingBookmark?.title"
          confirm-label="Delete bookmark"
          :loading="deletingBookmark"
          @cancel="pendingBookmark = null"
          @confirm="confirmDeleteBookmark"
        />

        <DeleteConfirmModal
          v-model:open="confirmOpen"
          title="Delete folder"
          :subject="folder?.name"
          confirm-label="Delete folder"
          :loading="deleting"
          @cancel="confirmOpen = false"
          @confirm="deleteFolder"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { BookmarkListResponse, BookmarkResponse, FolderResponse, TagResponse } from "~/types";
import {
  createBookmarkFormState,
  createSelectOptions,
  normalizeSelectValue,
  type BookmarkFormState,
  type SelectOption,
} from "~/utils/bookmarkList";
import { formatDateTime } from "~/utils/dateTime";

const route = useRoute();
const router = useRouter();
const { request } = useBookmarkApi();
const toast = useSingleToast();
const sidebarCatalog = useSidebarCatalog();
const { refresh: refreshSidebarCatalog } = sidebarCatalog;

const state = ref<"loading" | "ready" | "error" | "not-found">("loading");
const errorMessage = ref("");
const folder = ref<FolderResponse | null>(null);
const bookmarks = ref<BookmarkListResponse["items"]>([]);
const bookmarkTotal = ref(0);
const bookmarkPage = ref(1);
const bookmarkTotalPages = ref(0);
const bookmarkPageCount = computed(() => Math.max(bookmarkTotalPages.value, 1));
const folders = computed<FolderResponse[]>(() => sidebarCatalog.folders.value);
const tags = computed<TagResponse[]>(() => sidebarCatalog.tags.value);
const editOpen = ref(false);
const editBookmarkOpen = ref(false);
const deleteBookmarkOpen = ref(false);
const confirmOpen = ref(false);
const saving = ref(false);
const deleting = ref(false);
const deletingBookmark = ref(false);
const refreshing = ref(false);
const editForm = reactive({ name: "", description: "" });
const bookmarkForm = reactive<BookmarkFormState>(createBookmarkFormState());
const pendingBookmark = ref<BookmarkResponse | null>(null);

const loadFolderCore = async (showToast = false) => {
  state.value = "loading";
  try {
    folder.value = await request<FolderResponse>(`/folders/${route.params.id}`);
    state.value = "ready";
    if (showToast) {
      toast.show({
        title: "Folder refreshed.",
        color: "success",
        icon: "i-lucide-check",
      });
    }
  } catch (err) {
    folder.value = null;
    const message = err instanceof Error ? err.message : "Failed to load folder.";
    errorMessage.value = message;
    state.value = message.includes("404") ? "not-found" : "error";
  }
};

const loadFolderRelations = async () => {
  try {
    const [bookmarksRes] = await Promise.all([
      request<BookmarkListResponse>(
        `/bookmarks?folder_id=${route.params.id}&page=${bookmarkPage.value}`,
      ),
      refreshSidebarCatalog(),
    ]);

    bookmarks.value = bookmarksRes.items || [];
    bookmarkTotal.value = bookmarksRes.total;
    bookmarkPage.value = bookmarksRes.page;
    bookmarkTotalPages.value = bookmarksRes.total_pages;
  } catch (err) {
    bookmarks.value = [];
    bookmarkTotal.value = 0;
    bookmarkTotalPages.value = 0;
    errorMessage.value = err instanceof Error ? err.message : "Failed to load folder relations.";
    state.value = "error";
  }
};

const setBookmarkPage = async (page: number) => {
  const nextPage = Math.min(Math.max(page, 1), bookmarkPageCount.value);
  if (nextPage === bookmarkPage.value) return;

  bookmarkPage.value = nextPage;
  refreshing.value = true;
  try {
    await loadFolderRelations();
  } finally {
    refreshing.value = false;
  }
};

const loadFolder = async (showToast = false) => {
  refreshing.value = true;
  errorMessage.value = "";
  try {
    await Promise.all([loadFolderCore(showToast), loadFolderRelations()]);
  } finally {
    refreshing.value = false;
  }
};

const bookmarkFolderOptions = computed<SelectOption[]>(() => [
  { label: "No folder", value: "" },
  ...createSelectOptions(
    folders.value,
    (item) => item.name,
    (item) => item.id,
  ),
]);

const bookmarkTagOptions = computed<SelectOption[]>(() =>
  createSelectOptions(
    tags.value,
    (item) => item.name,
    (item) => item.id,
  ),
);

const selectedBookmarkFolder = computed<SelectOption | undefined>({
  get: () =>
    bookmarkFolderOptions.value.find((option) => option.value === bookmarkForm.folder_id),
  set: (value) => {
    bookmarkForm.folder_id = normalizeSelectValue(value);
  },
});

const openEdit = () => {
  if (!folder.value) return;
  editForm.name = folder.value.name;
  editForm.description = folder.value.description || "";
  editOpen.value = true;
};

const loadBookmarkForm = (bookmark: BookmarkResponse) => {
  bookmarkForm.id = String(bookmark.id);
  bookmarkForm.url = bookmark.url;
  bookmarkForm.title = bookmark.title;
  bookmarkForm.description = bookmark.description || "";
  bookmarkForm.folder_id = bookmark.folder_id ? String(bookmark.folder_id) : "";
  bookmarkForm.tag_ids = bookmark.tags.map((item) => String(item.id));
  editBookmarkOpen.value = true;
};

const saveBookmark = async () => {
  const url = bookmarkForm.url.trim();
  const title = bookmarkForm.title.trim();
  if (!url || !title) return;

  saving.value = true;
  try {
    await request(`/bookmarks/${bookmarkForm.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        url,
        title,
        description: bookmarkForm.description || null,
        folder_id: bookmarkForm.folder_id ? Number(bookmarkForm.folder_id) : null,
        tag_ids: bookmarkForm.tag_ids.map((item) => Number(item)),
      }),
    });
    editBookmarkOpen.value = false;
    Object.assign(bookmarkForm, createBookmarkFormState());
    await loadFolderRelations();
    toast.show({
      title: "Bookmark updated.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to save bookmark.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
};

const askDeleteBookmark = (bookmark: BookmarkResponse) => {
  pendingBookmark.value = bookmark;
  deleteBookmarkOpen.value = true;
};

const confirmDeleteBookmark = async () => {
  if (!pendingBookmark.value) return;

  deletingBookmark.value = true;
  try {
    await request(`/bookmarks/${pendingBookmark.value.id}`, {
      method: "DELETE",
    });
    deleteBookmarkOpen.value = false;
    pendingBookmark.value = null;
    await loadFolderRelations();
    toast.show({
      title: "Bookmark deleted.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to delete bookmark.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    deletingBookmark.value = false;
  }
};

const toggleFavorite = async (bookmark: BookmarkResponse) => {
  try {
    const updated = await request<BookmarkResponse>("/bookmarks/favorite", {
      method: "PATCH",
      body: JSON.stringify({
        bookmark_id: bookmark.id,
        is_favorite: !bookmark.is_favorite,
      }),
    });

    const index = bookmarks.value.findIndex((item) => item.id === updated.id);
    if (index >= 0) {
      bookmarks.value[index] = updated;
    }

    toast.show({
      title: updated.is_favorite ? "Added to favorites." : "Removed from favorites.",
      color: "success",
      icon: "i-lucide-check",
    });
  } catch (err) {
    toast.show({
      title: "Failed to update favorite.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

const saveFolder = async () => {
  if (!folder.value) return;
  const name = editForm.name.trim();
  if (!name) {
    toast.show({
      title: "Folder name is required.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return;
  }

  saving.value = true;
  try {
    await request(`/folders/${folder.value.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        name,
        description: editForm.description || null,
      }),
    });
    await refreshSidebarCatalog(true);
    await loadFolder();
    editOpen.value = false;
    toast.show({
      title: "Folder updated.",
      color: "success",
      icon: "i-lucide-check",
    });
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

const deleteFolder = async () => {
  if (!folder.value) return;
  deleting.value = true;
  try {
    await request(`/folders/${folder.value.id}`, { method: "DELETE" });
    await refreshSidebarCatalog(true);
    toast.show({
      title: "Folder deleted.",
      color: "success",
      icon: "i-lucide-check",
    });
    await router.push("/folders");
  } catch (err) {
    toast.show({
      title: "Failed to delete folder.",
      description: err instanceof Error ? err.message : undefined,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    deleting.value = false;
    confirmOpen.value = false;
  }
};

watch(
  () => route.params.id,
  () => {
    bookmarkPage.value = 1;
    void loadFolder();
  },
);

onMounted(() => {
  void loadFolder();
});
</script>
