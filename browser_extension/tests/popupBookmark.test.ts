import { describe, expect, mock, test } from "bun:test";

import {
  createConnectedPopupInitializer,
  createBookmark,
  initializeConnectedPopup,
  upsertBookmark,
  type PopupFetch,
  type PopupBookmarkState,
} from "../utils/popupBookmark";

const state: PopupBookmarkState = {
  title: "Example",
  url: "https://example.com/article",
  description: "Description",
  folder: 3,
  tag: [5, 8],
};

const response = (status: number) => new Response(null, { status });

describe("popup bookmark requests", () => {
  test("creates a bookmark with numeric folder and tag ids", async () => {
    const request = mock<PopupFetch>(async () => response(201));

    await createBookmark("http://localhost:8000", state, request);

    expect(request).toHaveBeenCalledTimes(1);
    const [url, init] = request.mock.calls[0]!;
    expect(String(url)).toBe("http://localhost:8000/bookmarks");
    expect(JSON.parse(String(init?.body))).toEqual({
      url: state.url,
      title: state.title,
      description: state.description,
      folder_id: 3,
      tag_ids: [5, 8],
    });
  });

  test("updates by URL without creating when the bookmark exists", async () => {
    const request = mock<PopupFetch>(async () => response(200));

    const result = await upsertBookmark(
      "http://localhost:8000",
      state,
      request,
    );

    expect(result.operation).toBe("updated");
    expect(request).toHaveBeenCalledTimes(1);
    expect(String(request.mock.calls[0]![0])).toBe(
      `http://localhost:8000/bookmarks/by-url?url=${encodeURIComponent(state.url)}`,
    );
  });

  test("creates only after update by URL returns 404", async () => {
    const request = mock<PopupFetch>(async () => response(201));
    request.mockResolvedValueOnce(response(404));

    const result = await upsertBookmark(
      "http://localhost:8000",
      state,
      request,
    );

    expect(result.operation).toBe("registered");
    expect(request).toHaveBeenCalledTimes(2);
    expect(String(request.mock.calls[1]![0])).toBe(
      "http://localhost:8000/bookmarks",
    );
  });
});

test("connected popup runs each initialization task once", async () => {
  const register = mock(async () => undefined);
  const getFolders = mock(async () => undefined);
  const getTags = mock(async () => undefined);

  await initializeConnectedPopup({ register, getFolders, getTags });

  expect(register).toHaveBeenCalledTimes(1);
  expect(getFolders).toHaveBeenCalledTimes(1);
  expect(getTags).toHaveBeenCalledTimes(1);
});

test("connected popup initializes only once for the same API origin", async () => {
  const initialize = createConnectedPopupInitializer();
  const register = mock(async () => undefined);
  const getFolders = mock(async () => undefined);
  const getTags = mock(async () => undefined);
  const tasks = { register, getFolders, getTags };

  expect(await initialize("http://localhost:8000", tasks)).toBe(true);
  expect(await initialize("http://localhost:8000/", tasks)).toBe(false);

  expect(register).toHaveBeenCalledTimes(1);
  expect(getFolders).toHaveBeenCalledTimes(1);
  expect(getTags).toHaveBeenCalledTimes(1);
});

test("connected popup initializes a newly selected API origin", async () => {
  const initialize = createConnectedPopupInitializer();
  const register = mock(async () => undefined);
  const getFolders = mock(async () => undefined);
  const getTags = mock(async () => undefined);
  const tasks = { register, getFolders, getTags };

  await initialize("http://localhost:8000", tasks);
  expect(await initialize("http://localhost:9000", tasks)).toBe(true);

  expect(register).toHaveBeenCalledTimes(2);
  expect(getFolders).toHaveBeenCalledTimes(2);
  expect(getTags).toHaveBeenCalledTimes(2);
});
