import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import {
  buildRequestHeaders,
  createHttpFetcher,
  extractErrorMessage,
  getDefaultApiBase,
  trimTrailingSlash,
} from "../app/utils/api";

describe("API helpers", () => {
  it("normalizes the API base and request headers", () => {
    expect(trimTrailingSlash("/api///")).toBe("/api");
    expect(getDefaultApiBase()).toBe("/api");
    expect(buildRequestHeaders({ body: "{}" }).headers).toEqual({
      "Content-Type": "application/json",
    });
    expect(buildRequestHeaders({ body: new FormData() }).headers).toEqual({});
  });

  it("normalizes API errors", () => {
    expect(extractErrorMessage(400, { detail: "Bad request" })).toBe("Bad request");
    expect(extractErrorMessage(500, null)).toBe("HTTP 500");
  });

  it("requests RSS endpoints through the shared fetcher", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    Object.defineProperty(globalThis, "fetch", { configurable: true, value: fetchMock });

    const baseUrl = ref("/api/");
    const { request } = createHttpFetcher(() => baseUrl.value);
    for (const path of [
      "/health",
      "/rss-feeds",
      "/settings/webhooks",
      "/settings/llm",
      "/ai/chat",
    ]) {
      await expect(request(path)).resolves.toEqual({ ok: true });
    }
    expect(fetchMock).toHaveBeenCalledWith("/api/rss-feeds", expect.any(Object));

    Object.defineProperty(globalThis, "fetch", { configurable: true, value: originalFetch });
  });

  it("surfaces a clear error instead of hanging when a request times out", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn(async () => {
      throw new DOMException("The operation timed out.", "TimeoutError");
    });
    Object.defineProperty(globalThis, "fetch", { configurable: true, value: fetchMock });

    const { request } = createHttpFetcher(() => "/api");
    await expect(request("/dashboard")).rejects.toThrow(
      "The request timed out. Check that the API server is reachable.",
    );

    Object.defineProperty(globalThis, "fetch", { configurable: true, value: originalFetch });
  });
});
