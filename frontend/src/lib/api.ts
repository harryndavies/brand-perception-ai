import { useAuthStore } from "@/stores/auth";
import type {
  BrandReport,
  User,
  UsageSummary,
  TeamMember,
  ApiKey,
} from "@/types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token;
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (res.status === 401) {
    useAuthStore.getState().logout();
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ user: User; token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    signup: (name: string, email: string, password: string) =>
      request<{ user: User; token: string }>("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      }),
    me: () => request<User>("/auth/me"),
  },
  reports: {
    list: () => request<BrandReport[]>("/reports"),
    get: (id: string) => request<BrandReport>(`/reports/${id}`),
    create: (brand: string, competitors: string[]) =>
      request<BrandReport>("/reports", {
        method: "POST",
        body: JSON.stringify({ brand, competitors }),
      }),
    stream: (id: string): EventSource => {
      const token = useAuthStore.getState().token;
      const url = `${BASE_URL}/reports/${id}/stream?token=${token}`;
      return new EventSource(url);
    },
  },
  usage: {
    get: () => request<UsageSummary>("/usage"),
  },
  team: {
    list: () => request<TeamMember[]>("/team"),
    invite: (email: string, role: "admin" | "member") =>
      request<TeamMember>("/team/invite", {
        method: "POST",
        body: JSON.stringify({ email, role }),
      }),
    remove: (id: string) =>
      request<void>(`/team/${id}`, { method: "DELETE" }),
  },
  keys: {
    list: () => request<ApiKey[]>("/keys"),
    create: (name: string) =>
      request<ApiKey & { key: string }>("/keys", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    revoke: (id: string) =>
      request<void>(`/keys/${id}`, { method: "DELETE" }),
  },
};
