import { Link } from "react-router-dom";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { NewAnalysisDialog } from "@/components/new-analysis-dialog";
import { SentimentBadge } from "@/components/dashboard/sentiment-badge";
import { STATUS_VARIANT, formatDate } from "@/lib/format";
import { AnalysisStatus } from "@/types";
import type { BrandReport } from "@/types";

interface ReportsTableProps {
  reports: BrandReport[];
  isLoading: boolean;
}

export function ReportsTable({ reports, isLoading }: ReportsTableProps) {
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
      <EmptyState
        title="No analyses yet"
        description="Run your first brand analysis to get started."
        icon={<FileText className="h-6 w-6 text-muted-foreground" />}
        action={<NewAnalysisDialog trigger={<Button>New Analysis</Button>} />}
      />
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
                {report.status === AnalysisStatus.COMPLETE && (
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
