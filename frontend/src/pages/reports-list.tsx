import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { AnalysisStatus } from "@/types";

const STATUS_VARIANT: Record<AnalysisStatus, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "outline",
  processing: "secondary",
  complete: "default",
  failed: "destructive",
};

export function ReportsListPage() {
  const { data: reports, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: api.reports.list,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground">
            All completed brand analysis reports.
          </p>
        </div>
        <Button render={<Link to="/analysis/new" />}>
          New Analysis
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : !reports?.length ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
          <p className="font-medium">No reports yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Run an analysis to generate your first report.
          </p>
          <Button render={<Link to="/analysis/new" />} className="mt-4">
            New Analysis
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {reports.map((report) => (
            <Link key={report.id} to={`/reports/${report.id}`}>
              <Card className="transition-colors hover:border-foreground/20">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{report.brand}</CardTitle>
                    <Badge variant={STATUS_VARIANT[report.status]}>
                      {report.status}
                    </Badge>
                  </div>
                  <CardDescription>
                    {report.competitors.length > 0
                      ? `vs ${report.competitors.join(", ")}`
                      : "No competitors"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {new Date(report.created_at).toLocaleDateString("en-GB", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    {report.sentiment_score !== null && (
                      <span
                        className={
                          report.sentiment_score >= 0.2
                            ? "text-emerald-500"
                            : report.sentiment_score >= -0.2
                              ? "text-amber-500"
                              : "text-red-500"
                        }
                      >
                        {report.sentiment_score > 0 ? "+" : ""}
                        {report.sentiment_score.toFixed(2)}
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
