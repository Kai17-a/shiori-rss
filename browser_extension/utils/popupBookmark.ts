export type PopupBookmarkState = {
  title: string;
  url: string;
  description: string;
  folder: number | null;
  tag: number[];
};

export type PopupFetch = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

const bookmarkBody = (state: PopupBookmarkState) => ({
  title: state.title,
  description: state.description,
  folder_id: state.folder,
  tag_ids: state.tag,
});

const jsonRequest = (method: "POST" | "PATCH", body: object): RequestInit => ({
  method,
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify(body),
});

export const createBookmark = (
  apiUrl: string,
  state: PopupBookmarkState,
  request: PopupFetch = fetch,
) =>
  request(
    new URL("/bookmarks", apiUrl),
    jsonRequest("POST", { url: state.url, ...bookmarkBody(state) }),
  );

export const upsertBookmark = async (
  apiUrl: string,
  state: PopupBookmarkState,
  request: PopupFetch = fetch,
) => {
  const url = new URL("/bookmarks/by-url", apiUrl);
  url.searchParams.set("url", state.url);

  const updateResponse = await request(
    url,
    jsonRequest("PATCH", bookmarkBody(state)),
  );
  if (updateResponse.status !== 404) {
    return { operation: "updated" as const, response: updateResponse };
  }

  return {
    operation: "registered" as const,
    response: await createBookmark(apiUrl, state, request),
  };
};

export const initializeConnectedPopup = async (tasks: {
  register: () => Promise<unknown>;
  getFolders: () => Promise<unknown>;
  getTags: () => Promise<unknown>;
}) => {
  await Promise.all([tasks.register(), tasks.getFolders(), tasks.getTags()]);
};

export const createConnectedPopupInitializer = () => {
  const initializedApiOrigins = new Set<string>();

  return async (
    apiUrl: string,
    tasks: Parameters<typeof initializeConnectedPopup>[0],
  ) => {
    const apiOrigin = new URL(apiUrl).origin;
    if (initializedApiOrigins.has(apiOrigin)) {
      return false;
    }

    await initializeConnectedPopup(tasks);
    initializedApiOrigins.add(apiOrigin);
    return true;
  };
};
