<template>
  <UDashboardPanel id="favorites">
    <template #header>
      <PageHeaderActions title="Favorites" />
    </template>

    <template #body>
      <div class="space-y-6">
        <UPageCard :ui="{ body: 'space-y-4' }">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold text-default">Favorite bookmarks</h2>
              <p class="text-sm text-muted">
                Bookmarks marked with a star through the dedicated favorite API
              </p>
            </div>
            <RefreshButton :loading="loading" @click="refreshFavorites" />
          </div>

          <div
            class="flex flex-col gap-3 border-b border-default pb-4 md:flex-row md:items-center md:justify-between"
          >
            <p class="text-xs uppercase tracking-[0.08em] text-muted">
              {{ favoriteList.total }} favorites
            </p>
            <p class="text-xs uppercase tracking-[0.08em] text-muted">
              {{ favoriteBookmarks.length }} shown
            </p>
          </div>

          <div
            v-if="loading"
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            Loading favorites...
          </div>

          <div
            v-else-if="loadError"
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            {{ loadError }}
          </div>

          <div
            v-else-if="favoriteBookmarks.length"
            class="grid gap-4 md:grid-cols-2 xl:grid-cols-3"
          >
            <BookmarkCard
              v-for="bookmark in favoriteBookmarksWithFolderNames"
              :key="bookmark.id"
              :bookmark="bookmark"
              :show-folder="true"
              :show-tags="true"
              @edit="loadBookmarkForm"
              @remove="removeBookmark"
              @favorite="toggleFavorite"
            />
          </div>
          <div v-if="pageCount > 1" class="flex items-center justify-between gap-3">
            <p class="text-sm text-muted">Page {{ favoriteList.page }} of {{ pageCount }}</p>
            <div class="flex gap-2">
              <UButton
                color="neutral"
                variant="soft"
                :disabled="favoriteList.page <= 1 || loading"
                @click="setPage(favoriteList.page - 1)"
              >
                Previous
              </UButton>
              <UButton
                color="neutral"
                variant="soft"
                :disabled="favoriteList.page >= pageCount || loading"
                @click="setPage(favoriteList.page + 1)"
              >
                Next
              </UButton>
            </div>
          </div>
          <div
            v-else
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            No favorites yet.
          </div>

          <BookmarkEditorModal
            v-model:open="modalOpen"
            v-model:selected-folder="selectedBookmarkFolder"
            :form="bookmarkForm"
            :folder-options="bookmarkFolderOptions"
            :tag-options="bookmarkTagOptions"
            :title="bookmarkForm.id ? 'Edit bookmark' : 'Register bookmark'"
            :description="
              bookmarkForm.id
                ? 'Update the bookmark details.'
                : 'Create a bookmark and attach tags.'
            "
            :submit-label="saving ? 'Saving...' : 'Save bookmark'"
            :saving="saving"
            @save="saveBookmark"
          />

          <DeleteConfirmModal
            v-model:open="deleteOpen"
            title="Delete bookmark"
            subject="this bookmark"
            confirm-label="Delete bookmark"
            :loading="deleting"
            @cancel="pendingDeleteBookmark = null"
            @confirm="confirmDelete"
          />
        </UPageCard>
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { BookmarkListResponse, BookmarkResponse, FolderResponse, TagResponse } from "~/types";
import { mapBookmarksWithFolderNames } from "~/utils/bookmarkList";

const { request } = useBookmarkApi();
const sidebarCatalog = useSidebarCatalog();
const toast = useSingleToast();

const loading = ref(false);
const loadError = ref("");
const favoriteList = ref<BookmarkListResponse>({
  items: [],
  total: 0,
  page: 1,
  per_page: 20,
  total_pages: 0,
});
const favoriteBookmarks = computed(() => favoriteList.value.items);
const folders = computed<FolderResponse[]>(() => sidebarCatalog.folders.value);
const tags = computed<TagResponse[]>(() => sidebarCatalog.tags.value);
const bookmarkFolderOptions = computed(() => [
  { label: "No folder", value: "" },
  ...folders.value.map((folder) => ({ label: folder.name, value: String(folder.id) })),
]);

const favoriteBookmarksWithFolderNames = computed(() =>
  mapBookmarksWithFolderNames(favoriteBookmarks.value, folders.value),
);
const pageCount = computed(() => Math.max(favoriteList.value.total_pages, 1));

const bookmarkTagOptions = computed(() =>
  tags.value.map((tag) => ({ label: tag.name, value: String(tag.id) })),
);

const loadFavoriteBookmarks = async () => {
  const [bookmarkRes] = await Promise.all([
    request<BookmarkListResponse>(
      `/bookmarks?is_favorite=true&page=${favoriteList.value.page}`,
    ),
    sidebarCatalog.refresh(),
  ]);
  favoriteList.value = bookmarkRes;
};

type LoadToastKind = "loaded" | "refreshed";

async function loadFavorites(showToast = true, toastKind: LoadToastKind = "loaded") {
  loading.value = true;
  loadError.value = "";
  try {
    await loadFavoriteBookmarks();
    if (showToast) {
      toast.show({
        title: toastKind === "loaded" ? "Favorites loaded." : "Favorites refreshed.",
        color: "success",
        icon: "i-lucide-check",
      });
    }
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load favorites.";
    toast.show({
      title: "Failed to load favorites.",
      description: loadError.value,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    loading.value = false;
  }
}

const refreshFavorites = async () => {
  await loadFavorites(true, "refreshed");
};

const setPage = async (page: number) => {
  const nextPage = Math.min(Math.max(page, 1), pageCount.value);
  if (nextPage === favoriteList.value.page) return;

  favoriteList.value.page = nextPage;
  await loadFavorites(false);
};

const {
  bookmarkForm,
  confirmDelete,
  deleteOpen,
  deleting,
  loadBookmarkForm,
  modalOpen,
  pendingDeleteBookmark,
  removeBookmark,
  saveBookmark,
  saving,
} = useBookmarkEditor({
  request,
  refresh: loadFavorites,
  findBookmarkById: (id) => favoriteBookmarks.value.find((item) => item.id === id) || null,
});

const selectedBookmarkFolder = computed({
  get: () =>
    bookmarkFolderOptions.value.find((option) => option.value === bookmarkForm.folder_id),
  set: (value) => {
    bookmarkForm.folder_id = value?.value || "";
  },
});

const toggleFavorite = async (bookmark: BookmarkResponse) => {
  try {
    const updated = await request<BookmarkResponse>("/bookmarks/favorite", {
      method: "PATCH",
      body: JSON.stringify({
        bookmark_id: bookmark.id,
        is_favorite: !bookmark.is_favorite,
      }),
    });

    await loadFavorites(false);

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

onMounted(loadFavorites);
</script>
