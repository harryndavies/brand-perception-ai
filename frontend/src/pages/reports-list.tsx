import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { NewAnalysisDialog } from "@/components/new-analysis-dialog";
import { ReportCard } from "@/components/reports/report-card";
import { listReports } from "@/services/reports";

export function ReportsListPage() {
  const { data: reports, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: listReports,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="All completed brand analysis reports."
        action={<NewAnalysisDialog trigger={<Button>New Analysis</Button>} />}
      />

      {isLoading && (
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
      )}

      {!isLoading && reports?.length === 0 && (
        <EmptyState
          title="No reports yet"
          description="Run an analysis to generate your first report."
          action={<NewAnalysisDialog trigger={<Button>New Analysis</Button>} />}
        />
      )}

      {!isLoading && reports && reports.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      )}
    </div>
  );
}
