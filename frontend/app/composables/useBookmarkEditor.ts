import { createBookmarkFormState, type BookmarkFormState } from "~/utils/bookmarkList";
import type { BookmarkResponse } from "~/types";
import { useBookmarkApi } from "~/composables/useBookmarkApi";
import { useSingleToast } from "~/composables/useSingleToast";

type UseBookmarkEditorOptions = {
  request: ReturnType<typeof useBookmarkApi>["request"];
  refresh: (showToast?: boolean) => Promise<void>;
  findBookmarkById: (id: number) => BookmarkResponse | null;
};

export const useBookmarkEditor = (options: UseBookmarkEditorOptions) => {
  const toast = useSingleToast();

  const modalOpen = ref(false);
  const deleteOpen = ref(false);
  const saving = ref(false);
  const deleting = ref(false);
  const pendingDeleteBookmark = ref<BookmarkResponse | null>(null);
  const bookmarkForm = reactive<BookmarkFormState>(createBookmarkFormState());

  const resetBookmarkForm = () => {
    Object.assign(bookmarkForm, createBookmarkFormState());
  };

  const loadBookmarkForm = (bookmark: BookmarkResponse) => {
    bookmarkForm.id = String(bookmark.id);
    bookmarkForm.url = bookmark.url;
    bookmarkForm.title = bookmark.title;
    bookmarkForm.description = bookmark.description || "";
    bookmarkForm.folder_id = bookmark.folder_id ? String(bookmark.folder_id) : "";
    bookmarkForm.tag_ids = bookmark.tags.map((tag) => String(tag.id));
    modalOpen.value = true;
  };

  const openCreateModal = () => {
    resetBookmarkForm();
    modalOpen.value = true;
  };

  const saveBookmark = async () => {
    const url = bookmarkForm.url.trim();
    const title = bookmarkForm.title.trim();

    saving.value = true;
    try {
      const isEditing = Boolean(bookmarkForm.id);
      const path = isEditing ? `/bookmarks/${bookmarkForm.id}` : "/bookmarks";
      await options.request(path, {
        method: isEditing ? "PATCH" : "POST",
        body: JSON.stringify({
          url,
          title,
          description: bookmarkForm.description || null,
          folder_id: bookmarkForm.folder_id ? Number(bookmarkForm.folder_id) : null,
          tag_ids: bookmarkForm.tag_ids.map((tagId) => Number(tagId)),
        }),
      });
      modalOpen.value = false;
      resetBookmarkForm();
      await options.refresh(false);
      toast.show({
        title: isEditing ? "Bookmark updated." : "Bookmark created.",
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

  const removeBookmark = (bookmark: BookmarkResponse | number) => {
    const id = typeof bookmark === "number" ? bookmark : bookmark.id;
    pendingDeleteBookmark.value = options.findBookmarkById(id) || null;
    deleteOpen.value = true;
  };

  const confirmDelete = async () => {
    if (!pendingDeleteBookmark.value) return;
    deleting.value = true;
    try {
      await options.request(`/bookmarks/${pendingDeleteBookmark.value.id}`, { method: "DELETE" });
      deleteOpen.value = false;
      pendingDeleteBookmark.value = null;
      await options.refresh(false);
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
      deleting.value = false;
    }
  };

  return {
    bookmarkForm,
    confirmDelete,
    deleteOpen,
    deleting,
    loadBookmarkForm,
    modalOpen,
    openCreateModal,
    pendingDeleteBookmark,
    removeBookmark,
    resetBookmarkForm,
    saveBookmark,
    saving,
  };
};
