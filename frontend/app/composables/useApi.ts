import { createHttpFetcher, getDefaultApiBase } from "~/utils/api";

export const useApi = () => {
  const defaultApiBase = getDefaultApiBase();
  const apiBase = ref(defaultApiBase);
  const { request } = createHttpFetcher(() => apiBase.value);

  return { apiBase, defaultApiBase, request };
};
