import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScoreCard } from "@/components/report/score-card";
import { SentimentGauge } from "@/components/report/sentiment-gauge";
import { PillarCards } from "@/components/report/pillar-cards";
import { ModelComparison } from "@/components/report/model-comparison";
import { CompetitorChart } from "@/components/report/competitor-chart";
import { TrendChart } from "@/components/report/trend-chart";
import { api } from "@/lib/api";
import type { BrandReport } from "@/types";

function ReportSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-72" />
      <div className="grid gap-4 sm:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-40" />
        ))}
      </div>
    </div>
  );
}

function ReportContent({ report }: { report: BrandReport }) {
  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">
              {report.brand}
            </h1>
            <Badge>Complete</Badge>
            {report.models?.map((m) => (
              <Badge key={m} variant="outline">{m}</Badge>
            ))}
          </div>
          <p className="mt-1 text-muted-foreground">
            Analysis completed{" "}
            {report.completed_at
              ? new Date(report.completed_at).toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })
              : ""}
            {report.competitors.length > 0 && (
              <> · vs {report.competitors.join(", ")}</>
            )}
          </p>
        </div>
        <Button variant="outline" render={<Link to="/" />}>
          Back to Dashboard
        </Button>
      </div>

      {report.scores && <ScoreCard scores={report.scores} />}

      <SentimentGauge score={report.sentiment_score!} brand={report.brand} />

      <Separator />

      <Tabs defaultValue="pillars">
        <TabsList>
          <TabsTrigger value="pillars">Brand Pillars</TabsTrigger>
          <TabsTrigger value="models">Analysis Comparison</TabsTrigger>
          {report.competitors.length > 0 && (
            <TabsTrigger value="competitors">Competitors</TabsTrigger>
          )}
          <TabsTrigger value="trends">Trends</TabsTrigger>
        </TabsList>

        <TabsContent value="pillars" className="mt-6">
          <PillarCards pillars={report.pillars} />
        </TabsContent>

        <TabsContent value="models" className="mt-6">
          <ModelComparison models={report.model_perceptions} />
        </TabsContent>

        {report.competitors.length > 0 && (
          <TabsContent value="competitors" className="mt-6">
            <CompetitorChart
              positions={report.competitor_positions}
              primaryBrand={report.brand}
            />
          </TabsContent>
        )}

        <TabsContent value="trends" className="mt-6">
          <TrendChart data={report.trend_data} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export function ReportPage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["report", id],
    queryFn: () => api.reports.get(id!),
    enabled: !!id,
  });

  if (isLoading) return <ReportSkeleton />;
  if (isError || !data) {
    return (
      <div className="space-y-4 text-center py-12">
        <p className="text-muted-foreground">Report not found or failed to load.</p>
        <Button variant="outline" render={<Link to="/" />}>
          Back to Dashboard
        </Button>
      </div>
    );
  }

  const report = data;

  return <ReportContent report={report} />;
}
