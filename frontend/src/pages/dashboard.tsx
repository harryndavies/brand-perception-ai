import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { NewAnalysisDialog } from "@/components/new-analysis-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { AnalysisStatus, BrandReport } from "@/types";

const STATUS_VARIANT: Record<AnalysisStatus, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "outline",
  processing: "secondary",
  complete: "default",
  failed: "destructive",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function SentimentBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-muted-foreground">--</span>;
  const label = score >= 0.5 ? "Positive" : score >= 0 ? "Neutral" : "Negative";
  const color =
    score >= 0.5
      ? "text-emerald-600 dark:text-emerald-400"
      : score >= 0
        ? "text-muted-foreground"
        : "text-red-500";
  return <span className={color}>{label} ({score > 0 ? "+" : ""}{score.toFixed(2)})</span>;
}

function StatsCards({ reports, isLoading }: { reports: BrandReport[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        {[0, 1].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-7 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const completed = reports.filter((r) => r.status === "complete");
  const avgSentiment =
    completed.length > 0
      ? completed.reduce((sum, r) => sum + (r.sentiment_score ?? 0), 0) / completed.length
      : null;

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>Total Analyses</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{reports.length}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>Average Sentiment</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">
            {avgSentiment !== null
              ? `${avgSentiment > 0 ? "+" : ""}${avgSentiment.toFixed(2)}`
              : "--"}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function ReportsTable({ reports, isLoading }: { reports: BrandReport[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-muted-foreground">
            <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
            <path d="M14 2v4a2 2 0 0 0 2 2h4" />
          </svg>
        </div>
        <p className="font-medium">No analyses yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Run your first brand analysis to get started.
        </p>
        <NewAnalysisDialog trigger={<Button className="mt-4">New Analysis</Button>} />
      </div>
    );
  }

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Brand</TableHead>
            <TableHead>Competitors</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Sentiment</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {reports.map((report) => (
            <TableRow key={report.id}>
              <TableCell className="font-medium">{report.brand}</TableCell>
              <TableCell className="text-muted-foreground">
                {report.competitors.length > 0
                  ? report.competitors.join(", ")
                  : "--"}
              </TableCell>
              <TableCell>
                <Badge variant={STATUS_VARIANT[report.status]}>
                  {report.status}
                </Badge>
              </TableCell>
              <TableCell>
                <SentimentBadge score={report.sentiment_score} />
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatDate(report.created_at)}
              </TableCell>
              <TableCell>
                {report.status === "complete" && (
                  <Button variant="ghost" size="sm" render={<Link to={`/reports/${report.id}`} />}>
                    View
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function DashboardPage() {
  const { data: reports, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: api.reports.list,
  });

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your brand analysis runs.
          </p>
        </div>
        <NewAnalysisDialog trigger={
          <Button>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2 h-4 w-4">
              <path d="M5 12h14" />
              <path d="M12 5v14" />
            </svg>
            New Analysis
          </Button>
        } />
      </div>

      <StatsCards reports={reports ?? []} isLoading={isLoading} />
      <ReportsTable reports={reports ?? []} isLoading={isLoading} />
    </div>
  );
}
