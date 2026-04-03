import { useAuthStore } from "@/stores/auth";
import type { BrandReport, User, Schedule, ModelOption } from "@/types";

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
    setApiKey: (api_key: string) =>
      request<{ has_api_key: boolean }>("/auth/api-key", {
        method: "PUT",
        body: JSON.stringify({ api_key }),
      }),
    deleteApiKey: () =>
      request<{ has_api_key: boolean }>("/auth/api-key", {
        method: "DELETE",
      }),
  },
  reports: {
    list: () => request<BrandReport[]>("/reports"),
    get: (id: string) => request<BrandReport>(`/reports/${id}`),
    create: (brand: string, competitors: string[], model: ModelOption = "sonnet") =>
      request<BrandReport>("/reports", {
        method: "POST",
        body: JSON.stringify({ brand, competitors, model }),
      }),
    stream: (id: string): EventSource => {
      const token = useAuthStore.getState().token;
      const url = `${BASE_URL}/reports/${id}/stream?token=${token}`;
      return new EventSource(url);
    },
  },
  schedules: {
    list: () => request<Schedule[]>("/schedules"),
    create: (brand: string, competitors: string[], model: ModelOption, interval_days: number) =>
      request<Schedule>("/schedules", {
        method: "POST",
        body: JSON.stringify({ brand, competitors, model, interval_days }),
      }),
    remove: (id: string) =>
      request<{ ok: boolean }>(`/schedules/${id}`, { method: "DELETE" }),
  },
};
