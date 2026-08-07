<template>
  <UDashboardPanel id="bookmarks">
    <template #header>
      <PageHeaderActions title="Bookmarks" />
    </template>

    <template #body>
      <div class="space-y-6">
        <UPageCard
          title="Search & filters"
          description="Filter bookmarks by keyword, folder, or tag"
          :ui="{ body: 'space-y-4' }"
        >
          <form class="grid gap-3 lg:grid-cols-[2fr_1fr_1fr]">
            <UInput v-model="searchQ" placeholder="Search by title or URL" />
            <USelectMenu
              v-model="selectedFilterFolder"
              :items="filterFolderOptions"
              placeholder="All folders"
            />
            <USelectMenu
              v-model="selectedFilterTag"
              :items="filterTagOptions"
              placeholder="All tags"
            />
          </form>
        </UPageCard>

        <UPageCard :ui="{ body: 'space-y-4' }">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0">
              <h2 class="text-lg font-semibold text-default">Bookmark list</h2>
              <p class="text-sm text-muted">Latest bookmarks matching the current filters</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <RefreshButton :loading="loading" @click="refreshBookmarks" />
              <UButton label="Register" icon="i-lucide-plus" size="sm" @click="openCreateModal" />
            </div>
          </div>

          <div
            class="flex flex-col gap-3 border-b border-default pb-4 md:flex-row md:items-center md:justify-between"
          >
            <p class="text-xs uppercase tracking-[0.08em] text-muted">
              Page {{ bookmarkList.page }} of
              {{ pageCount }}
            </p>
            <div class="flex items-center gap-2">
              <UButton
                size="sm"
                variant="ghost"
                color="neutral"
                :disabled="page <= 1 || loading"
                @click="setPage(page - 1)"
              >
                Prev
              </UButton>
              <template
                v-for="(item, index) in paginationItems"
                :key="`${item.type}-${index}-${item.type === 'page' ? item.value : 'ellipsis'}`"
              >
                <UButton
                  v-if="item.type === 'page'"
                  size="sm"
                  :color="item.value === page ? 'primary' : 'neutral'"
                  :variant="item.value === page ? 'solid' : 'ghost'"
                  :disabled="loading"
                  @click="setPage(item.value)"
                >
                  {{ item.label }}
                </UButton>
                <UButton v-else size="sm" variant="ghost" color="neutral" disabled> ... </UButton>
              </template>
              <UButton
                size="sm"
                variant="ghost"
                color="neutral"
                :disabled="page >= pageCount || loading"
                @click="setPage(page + 1)"
              >
                Next
              </UButton>
            </div>
          </div>

          <div v-if="bookmarkList.items.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <BookmarkCard
              v-for="bookmark in bookmarkCards"
              :key="bookmark.id"
              :bookmark="bookmark"
              :show-folder="true"
              :show-tags="true"
              @edit="loadBookmarkForm"
              @remove="removeBookmark"
              @favorite="toggleFavorite"
            />
          </div>

          <div
            v-else
            class="rounded-2xl border border-dashed border-default p-6 text-sm text-muted"
          >
            <p v-if="loading">Loading bookmarks...</p>
            <p v-else-if="loadError">
              {{ loadError }}
            </p>
            <p v-else>No bookmarks yet.</p>
          </div>
        </UPageCard>

        <BookmarkEditorModal
          v-model:open="modalOpen"
          v-model:selected-folder="selectedBookmarkFolder"
          :form="bookmarkForm"
          :folder-options="bookmarkFolderOptions"
          :tag-options="bookmarkTagOptions"
          :title="bookmarkForm.id ? 'Edit bookmark' : 'Register bookmark'"
          :description="
            bookmarkForm.id ? 'Update the bookmark details.' : 'Create a bookmark and attach tags.'
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
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { BookmarkListResponse, BookmarkResponse, FolderResponse, TagResponse } from "~/types";
import {
  buildBookmarkQuery,
  buildPaginationItems,
  createSelectOptions,
  mapBookmarksWithFolderNames,
  normalizeSelectValue,
  parsePositiveInteger,
  toBookmarkRouteQuery,
  type PaginationItem,
} from "~/utils/bookmarkList";

const route = useRoute();
const router = useRouter();
const { request } = useBookmarkApi();
const sidebarCatalog = useSidebarCatalog();
const toast = useSingleToast();

const loading = ref(false);
const loadError = ref("");
const bookmarkList = ref<BookmarkListResponse>({
  items: [],
  total: 0,
  page: 1,
  per_page: 20,
  total_pages: 0,
});
const folders = computed<FolderResponse[]>(() => sidebarCatalog.folders.value);
const tags = computed<TagResponse[]>(() => sidebarCatalog.tags.value);
const searchQ = ref(String(route.query.q || ""));
const filterFolder = ref(String(route.query.folder_id || ""));
const filterTag = ref(String(route.query.tag_id || ""));
const page = ref(parsePositiveInteger(route.query.page, 1));
type SelectOption = {
  label: string;
  value: string;
};
const filterFolderOptions = computed(() => [
  { label: "All folders", value: "" },
  ...createSelectOptions(
    folders.value,
    (folder) => folder.name,
    (folder) => folder.id,
  ),
]);

