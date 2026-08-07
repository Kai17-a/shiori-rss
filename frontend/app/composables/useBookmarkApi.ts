import { createHttpFetcher, getDefaultApiBase } from "~/utils/bookmarkApi";

export const useBookmarkApi = () => {
  const defaultApiBase = getDefaultApiBase();
  const apiBase = ref(defaultApiBase);

  const { request } = createHttpFetcher(() => apiBase.value);

  return { apiBase, defaultApiBase, request };
};
