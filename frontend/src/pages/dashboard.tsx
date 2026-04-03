import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { NewAnalysisDialog } from "@/components/new-analysis-dialog";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { ReportsTable } from "@/components/dashboard/reports-table";
import { SchedulesSection } from "@/components/dashboard/schedules-section";
import { listReports } from "@/services/reports";

export function DashboardPage() {
  const { data: reports, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: listReports,
  });

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="Overview of your brand analysis runs."
        action={
          <NewAnalysisDialog trigger={
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Analysis
            </Button>
          } />
        }
      />

      <StatsCards reports={reports ?? []} isLoading={isLoading} />
      <SchedulesSection />
      <ReportsTable reports={reports ?? []} isLoading={isLoading} />
    </div>
  );
}
