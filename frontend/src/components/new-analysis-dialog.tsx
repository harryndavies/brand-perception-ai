import { useState, useRef, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
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
import type { JobStatus } from "@/types";

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  google: "Google",
};

export function NewAnalysisDialog({ trigger }: { trigger: React.ReactElement }) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const hasKey = user?.has_api_key ?? false;
  const userProviders = user?.api_keys ?? [];
  const [open, setOpen] = useState(false);
  const [brand, setBrand] = useState("");
  const [competitors, setCompetitors] = useState(["", "", ""]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [repeatMonthly, setRepeatMonthly] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState<JobStatus>("idle");
  const [modelStatuses, setModelStatuses] = useState<Record<string, JobStatus>>({});
  const eventSourceRef = useRef<EventSource | null>(null);

  const { data: availableModels } = useQuery({
    queryKey: ["models"],
    queryFn: api.reports.models,
    staleTime: 60_000,
  });

  // Filter to models the user has keys for
  const userModels = (availableModels ?? []).filter((m) =>
    userProviders.includes(m.provider)
  );

  // Set default selection when models load
  useEffect(() => {
    if (userModels.length > 0 && selectedModels.length === 0) {
      setSelectedModels([userModels[0].key]);
    }
  }, [userModels.length]);

  useEffect(() => {
    return () => { eventSourceRef.current?.close(); };
  }, []);

  function reset() {
    setBrand("");
    setCompetitors(["", "", ""]);
    setSelectedModels(userModels.length > 0 ? [userModels[0].key] : []);
    setRepeatMonthly(false);
    setIsRunning(false);
    setStatus("idle");
    setModelStatuses({});
    eventSourceRef.current?.close();
  }

  const connectSSE = useCallback(
    (reportId: string) => {
      const es = api.reports.stream(reportId);
      eventSourceRef.current = es;

      es.addEventListener("progress", (e) => {
        const data = JSON.parse(e.data) as Record<
          string,
          { id: string; status: JobStatus; progress: number }
        >;
        setModelStatuses(
          Object.fromEntries(
            Object.entries(data).map(([k, v]) => [k, v.status])
          )
        );
        // Overall status: if any running, show running
        const statuses = Object.values(data).map((v) => v.status);
        if (statuses.includes("running")) setStatus("running");
        else if (statuses.every((s) => s === "complete")) setStatus("complete");
      });

      es.addEventListener("complete", () => {
        es.close();
        setTimeout(() => {
          setOpen(false);
          reset();
          navigate(`/reports/${reportId}`);
        }, 600);
      });

      es.addEventListener("error", () => {
        es.close();
        setStatus("failed");
      });
    },
    [navigate, userModels]
  );

  const mutation = useMutation({
    mutationFn: async () => {
      const filteredCompetitors = competitors.filter((c) => c.trim());
      const report = await api.reports.create(brand.trim(), filteredCompetitors, selectedModels);
      if (repeatMonthly) {
        await api.schedules.create(brand.trim(), filteredCompetitors, selectedModels, 30);
      }
      return report;
    },
    onSuccess: (report) => {
      connectSSE(report.id);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!brand.trim() || selectedModels.length === 0) return;

    setIsRunning(true);
    setStatus("pending");
    mutation.mutate();
  }

  function toggleModel(key: string) {
    const model = availableModels?.find((m) => m.key === key);
    if (!model) return;

    setSelectedModels((prev) => {
      if (prev.includes(key)) {
        // Deselect — but don't allow empty selection
        const next = prev.filter((k) => k !== key);
        return next.length > 0 ? next : prev;
      }
      // Replace any existing model from the same provider
      const otherProviders = prev.filter((k) => {
        const m = availableModels?.find((am) => am.key === k);
        return m?.provider !== model.provider;
      });
      return [...otherProviders, key];
    });
  }

  function updateCompetitor(index: number, value: string) {
    setCompetitors((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }

  const statusLabel =
    status === "pending" ? "Queued" :
    status === "running" ? "Analysing" :
    status === "complete" ? "Complete" :
    status === "failed" ? "Failed" : "Waiting";

  const badgeVariant =
    status === "complete" ? "default" as const :
    status === "failed" ? "destructive" as const :
    status === "running" ? "secondary" as const :
    "outline" as const;

  // Group available models by provider
  const modelsByProvider = userModels.reduce<Record<string, typeof userModels>>((acc, m) => {
    (acc[m.provider] ??= []).push(m);
    return acc;
  }, {});

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen && isRunning && status !== "failed") return;
        setOpen(nextOpen);
        if (!nextOpen) reset();
      }}
    >
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isRunning ? `Analysing ${brand}` : "New Analysis"}</DialogTitle>
          <DialogDescription>
            {isRunning
              ? `Running analysis across ${selectedModels.length} model${selectedModels.length > 1 ? "s" : ""}.`
              : "Enter a brand and select one model per provider to compare."}
          </DialogDescription>
        </DialogHeader>

        {!isRunning ? (
          !hasKey ? (
            <div className="space-y-3 text-center py-2">
              <p className="text-sm text-muted-foreground">
                Add at least one API key to run analyses. Click the key icon in the sidebar.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="brand">Brand name</Label>
                <Input
                  id="brand"
                  placeholder="e.g. Arc'teryx, Notion, Stripe..."
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="space-y-2">
                <Label>Competitors (optional)</Label>
                {competitors.map((comp, i) => (
                  <Input
                    key={i}
                    placeholder={`Competitor ${i + 1}`}
                    value={comp}
                    onChange={(e) => updateCompetitor(i, e.target.value)}
                  />
                ))}
              </div>

              <div className="space-y-2">
                <Label>Models</Label>
                <div className="space-y-3">
                  {Object.entries(modelsByProvider).map(([provider, models]) => (
                    <div key={provider} className="space-y-1.5">
                      <p className="text-xs font-medium text-muted-foreground">
                        {PROVIDER_LABELS[provider] ?? provider}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {models.map((m) => (
                          <button
                            key={m.key}
                            type="button"
                            onClick={() => toggleModel(m.key)}
                            className={`rounded-md border px-3 py-1.5 text-sm transition-colors ${
                              selectedModels.includes(m.key)
                                ? "border-indigo-500 bg-indigo-500/10 text-indigo-500"
                                : "hover:border-foreground/20"
                            }`}
                          >
                            {m.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <div>
                  <Label htmlFor="repeat" className="text-sm font-medium">Repeat monthly</Label>
                  <p className="text-xs text-muted-foreground">Auto-run this analysis every 30 days</p>
                </div>
                <Switch
                  id="repeat"
                  checked={repeatMonthly}
                  onCheckedChange={setRepeatMonthly}
                />
              </div>

              <Button type="submit" className="w-full" disabled={!brand.trim() || selectedModels.length === 0}>
                {selectedModels.length > 1
                  ? `Run ${selectedModels.length} Models`
                  : "Start Analysis"}
              </Button>
            </form>
          )
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Overall</span>
              <Badge variant={badgeVariant}>{statusLabel}</Badge>
            </div>

            {selectedModels.map((mk) => {
              const modelInfo = availableModels?.find((m) => m.key === mk);
              const ms = modelStatuses[mk] ?? "pending";
              return (
                <div key={mk} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span>{modelInfo?.label ?? mk}</span>
                    <Badge variant={
                      ms === "complete" ? "default" :
                      ms === "running" ? "secondary" : "outline"
                    }>
                      {ms}
                    </Badge>
                  </div>
                  <Progress
                    value={ms === "complete" ? 100 : ms === "running" ? 50 : 0}
                    className="h-1.5"
                  />
                </div>
              );
            })}

            {status === "failed" && (
              <div className="space-y-2">
                <p className="text-sm text-destructive">
                  Something went wrong. Please try again.
                </p>
                <Button variant="outline" className="w-full" onClick={reset}>
                  Try Again
                </Button>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
