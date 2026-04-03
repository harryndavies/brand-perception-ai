import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatSentiment } from "@/lib/format";
import { AnalysisStatus } from "@/types";
import type { BrandReport } from "@/types";

interface StatsCardsProps {
  reports: BrandReport[];
  isLoading: boolean;
}

export function StatsCards({ reports, isLoading }: StatsCardsProps) {
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

  const completed = reports.filter((r) => r.status === AnalysisStatus.COMPLETE);
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
            {avgSentiment !== null ? formatSentiment(avgSentiment) : "--"}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
