export type ApiErrorBody = {
  detail?: string | string[] | Record<string, unknown>[];
};

export const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");

export const getDefaultApiBase = () => {
  return "/api";
};

export const buildRequestHeaders = (options: RequestInit = {}) => {
  const { headers, ...rest } = options;

  return {
    headers: {
      ...(rest.body ? { "Content-Type": "application/json" } : {}),
      ...(headers || {}),
    } satisfies HeadersInit,
    rest,
  };
};

export const extractErrorMessage = (status: number, body: ApiErrorBody | null) => {
  if (Array.isArray(body?.detail)) {
    return body.detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item && typeof item === "object") {
          const message = "msg" in item ? item.msg : undefined;
          if (typeof message === "string" && message.trim()) {
            return message;
          }

          const detail = "detail" in item ? item.detail : undefined;
          if (typeof detail === "string" && detail.trim()) {
            return detail;
          }
        }

        return "Validation error";
      })
      .join(", ");
  }

  if (typeof body?.detail === "string") {
    return body.detail;
  }

  return `HTTP ${status}`;
};

export const parseJsonBody = async <T>(response: Response) => {
  return response.json().catch(() => null) as Promise<T | null>;
};

export const createHttpFetcher = (getBaseUrl: () => string) => {
  const request = async <T = unknown>(path: string, options: RequestInit = {}): Promise<T> => {
    const { headers: mergedHeaders, rest } = buildRequestHeaders(options);

    const res = await fetch(`${trimTrailingSlash(getBaseUrl())}${path}`, {
      headers: mergedHeaders,
      ...rest,
    });

    const body = await parseJsonBody<T>(res);
    if (!res.ok) {
      throw new Error(extractErrorMessage(res.status, body as ApiErrorBody | null));
    }

    return body as T;
  };

  return { request };
};
