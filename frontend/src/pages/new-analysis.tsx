import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AnalysisJob, JobStatus } from "@/types";

const JOB_LABELS: Record<string, string> = {
  "ai-perception": "AI Perception Analysis",
  "news-sentiment": "News Sentiment Scan",
  "competitor-analysis": "Competitor Analysis",
};

const JOB_ICON: Record<string, React.ReactNode> = {
  "ai-perception": (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M12 2a8 8 0 0 0-8 8c0 6 8 12 8 12s8-6 8-12a8 8 0 0 0-8-8Z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  ),
  "news-sentiment": (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2" />
      <path d="M18 14h-8" />
      <path d="M15 18h-5" />
      <path d="M10 6h8v4h-8V6Z" />
    </svg>
  ),
  "competitor-analysis": (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
};

const STATUS_COLOR: Record<JobStatus, string> = {
  idle: "text-muted-foreground",
  pending: "text-amber-500",
  running: "text-indigo-500",
  complete: "text-emerald-500",
  failed: "text-destructive",
};

const INITIAL_JOBS: AnalysisJob[] = [
  { id: "ai-perception", label: "AI Perception Analysis", status: "idle", progress: 0 },
  { id: "news-sentiment", label: "News Sentiment Scan", status: "idle", progress: 0 },
  { id: "competitor-analysis", label: "Competitor Analysis", status: "idle", progress: 0 },
];

export function NewAnalysisPage() {
  const navigate = useNavigate();
  const [brand, setBrand] = useState("");
  const [competitors, setCompetitors] = useState(["", "", ""]);
  const [isRunning, setIsRunning] = useState(false);
  const [jobs, setJobs] = useState<AnalysisJob[]>(INITIAL_JOBS);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connectSSE = useCallback(
    (reportId: string) => {
      const es = api.reports.stream(reportId);
      eventSourceRef.current = es;

      es.addEventListener("progress", (e) => {
        const data = JSON.parse(e.data) as Record<
          string,
          { id: string; status: JobStatus; progress: number }
        >;
        setJobs((prev) =>
          prev.map((job) => {
            const update = data[job.id];
            if (!update) return job;
            return {
              ...job,
              status: update.status,
              progress: update.progress,
            };
          })
        );
      });

      es.addEventListener("complete", () => {
        es.close();
        // Brief pause so user sees all jobs complete before navigating
        setTimeout(() => navigate(`/reports/${reportId}`), 800);
      });

      es.addEventListener("error", () => {
        es.close();
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
    setJobs(INITIAL_JOBS);
    mutation.mutate();
  }

  function updateCompetitor(index: number, value: string) {
    setCompetitors((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">New Analysis</h1>
        <p className="text-muted-foreground">
          Enter a brand to analyse its perception across AI models and data sources.
        </p>
      </div>

      {!isRunning ? (
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="brand">Brand name</Label>
                <Input
                  id="brand"
                  placeholder="e.g. Arc'teryx, Notion, Stripe..."
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                  autoFocus
                  className="text-base"
                />
              </div>

              <div className="space-y-3">
                <Label>Competitors (optional)</Label>
                <p className="text-sm text-muted-foreground">
                  Add up to 3 competitor brands for comparison.
                </p>
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
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Analysing <span className="text-indigo-500">{brand}</span>
              </CardTitle>
              <CardDescription>
                Running parallel analysis across AI models and data sources.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {jobs.map((job) => (
                <div key={job.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={STATUS_COLOR[job.status]}>
                        {JOB_ICON[job.id]}
                      </span>
                      <span className="text-sm font-medium">
                        {JOB_LABELS[job.id] ?? job.label}
                      </span>
                    </div>
                    <Badge
                      variant={
                        job.status === "complete"
                          ? "default"
                          : job.status === "running"
                            ? "secondary"
                            : "outline"
                      }
                    >
                      {job.status}
                    </Badge>
                  </div>
                  {job.status === "running" ? (
                    <Progress value={job.progress} className="h-1.5" />
                  ) : job.status === "idle" ? (
                    <Skeleton className="h-1.5 w-full" />
                  ) : (
                    <Progress value={100} className="h-1.5" />
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
