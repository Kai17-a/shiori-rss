import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import {
  createHttpFetcher,
  buildRequestHeaders,
  getDefaultApiBase,
  extractErrorMessage,
  trimTrailingSlash,
} from "../app/utils/bookmarkApi";

describe("bookmarkApi helpers", () => {
  it("trims trailing slashes from an API base", () => {
    expect(trimTrailingSlash("/api///")).toBe("/api");
    expect(trimTrailingSlash("/api")).toBe("/api");
  });

  it("uses the reverse proxy api base by default", () => {
    expect(getDefaultApiBase()).toBe("/api");
  });

  it("adds JSON content type only when a request body is present", () => {
    expect(buildRequestHeaders({})).toEqual({
      headers: {},
      rest: {},
    });

    expect(
      buildRequestHeaders({
        body: JSON.stringify({ foo: "bar" }),
        headers: { Authorization: "Bearer token" },
      }),
    ).toEqual({
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer token",
      },
      rest: {
        body: JSON.stringify({ foo: "bar" }),
      },
    });
  });

  it("normalizes error payloads into readable messages", () => {
    expect(extractErrorMessage(400, { detail: "Bad request" })).toBe("Bad request");
    expect(extractErrorMessage(400, { detail: ["name is required"] })).toBe("name is required");
    expect(
      extractErrorMessage(422, {
        detail: [
          { msg: "url is not a valid URL" },
          { msg: "title is required" },
        ] as never,
      }),
    ).toBe("url is not a valid URL, title is required");
    expect(extractErrorMessage(500, null)).toBe("HTTP 500");
  });

  it("builds requests from the current base url and handles json responses", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn(async () => {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: fetchMock,
    });

    const baseUrl = ref("/api/");
    const { request } = createHttpFetcher(() => baseUrl.value);

    await expect(request<{ ok: boolean }>("/health")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith("/api/health", expect.any(Object));

    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: originalFetch,
    });
  });

  it("can reach every frontend api path through the shared fetcher", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";

      if (method === "GET" && url.endsWith("/health")) {
        return new Response(JSON.stringify({ status: "ok" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: fetchMock,
    });

    const baseUrl = ref("/api/");
    const { request } = createHttpFetcher(() => baseUrl.value);

    await expect(request("/health")).resolves.toEqual({ status: "ok" });

    const cases = [
      { path: "/bookmarks", options: { method: "GET" } },
      { path: "/bookmarks?per_page=100&page=1", options: { method: "GET" } },
      { path: "/bookmarks/123", options: { method: "GET" } },
      { path: "/bookmarks", options: { method: "POST", body: JSON.stringify({ url: "https://example.com", title: "Example" }) } },
      { path: "/bookmarks/123", options: { method: "PATCH", body: JSON.stringify({ title: "Updated" }) } },
      { path: "/bookmarks/by-url?url=https%3A%2F%2Fexample.com", options: { method: "PATCH", body: JSON.stringify({ title: "Updated by URL" }) } },
      { path: "/bookmarks/123", options: { method: "DELETE" } },
      { path: "/bookmarks?url=https%3A%2F%2Fexample.com", options: { method: "DELETE" } },
      { path: "/bookmarks/favorite", options: { method: "PATCH", body: JSON.stringify({ bookmark_id: 123, is_favorite: true }) } },
      { path: "/bookmarks/123/tags", options: { method: "POST", body: JSON.stringify({ tag_id: 456 }) } },
      { path: "/bookmarks/123/tags/456", options: { method: "DELETE" } },
      { path: "/folders", options: { method: "GET" } },
      { path: "/folders", options: { method: "POST", body: JSON.stringify({ name: "Folder" }) } },
      { path: "/folders/123", options: { method: "GET" } },
      { path: "/folders/123", options: { method: "PATCH", body: JSON.stringify({ name: "Folder 2" }) } },
      { path: "/folders/123", options: { method: "DELETE" } },
      { path: "/tags", options: { method: "GET" } },
      { path: "/tags", options: { method: "POST", body: JSON.stringify({ name: "Tag" }) } },
      { path: "/tags/123", options: { method: "GET" } },
      { path: "/tags/123", options: { method: "PATCH", body: JSON.stringify({ name: "Tag 2" }) } },
      { path: "/tags/123", options: { method: "DELETE" } },
      { path: "/rss-feeds", options: { method: "GET" } },
      { path: "/rss-feeds", options: { method: "POST", body: JSON.stringify({ url: "https://example.com/feed.xml", title: "Feed" }) } },
      { path: "/rss-feeds/123", options: { method: "GET" } },
      { path: "/rss-feeds/123/articles?page=2&per_page=10", options: { method: "GET" } },
      { path: "/rss-feeds/123", options: { method: "PATCH", body: JSON.stringify({ title: "Feed 2" }) } },
      { path: "/rss-feeds/123", options: { method: "DELETE" } },
      { path: "/rss-feeds/123/execute", options: { method: "POST" } },
      { path: "/news-sites", options: { method: "GET" } },
      { path: "/news-sites", options: { method: "POST", body: JSON.stringify({ url: "https://example.com/news" }) } },
      { path: "/news-sites/123", options: { method: "GET" } },
      { path: "/news-sites/123/articles?page=1", options: { method: "GET" } },
      { path: "/news-sites/123", options: { method: "PATCH", body: JSON.stringify({ title: "News", reanalyze: true }) } },
      { path: "/news-sites/123", options: { method: "DELETE" } },
      { path: "/news-sites/123/execute", options: { method: "POST" } },
      { path: "/metrics/dashboard", options: { method: "GET" } },
      { path: "/settings/webhooks", options: { method: "GET" } },
      { path: "/settings/webhooks", options: { method: "POST", body: JSON.stringify({ name: "Test webhook", webhook_url: "https://example.com/webhook" }) } },
      { path: "/settings/webhooks/123", options: { method: "PATCH", body: JSON.stringify({ enabled: false }) } },
      { path: "/settings/webhooks/123", options: { method: "DELETE" } },
      { path: "/settings/webhook/ping", options: { method: "POST", body: JSON.stringify({ webhook_url: "https://example.com/webhook" }) } },
      { path: "/settings/rss-execution", options: { method: "GET" } },
      { path: "/settings/rss-execution", options: { method: "PUT", body: JSON.stringify({ enabled: true }) } },
      { path: "/settings/webhook-summary", options: { method: "GET" } },
      { path: "/settings/webhook-summary", options: { method: "PUT", body: JSON.stringify({ enabled: false }) } },
      { path: "/settings/llm", options: { method: "GET" } },
      { path: "/settings/llm", options: { method: "PUT", body: JSON.stringify({ provider: "ollama", base_url: "http://127.0.0.1:11434", model: "llama3.2" }) } },
      { path: "/settings/llm/test", options: { method: "POST", body: JSON.stringify({}) } },
      { path: "/settings/llm", options: { method: "DELETE" } },
    ] as const;

    for (const testCase of cases) {
      await expect(request(testCase.path, testCase.options)).resolves.toEqual({ ok: true });
    }

    expect(fetchMock).toHaveBeenCalled();

    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: originalFetch,
    });
  });
});
