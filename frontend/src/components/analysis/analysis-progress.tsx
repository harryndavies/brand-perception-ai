import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { JobStatus } from "@/types";
import type { ModelInfo } from "@/types";

function jobStatusLabel(status: JobStatus): string {
  switch (status) {
    case JobStatus.PENDING: return "Queued";
    case JobStatus.RUNNING: return "Analysing";
    case JobStatus.COMPLETE: return "Complete";
    case JobStatus.FAILED: return "Failed";
    default: return "Waiting";
  }
}

function jobStatusVariant(status: JobStatus): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case JobStatus.COMPLETE: return "default";
    case JobStatus.FAILED: return "destructive";
    case JobStatus.RUNNING: return "secondary";
    default: return "outline";
  }
}

function jobProgressValue(status: JobStatus): number {
  switch (status) {
    case JobStatus.COMPLETE: return 100;
    case JobStatus.RUNNING: return 50;
    default: return 0;
  }
}

interface AnalysisProgressProps {
  selectedModels: string[];
  modelStatuses: Record<string, JobStatus>;
  status: JobStatus;
  errorMessage: string;
  availableModels: ModelInfo[] | undefined;
  onRetry: () => void;
}

export function AnalysisProgress({ selectedModels, modelStatuses, status, errorMessage, availableModels, onRetry }: AnalysisProgressProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Overall</span>
        <Badge variant={jobStatusVariant(status)}>{jobStatusLabel(status)}</Badge>
      </div>

      {selectedModels.map((mk) => {
        const modelInfo = availableModels?.find((m) => m.key === mk);
        const ms = modelStatuses[mk] ?? "pending";
        return (
          <div key={mk} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span>{modelInfo?.label ?? mk}</span>
              <Badge variant={jobStatusVariant(ms)}>{ms}</Badge>
            </div>
            <Progress value={jobProgressValue(ms)} className="h-1.5" />
          </div>
        );
      })}

      {status === JobStatus.FAILED && (
        <div className="space-y-2">
          <p className="text-sm text-destructive">
            {errorMessage || "Something went wrong. Please try again."}
          </p>
          <Button variant="outline" className="w-full" onClick={onRetry}>
            Try Again
          </Button>
        </div>
      )}
    </div>
  );
}
