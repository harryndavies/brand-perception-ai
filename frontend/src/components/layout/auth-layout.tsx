import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";

export function AuthLayout() {
  const token = useAuthStore((s) => s.token);

  if (token) return <Navigate to="/" replace />;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-8 w-8 text-indigo-500"
          >
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
          <h1 className="text-lg font-semibold">Perception AI</h1>
          <p className="text-sm text-muted-foreground">
            AI-powered brand perception analysis
          </p>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
