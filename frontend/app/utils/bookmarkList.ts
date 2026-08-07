import type { BookmarkResponse, FolderResponse } from "~/types";

export type SelectOption = {
  label: string;
  value: string;
};

export type BookmarkFormState = {
  id: string;
  url: string;
  title: string;
  description: string;
  folder_id: string;
  tag_ids: string[];
};

export type PaginationItem =
  | {
      type: "page";
      value: number;
      label: string;
    }
  | {
      type: "ellipsis";
    };

export const createBookmarkFormState = (): BookmarkFormState => ({
  id: "",
  url: "",
  title: "",
  description: "",
  folder_id: "",
  tag_ids: [],
});

export const createEmptyBookmarkForm = createBookmarkFormState;

export const normalizeSelectValue = (value: unknown) => {
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }

  if (value && typeof value === "object" && "value" in value) {
    const raw = (value as { value?: unknown }).value;
    return raw == null ? "" : String(raw);
  }

  return "";
};

export const createSelectOptions = <T>(
  items: readonly T[],
  getLabel: (item: T) => string,
  getValue: (item: T) => string | number,
) =>
  items.map((item) => ({
    label: getLabel(item),
    value: String(getValue(item)),
  })) satisfies SelectOption[];

export const buildBookmarkListPath = (params: {
  search: string;
  folderId: string;
  tagId: string;
  page: number;
}) => {
  const query = new URLSearchParams();

  if (params.folderId) query.set("folder_id", params.folderId);
  if (params.tagId) query.set("tag_id", params.tagId);
  if (params.search.trim()) query.set("q", params.search.trim());
  query.set("page", String(params.page));

  const suffix = query.toString();
  return suffix ? `/bookmarks?${suffix}` : "/bookmarks";
};

export const buildBookmarkQuery = (params: {
  searchQ: string;
  folderId: string;
  tagId: string;
  page: number;
}) =>
  buildBookmarkListPath({
    search: params.searchQ,
    folderId: params.folderId,
    tagId: params.tagId,
    page: params.page,
  });

export const toBookmarkRouteQuery = (params: {
  searchQ: string;
  folderId: string;
  tagId: string;
  page: number;
}) => ({
  query: {
    ...(params.searchQ.trim() ? { q: params.searchQ.trim() } : {}),
    ...(params.folderId ? { folder_id: params.folderId } : {}),
    ...(params.tagId ? { tag_id: params.tagId } : {}),
    ...(params.page > 1 ? { page: String(params.page) } : {}),
  },
});

export const parsePositiveInteger = (value: unknown, fallback = 1) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
};

export const buildPaginationItems = (currentPage: number, totalPages: number): PaginationItem[] => {
  const total = Math.max(totalPages, 1);
  const current = Math.min(Math.max(currentPage, 1), total);
  const items: PaginationItem[] = [];

  if (total <= 7) {
    for (let page = 1; page <= total; page += 1) {
      items.push({ type: "page", value: page, label: String(page) });
    }

    return items;
  }

  items.push({ type: "page", value: 1, label: "1" });

  if (current > 3) {
    items.push({ type: "ellipsis" });
  }

  const middleStart = Math.max(2, current - 1);
  const middleEnd = Math.min(total - 1, current + 1);

  for (let page = middleStart; page <= middleEnd; page += 1) {
    items.push({ type: "page", value: page, label: String(page) });
  }

  if (current < total - 2) {
    items.push({ type: "ellipsis" });
  }

  items.push({ type: "page", value: total, label: String(total) });
  return items;
};

export const mapBookmarksWithFolderNames = (
  bookmarks: BookmarkResponse[],
  folders: FolderResponse[],
) =>
  bookmarks.map((bookmark) => ({
    ...bookmark,
    folder_name: folders.find((folder) => folder.id === bookmark.folder_id)?.name || null,
  }));
