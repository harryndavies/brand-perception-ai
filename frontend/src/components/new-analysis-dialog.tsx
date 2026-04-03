import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useAnalysisDialog } from "@/hooks/use-analysis-dialog";
import { AnalysisProgress } from "@/components/analysis/analysis-progress";
import { AnalysisForm } from "@/components/analysis/analysis-form";

export function NewAnalysisDialog({ trigger }: { trigger: React.ReactElement }) {
  const {
    form,
    execution,
    isRunning,
    hasKey,
    availableModels,
    modelsByProvider,
    handleFormSubmit,
    handleOpenChange,
    toggleModel,
    reset,
  } = useAnalysisDialog();

  const selectedModels = form.watch("selectedModels");
  const brand = form.watch("brand");

  return (
    <Dialog open={execution.open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isRunning ? `Analysing ${brand}` : "New Analysis"}</DialogTitle>
          <DialogDescription>
            {isRunning
              ? `Running analysis across ${selectedModels.length} model${selectedModels.length > 1 ? "s" : ""}.`
              : "Enter a brand and select one model per provider to compare."}
          </DialogDescription>
        </DialogHeader>

        {isRunning ? (
          <AnalysisProgress
            selectedModels={selectedModels}
            modelStatuses={execution.modelStatuses}
            status={execution.status}
            errorMessage={execution.errorMessage}
            availableModels={availableModels}
            onRetry={reset}
          />
        ) : !hasKey ? (
          <div className="space-y-3 text-center py-2">
            <p className="text-sm text-muted-foreground">
              Add at least one API key to run analyses. Click the key icon in the sidebar.
            </p>
          </div>
        ) : (
          <AnalysisForm
            form={form}
            modelsByProvider={modelsByProvider}
            onToggleModel={toggleModel}
            onSubmit={handleFormSubmit}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
