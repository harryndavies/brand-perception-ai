import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import { Logo } from "@/components/logo";

export function AuthLayout() {
  const token = useAuthStore((s) => s.token);

  if (token) return <Navigate to="/" replace />;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <Logo className="text-2xl" />
          <p className="text-sm text-muted-foreground">
            AI-powered brand perception analysis
          </p>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
