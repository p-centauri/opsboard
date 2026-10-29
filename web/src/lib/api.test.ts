import { describe, expect, it, vi } from "vitest";

import { api, ApiError, queryString } from "./api";

function respond(status: number, body?: unknown, headers: Record<string, string> = {}) {
  const init = { status, headers: { "content-type": "application/json", ...headers } };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body === undefined ? null : JSON.stringify(body), init)));
}

describe("queryString", () => {
  it("skips empty values and repeats array keys", () => {
    expect(queryString({ q: "", page: 2, status: ["draft", "shipped"], x: null, y: undefined, flag: false })).toBe(
      "?page=2&status=draft&status=shipped&flag=false",
    );
  });

  it("returns an empty string when nothing is set", () => {
    expect(queryString({ q: "", status: [] })).toBe("");
  });

  it("encodes special characters", () => {
    expect(queryString({ q: "100% & co" })).toBe("?q=100%25+%26+co");
  });
});

describe("api", () => {
  it("sends JSON to the same-origin /api proxy and parses the response", async () => {
    respond(200, { id: 1 });
    await expect(api("/orders", { method: "POST", json: { a: 1 } })).resolves.toEqual({ id: 1 });
    expect(fetch).toHaveBeenCalledWith("/api/orders", expect.objectContaining({
      method: "POST",
      body: '{"a":1}',
      credentials: "same-origin",
      headers: { "content-type": "application/json" },
    }));
  });

  it("returns undefined for 204", async () => {
    respond(204);
    await expect(api("/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });

  it("turns the API error shape into an ApiError with field errors", async () => {
    respond(409, { error: { code: "conflict", message: "SKU taken", fields: { sku: "SKU taken" } } });
    const error = await api("/products", { method: "POST", json: {} }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: "conflict", message: "SKU taken", fields: { sku: "SKU taken" } });
  });

  it("gives a readable message when a 5xx has no error body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>Bad gateway</html>", { status: 502 })));
    await expect(api("/orders")).rejects.toMatchObject({ status: 502, code: "http_error", message: "The server had a problem. Try again in a moment." });
  });

  it("reports network failures as status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api("/orders")).rejects.toMatchObject({ status: 0, code: "network_error" });
  });

  it("lets aborts through untouched (cancelled stale requests are not errors)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError")));
    await expect(api("/orders")).rejects.toMatchObject({ name: "AbortError" });
  });
});
