import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SentimentGauge } from "@/components/report/sentiment-gauge";
import { PillarCards } from "@/components/report/pillar-cards";
import { ModelComparison } from "@/components/report/model-comparison";
import { CompetitorChart } from "@/components/report/competitor-chart";
import { TrendChart } from "@/components/report/trend-chart";
import { api } from "@/lib/api";
import type { BrandReport } from "@/types";

const DEMO_REPORT: BrandReport = {
  id: "demo",
  brand: "Arc'teryx",
  competitors: ["Patagonia", "The North Face", "Salomon"],
  status: "complete",
  sentiment_score: 0.74,
  pillars: [
    {
      name: "Technical Performance",
      description: "Widely recognised for industry-leading Gore-Tex Pro construction and minimalist design that prioritises function.",
      confidence: 0.92,
      sources: ["Claude", "GPT-4", "Reddit", "Trustpilot"],
    },
    {
      name: "Premium Positioning",
      description: "Consistently perceived as a premium brand with pricing that reflects technical innovation and build quality.",
      confidence: 0.88,
      sources: ["Claude", "Gemini", "News"],
    },
    {
      name: "Sustainability",
      description: "Growing recognition of repair and reuse programs, though some concern about fast fashion crossover.",
      confidence: 0.65,
      sources: ["GPT-4", "News", "Reddit"],
    },
    {
      name: "Cultural Cachet",
      description: "Strong urban adoption beyond outdoor use. The brand bridges technical outdoor and streetwear markets.",
      confidence: 0.78,
      sources: ["Claude", "Gemini", "Reddit"],
    },
  ],
  model_perceptions: [
    {
      model: "Claude",
      summary: "Sees Arc'teryx as the gold standard in technical outerwear with genuine innovation credentials, though notes growing hype risk.",
      sentiment: 0.82,
      key_themes: ["technical excellence", "premium quality", "urban adoption"],
    },
    {
      model: "GPT-4",
      summary: "Highlights durability and warranty as key differentiators. Flags sustainability as an area needing stronger communication.",
      sentiment: 0.71,
      key_themes: ["durability", "warranty", "sustainability gap"],
    },
    {
      model: "Gemini",
      summary: "Focuses on the brand's cultural shift from niche outdoor to mainstream fashion, seeing both opportunity and dilution risk.",
      sentiment: 0.68,
      key_themes: ["cultural crossover", "brand dilution risk", "fashion trend"],
    },
  ],
  competitor_positions: [
    { brand: "Arc'teryx", premium_score: 0.9, lifestyle_score: 0.55 },
    { brand: "Patagonia", premium_score: 0.7, lifestyle_score: 0.4 },
    { brand: "The North Face", premium_score: 0.5, lifestyle_score: 0.7 },
    { brand: "Salomon", premium_score: 0.65, lifestyle_score: 0.45 },
  ],
  trend_data: [
    { date: "2025-10-01", sentiment: 0.65, volume: 1200 },
    { date: "2025-11-01", sentiment: 0.68, volume: 1450 },
    { date: "2025-12-01", sentiment: 0.72, volume: 1800 },
    { date: "2026-01-01", sentiment: 0.7, volume: 1600 },
    { date: "2026-02-01", sentiment: 0.73, volume: 1700 },
    { date: "2026-03-01", sentiment: 0.74, volume: 1900 },
  ],
  created_at: "2026-04-01T10:00:00Z",
  completed_at: "2026-04-01T10:02:34Z",
};

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

      <SentimentGauge score={report.sentiment_score!} brand={report.brand} />

      <Separator />

      <Tabs defaultValue="pillars">
        <TabsList>
          <TabsTrigger value="pillars">Brand Pillars</TabsTrigger>
          <TabsTrigger value="models">AI Model Comparison</TabsTrigger>
          <TabsTrigger value="competitors">Competitors</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
        </TabsList>

        <TabsContent value="pillars" className="mt-6">
          <PillarCards pillars={report.pillars} />
        </TabsContent>

        <TabsContent value="models" className="mt-6">
          <ModelComparison models={report.model_perceptions} />
        </TabsContent>

        <TabsContent value="competitors" className="mt-6">
          <CompetitorChart
            positions={report.competitor_positions}
            primaryBrand={report.brand}
          />
        </TabsContent>

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

  // Use demo data as fallback when API is unavailable
  const report = data ?? (isError || !isLoading ? DEMO_REPORT : null);

  if (isLoading && !report) return <ReportSkeleton />;
  if (!report) return <ReportSkeleton />;

  return <ReportContent report={report} />;
}
