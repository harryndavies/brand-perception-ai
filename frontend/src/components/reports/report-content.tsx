import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScoreCard } from "@/components/report/score-card";
import { SentimentGauge } from "@/components/report/sentiment-gauge";
import { PillarCards } from "@/components/report/pillar-cards";
import { ModelComparison } from "@/components/report/model-comparison";
import { CompetitorChart } from "@/components/report/competitor-chart";
import { TrendChart } from "@/components/report/trend-chart";
import { formatDateTime } from "@/lib/format";
import type { BrandReport } from "@/types";

export function ReportContent({ report }: { report: BrandReport }) {
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
            {report.completed_at ? formatDateTime(report.completed_at) : ""}
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
