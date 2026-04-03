import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import { getMe } from "@/services/auth";
import { Sidebar } from "./sidebar";
import { cn } from "@/lib/utils";

export function AppLayout() {
  const { token, user, setAuth, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);
  const [loading, setLoading] = useState(!user && !!token);

  useEffect(() => {
    if (token && !user) {
      getMe()
        .then((u) => setAuth(u, token))
        .catch(() => logout())
        .finally(() => setLoading(false));
    }
  }, [token, user, setAuth, logout]);

  if (!token) return <Navigate to="/login" replace />;
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <main
        className={cn(
          "min-h-screen transition-all duration-200",
          collapsed ? "pl-16" : "pl-56"
        )}
      >
        <div className="mx-auto max-w-6xl px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
