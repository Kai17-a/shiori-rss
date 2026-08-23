export type ApiErrorBody = {
  detail?: string | string[] | Record<string, unknown>[];
};

export const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");

export const DEFAULT_REQUEST_TIMEOUT_MS = 20_000;

export const getDefaultApiBase = () => "/api";

export const buildRequestHeaders = (options: RequestInit = {}) => {
  const { headers, ...rest } = options;
  const hasJsonBody = Boolean(rest.body) && !(rest.body instanceof FormData);
  return {
    headers: {
      ...(hasJsonBody ? { "Content-Type": "application/json" } : {}),
      ...(headers || {}),
    } satisfies HeadersInit,
    rest,
  };
};

export const extractErrorMessage = (status: number, body: ApiErrorBody | null) => {
  if (Array.isArray(body?.detail)) {
    return body.detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const message = "msg" in item ? item.msg : undefined;
          if (typeof message === "string" && message.trim()) return message;
          const detail = "detail" in item ? item.detail : undefined;
          if (typeof detail === "string" && detail.trim()) return detail;
        }
        return "Validation error";
      })
      .join(", ");
  }
  if (typeof body?.detail === "string") return body.detail;
  return `HTTP ${status}`;
};

export const parseJsonBody = async <T>(response: Response) =>
  response.json().catch(() => null) as Promise<T | null>;

export const createHttpFetcher = (getBaseUrl: () => string) => {
  const request = async <T = unknown>(path: string, options: RequestInit = {}): Promise<T> => {
    const { headers: mergedHeaders, rest } = buildRequestHeaders(options);
    let response: Response;
    try {
      response = await fetch(`${trimTrailingSlash(getBaseUrl())}${path}`, {
        cache: "no-store",
        ...rest,
        headers: mergedHeaders,
        signal: rest.signal ?? AbortSignal.timeout(DEFAULT_REQUEST_TIMEOUT_MS),
      });
    } catch (error) {
      if (error instanceof DOMException && (error.name === "TimeoutError" || error.name === "AbortError")) {
        throw new Error("The request timed out. Check that the API server is reachable.");
      }
      throw error;
    }
    const body = await parseJsonBody<T>(response);
    if (!response.ok) {
      throw new Error(extractErrorMessage(response.status, body as ApiErrorBody | null));
    }
    return body as T;
  };
  return { request };
};
