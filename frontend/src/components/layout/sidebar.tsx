import { NavLink } from "react-router-dom";
import { LayoutDashboard, FileText, ChevronLeft, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/theme-toggle";
import { ApiKeyDialog } from "@/components/api-key-dialog";
import { Logo } from "@/components/logo";
import { useAuthStore } from "@/stores/auth";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard },
  { label: "Reports", to: "/reports", icon: FileText },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { user, logout } = useAuthStore();

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 flex flex-col border-r bg-background transition-all duration-200",
        collapsed ? "w-16" : "w-56"
      )}
    >
      <div className="flex h-14 items-center px-4">
        {!collapsed ? (
          <Logo className="text-sm" />
        ) : (
          <span className="text-sm font-semibold">P<sup className="text-[0.6em]">AI</sup></span>
        )}
      </div>

      <Separator />

      <nav className="flex-1 space-y-1 px-2 py-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {!collapsed && item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto space-y-2 px-2 pb-4">
        <Separator />
        <div className="flex items-center justify-between px-2 pt-2">
          <ThemeToggle />
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onToggle}>
            <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
          </Button>
        </div>
        {user && (
          <UserProfile user={user} collapsed={collapsed} onLogout={logout} />
        )}
      </div>
    </aside>
  );
}

interface UserProfileProps {
  user: { name: string; has_api_key: boolean };
  collapsed: boolean;
  onLogout: () => void;
}

function UserProfile({ user, collapsed, onLogout }: UserProfileProps) {
  return (
    <div className={cn("flex items-center gap-2 px-2", collapsed && "justify-center")}>
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500/10 text-xs font-medium text-indigo-500">
        {user.name.charAt(0).toUpperCase()}
      </div>
      {!collapsed && (
        <div className="flex-1 truncate">
          <p className="truncate text-xs font-medium">{user.name}</p>
          <div className="flex items-center gap-2">
            <button
              onClick={onLogout}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Sign out
            </button>
            <ApiKeyDialog trigger={
              <button className={cn(
                "text-xs hover:text-foreground",
                user.has_api_key ? "text-emerald-500" : "text-muted-foreground"
              )}>
                <KeyRound className="h-3.5 w-3.5" />
              </button>
            } />
          </div>
        </div>
      )}
    </div>
  );
}
