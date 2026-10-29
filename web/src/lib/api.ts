/**
 * Typed fetch wrapper for the OpsBoard API (proxied same-origin at /api).
 * Every failure becomes an ApiError with the server's { code, message, fields } shape,
 * so screens can show field errors and specific messages without guessing.
 */
import type { components } from "./api-schema";

export type Schemas = components["schemas"];
export type OrderStatus = Schemas["OrderStatus"];
export type Role = Schemas["Role"];
export type User = Schemas["UserOut"];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly fields: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type QueryValue = string | number | boolean | null | undefined | readonly string[];

/** Builds "?a=1&status=x&status=y", skipping empty values. Arrays repeat the key. */
export function queryString(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) value.forEach((v) => search.append(key, v));
    else search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

interface ErrorBody {
  error?: { code?: string; message?: string; fields?: Record<string, string> };
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: ErrorBody | null = null;
  try {
    body = (await response.json()) as ErrorBody;
  } catch {
    // Not JSON (e.g. a proxy error page): fall through to a generic message.
  }
  const error = body?.error;
  if (error?.code && error.message) {
    return new ApiError(response.status, error.code, error.message, error.fields ?? {});
  }
  return new ApiError(
    response.status,
    "http_error",
    response.status >= 500
      ? "The server had a problem. Try again in a moment."
      : `Request failed (${response.status}).`,
  );
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH";
  json?: unknown;
  signal?: AbortSignal;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: options.method ?? "GET",
      headers: options.json === undefined ? undefined : { "content-type": "application/json" },
      body: options.json === undefined ? undefined : JSON.stringify(options.json),
      credentials: "same-origin",
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.");
  }
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function isApiError(error: unknown, code?: string): error is ApiError {
  return error instanceof ApiError && (code === undefined || error.code === code);
}
