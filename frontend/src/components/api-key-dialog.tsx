import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const PROVIDERS = [
  { id: "anthropic", label: "Anthropic", placeholder: "sk-ant-..." },
  { id: "openai", label: "OpenAI", placeholder: "sk-..." },
  { id: "google", label: "Google", placeholder: "AIza..." },
] as const;

type ProviderId = (typeof PROVIDERS)[number]["id"];

export function ApiKeyDialog({ trigger }: { trigger: React.ReactElement }) {
  const [open, setOpen] = useState(false);
  const [activeProvider, setActiveProvider] = useState<ProviderId>("anthropic");
  const [key, setKey] = useState("");
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const savedProviders = user?.api_keys ?? [];

  const saveMutation = useMutation({
    mutationFn: () => api.auth.setApiKey(activeProvider, key),
    onSuccess: () => {
      if (user) {
        const updated = [...new Set([...savedProviders, activeProvider])];
        setUser({ ...user, has_api_key: true, api_keys: updated });
      }
      setKey("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (provider: string) => api.auth.deleteApiKey(provider),
    onSuccess: (_, provider) => {
      if (user) {
        const updated = savedProviders.filter((p) => p !== provider);
        setUser({ ...user, has_api_key: updated.length > 0, api_keys: updated });
      }
    },
  });

  const currentProvider = PROVIDERS.find((p) => p.id === activeProvider)!;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>API Keys</DialogTitle>
          <DialogDescription>
            Add API keys for the providers you want to use. Keys are encrypted at rest.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Provider tabs */}
          <div className="flex gap-2">
            {PROVIDERS.map((p) => (
              <button
                key={p.id}
                onClick={() => { setActiveProvider(p.id); setKey(""); }}
                className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors ${
                  activeProvider === p.id
                    ? "border-indigo-500 bg-indigo-500/10 text-indigo-500"
                    : "hover:border-foreground/20"
                }`}
              >
                {p.label}
                {savedProviders.includes(p.id) && (
                  <Badge variant="default" className="ml-1 h-4 px-1 text-[10px]">
                    saved
                  </Badge>
                )}
              </button>
            ))}
          </div>

          {/* Current provider key input */}
          {savedProviders.includes(activeProvider) && (
            <div className="flex items-center justify-between rounded-md border px-3 py-2">
              <span className="text-sm text-muted-foreground">{currentProvider.label} key saved</span>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => deleteMutation.mutate(activeProvider)}
                disabled={deleteMutation.isPending}
              >
                Remove
              </Button>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="api-key">
              {savedProviders.includes(activeProvider) ? "Replace key" : `${currentProvider.label} API key`}
            </Label>
            <Input
              id="api-key"
              type="password"
              placeholder={currentProvider.placeholder}
              value={key}
              onChange={(e) => setKey(e.target.value)}
            />
          </div>

          <Button
            className="w-full"
            disabled={!key.trim() || saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            {saveMutation.isPending ? "Saving..." : `Save ${currentProvider.label} Key`}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