const filterTagOptions = computed(() => [
  { label: "All tags", value: "" },
  ...createSelectOptions(
    tags.value,
    (tag) => tag.name,
    (tag) => tag.id,
  ),
]);

const selectedFilterFolder = computed<SelectOption | undefined>({
  get: () =>
    filterFolderOptions.value.find((option) => option.value === filterFolder.value),
  set: (value) => {
    filterFolder.value = normalizeSelectValue(value);
  },
});

const selectedFilterTag = computed<SelectOption | undefined>({
  get: () => filterTagOptions.value.find((option) => option.value === filterTag.value),
  set: (value) => {
    filterTag.value = normalizeSelectValue(value);
  },
});
const bookmarkFolderOptions = computed(() => [
  { label: "No folder", value: "" },
  ...createSelectOptions(
    folders.value,
    (folder) => folder.name,
    (folder) => folder.id,
  ),
]);

const bookmarkTagOptions = computed(() => [
  ...createSelectOptions(
    tags.value,
    (tag) => tag.name,
    (tag) => tag.id,
  ),
]);

const {
  bookmarkForm,
  confirmDelete,
  deleteOpen,
  deleting,
  loadBookmarkForm,
  modalOpen,
  openCreateModal,
  pendingDeleteBookmark,
  removeBookmark,
  saveBookmark,
  saving,
} = useBookmarkEditor({
  request,
  refresh: loadData,
  findBookmarkById: (id) => bookmarkCards.value.find((bookmark) => bookmark.id === id) || null,
});

const selectedBookmarkFolder = computed<SelectOption | undefined>({
  get: () =>
    bookmarkFolderOptions.value.find((option) => option.value === bookmarkForm.folder_id),
  set: (value) => {
    bookmarkForm.folder_id = value?.value || "";
  },
});

const bookmarkCards = computed(() =>
  mapBookmarksWithFolderNames(bookmarkList.value.items, folders.value),
);

const pageCount = computed(() =>
  Math.max(Math.ceil(bookmarkList.value.total / Math.max(bookmarkList.value.per_page, 1)), 1),
);

const paginationItems = computed<PaginationItem[]>(() =>
  buildPaginationItems(page.value, pageCount.value),
);

type LoadToastKind = "loaded" | "refreshed";
let loadRequestId = 0;

async function loadData(showToast = true, toastKind: LoadToastKind = "loaded") {
  const requestId = ++loadRequestId;
  loading.value = true;
  loadError.value = "";

  void sidebarCatalog.refresh();

  try {
    const bookmarkRes = await request<BookmarkListResponse>(
      buildBookmarkQuery({
        searchQ: searchQ.value,
        folderId: filterFolder.value,
        tagId: filterTag.value,
        page: page.value,
      }),
    );

    if (requestId !== loadRequestId) return;

    const resolvedPage = Math.min(
      Math.max(bookmarkRes.page, 1),
      Math.max(bookmarkRes.total_pages, 1),
    );
    if (resolvedPage !== page.value) {
      page.value = resolvedPage;
      return;
    }

    bookmarkList.value = bookmarkRes;

    if (showToast) {
      toast.show({
        title: toastKind === "loaded" ? "Bookmarks loaded." : "Bookmarks refreshed.",
        color: "success",
        icon: "i-lucide-check",
      });
    }
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load bookmarks.";
    toast.show({
      title: "Failed to load bookmarks.",
      description: loadError.value,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    if (requestId === loadRequestId) {
      loading.value = false;
    }
  }
}

const refreshBookmarks = async () => {
  await loadData(true, "refreshed");
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

    const index = bookmarkList.value.items.findIndex((item) => item.id === updated.id);
    if (index >= 0) {
      bookmarkList.value.items[index] = updated;
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

const setPage = async (nextPage: number) => {
  const next = Math.min(Math.max(nextPage, 1), pageCount.value);
  if (next === page.value) return;
  page.value = next;
};

onMounted(() => {
  void loadData(true);
});

watch(
  [searchQ, filterFolder, filterTag, page],
  async ([nextSearch, nextFolder, nextTag, nextPage]) => {
    await router.replace(
      toBookmarkRouteQuery({
        searchQ: nextSearch,
        folderId: nextFolder,
        tagId: nextTag,
        page: nextPage,
      }),
    );
    await loadData(true);
  },
);

watch(
  () => route.query.page,
  async (next) => {
    const nextPage = parsePositiveInteger(next, 1);
    if (nextPage !== page.value) {
      page.value = nextPage;
    }
  },
);
</script>
