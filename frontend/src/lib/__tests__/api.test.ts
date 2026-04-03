import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAuthStore } from "@/stores/auth";

// Must import api after mocking fetch
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

const { api } = await import("../api");

function mockResponse(data: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  });
}

describe("api client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  it("sends auth header when token exists", async () => {
    const user = { id: "1", email: "a@b.com", name: "T", team: "D", has_api_key: false, api_keys: [] };
    useAuthStore.getState().setAuth(user, "my-token");
    mockResponse(user);

    await api.auth.me();

    const headers = mockFetch.mock.calls[0][1].headers;
    expect(headers.Authorization).toBe("Bearer my-token");
  });

  it("does not send auth header when no token", async () => {
    mockResponse({ user: {}, token: "t" });

    await api.auth.login("a@b.com", "pass");

    const headers = mockFetch.mock.calls[0][1].headers;
    expect(headers.Authorization).toBeUndefined();
  });

  it("calls logout on 401 response", async () => {
    const user = { id: "1", email: "a@b.com", name: "T", team: "D", has_api_key: false, api_keys: [] };
    useAuthStore.getState().setAuth(user, "my-token");
    mockResponse(null, 401);

    await expect(api.auth.me()).rejects.toThrow("Unauthorized");
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("throws on non-ok response", async () => {
    mockResponse(null, 500);
    await expect(api.reports.list()).rejects.toThrow("API error: 500");
  });

  it("auth.signup sends correct payload", async () => {
    mockResponse({ user: { id: "1" }, token: "t" });

    await api.auth.signup("Name", "a@b.com", "pass123");

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain("/auth/signup");
    expect(JSON.parse(opts.body)).toEqual({
      name: "Name",
      email: "a@b.com",
      password: "pass123",
    });
  });

  it("reports.create sends brand and competitors", async () => {
    mockResponse({ id: "r1", brand: "Nike" });

    await api.reports.create("Nike", ["Adidas"], ["claude-sonnet"]);

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain("/reports");
    expect(JSON.parse(opts.body)).toEqual({
      brand: "Nike",
      competitors: ["Adidas"],
      models: ["claude-sonnet"],
    });
  });

  it("reports.stream returns EventSource with token", () => {
    const user = { id: "1", email: "a@b.com", name: "T", team: "D", has_api_key: false, api_keys: [] };
    useAuthStore.getState().setAuth(user, "stream-token");

    // EventSource not available in jsdom, so we just test the URL construction
    const originalEventSource = globalThis.EventSource;
    let capturedUrl = "";
    globalThis.EventSource = class {
      constructor(url: string) {
        capturedUrl = url;
      }
    } as unknown as typeof EventSource;

    api.reports.stream("report-123");
    expect(capturedUrl).toContain("/reports/report-123/stream?token=stream-token");

    globalThis.EventSource = originalEventSource;
  });
});
