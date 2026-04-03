import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { STATUS_VARIANT, formatDate, sentimentColorCompact, formatSentiment } from "@/lib/format";
import type { BrandReport } from "@/types";

export function ReportCard({ report }: { report: BrandReport }) {
  return (
    <Link to={`/reports/${report.id}`}>
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
              {formatDate(report.created_at)}
            </span>
            {report.sentiment_score !== null && (
              <span className={sentimentColorCompact(report.sentiment_score)}>
                {formatSentiment(report.sentiment_score)}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
