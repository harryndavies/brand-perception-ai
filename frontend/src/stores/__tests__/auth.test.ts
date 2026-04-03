import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore } from "../auth";

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  it("starts with no user and reads token from localStorage", () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
  });

  it("setAuth stores user and token", () => {
    const user = { id: "1", email: "a@b.com", name: "Test", team: "Default", has_api_key: false, api_keys: [] };
    useAuthStore.getState().setAuth(user, "tok123");

    const state = useAuthStore.getState();
    expect(state.user).toEqual(user);
    expect(state.token).toBe("tok123");
    expect(localStorage.getItem("token")).toBe("tok123");
  });

  it("logout clears user, token, and localStorage", () => {
    const user = { id: "1", email: "a@b.com", name: "Test", team: "Default", has_api_key: false, api_keys: [] };
    useAuthStore.getState().setAuth(user, "tok123");
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(localStorage.getItem("token")).toBeNull();
  });
});
