import { useState, useRef, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import type { JobStatus } from "@/types";

export function NewAnalysisDialog({ trigger }: { trigger: React.ReactElement }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [brand, setBrand] = useState("");
  const [competitors, setCompetitors] = useState(["", "", ""]);
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState<JobStatus>("idle");
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => { eventSourceRef.current?.close(); };
  }, []);

  function reset() {
    setBrand("");
    setCompetitors(["", "", ""]);
    setIsRunning(false);
    setStatus("idle");
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
        const analysis = data["analysis"];
        if (analysis) {
          setStatus(analysis.status);
        }
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
    [navigate]
  );

  const mutation = useMutation({
    mutationFn: () => {
      const filteredCompetitors = competitors.filter((c) => c.trim());
      return api.reports.create(brand.trim(), filteredCompetitors);
    },
    onSuccess: (report) => {
      connectSSE(report.id);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!brand.trim()) return;

    setIsRunning(true);
    setStatus("pending");
    mutation.mutate();
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

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen && isRunning && status !== "failed") return; // prevent closing while running
        setOpen(nextOpen);
        if (!nextOpen) reset();
      }}
    >
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isRunning ? `Analysing ${brand}` : "New Analysis"}</DialogTitle>
          <DialogDescription>
            {isRunning
              ? "Running brand perception, news sentiment, and competitor analysis."
              : "Enter a brand to analyse its perception using Claude AI."}
          </DialogDescription>
        </DialogHeader>

        {!isRunning ? (
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

            <Button type="submit" className="w-full" disabled={!brand.trim()}>
              Start Analysis
            </Button>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Analysis</span>
              <Badge variant={badgeVariant}>{statusLabel}</Badge>
            </div>
            {status === "running" ? (
              <Progress value={50} className="h-2" />
            ) : status === "complete" ? (
              <Progress value={100} className="h-2" />
            ) : (
              <Progress value={0} className="h-2" />
            )}
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
