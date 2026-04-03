import { useAuthStore } from "@/stores/auth";
import type { BrandReport, User, Schedule, ModelInfo } from "@/types";

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
    setApiKey: (provider: string, api_key: string) =>
      request<{ provider: string; saved: boolean }>("/auth/api-key", {
        method: "PUT",
        body: JSON.stringify({ provider, api_key }),
      }),
    deleteApiKey: (provider: string) =>
      request<{ provider: string; removed: boolean }>(`/auth/api-key/${provider}`, {
        method: "DELETE",
      }),
  },
  reports: {
    list: () => request<BrandReport[]>("/reports"),
    get: (id: string) => request<BrandReport>(`/reports/${id}`),
    models: () => request<ModelInfo[]>("/reports/models"),
    create: (brand: string, competitors: string[], models: string[]) =>
      request<BrandReport>("/reports", {
        method: "POST",
        body: JSON.stringify({ brand, competitors, models }),
      }),
    stream: (id: string): EventSource => {
      const token = useAuthStore.getState().token;
      const url = `${BASE_URL}/reports/${id}/stream?token=${token}`;
      return new EventSource(url);
    },
  },
  schedules: {
    list: () => request<Schedule[]>("/schedules"),
    create: (brand: string, competitors: string[], models: string[], interval_days: number) =>
      request<Schedule>("/schedules", {
        method: "POST",
        body: JSON.stringify({ brand, competitors, models, interval_days }),
      }),
    remove: (id: string) =>
      request<{ ok: boolean }>(`/schedules/${id}`, { method: "DELETE" }),
  },
};
