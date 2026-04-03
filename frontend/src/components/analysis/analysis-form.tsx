import type { UseFormReturn } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { FormError } from "@/components/ui/form-error";
import { PROVIDER_LABELS } from "@/lib/constants";
import type { AnalysisFormData } from "@/lib/schemas";
import type { ModelInfo } from "@/types";

interface AnalysisFormProps {
  form: UseFormReturn<AnalysisFormData>;
  modelsByProvider: Record<string, ModelInfo[]>;
  onToggleModel: (key: string) => void;
  onSubmit: (data: AnalysisFormData) => void;
}

export function AnalysisForm({ form, modelsByProvider, onToggleModel, onSubmit }: AnalysisFormProps) {
  const { register, handleSubmit, watch, setValue, formState: { errors } } = form;
  const selectedModels = watch("selectedModels");
  const brand = watch("brand");

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="brand">Brand name</Label>
        <Input
          id="brand"
          placeholder="e.g. Arc'teryx, Notion, Stripe..."
          autoFocus
          {...register("brand")}
        />
        <FormError error={errors.brand} />
      </div>

      <div className="space-y-2">
        <Label>Competitors (optional)</Label>
        {[0, 1, 2].map((i) => (
          <Input
            key={i}
            placeholder={`Competitor ${i + 1}`}
            {...register(`competitors.${i}`)}
          />
        ))}
      </div>

      <div className="space-y-2">
        <Label>Models</Label>
        <div className="space-y-3">
          {Object.entries(modelsByProvider).map(([provider, models]) => (
            <div key={provider} className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">
                {PROVIDER_LABELS[provider] ?? provider}
              </p>
              <div className="flex flex-wrap gap-2">
                {models.map((m) => (
                  <button
                    key={m.key}
                    type="button"
                    onClick={() => onToggleModel(m.key)}
                    className={`rounded-md border px-3 py-1.5 text-sm transition-colors ${
                      selectedModels.includes(m.key)
                        ? "border-indigo-500 bg-indigo-500/10 text-indigo-500"
                        : "hover:border-foreground/20"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <FormError error={errors.selectedModels} />
      </div>

      <div className="flex items-center justify-between rounded-md border px-3 py-2">
        <div>
          <Label htmlFor="repeat" className="text-sm font-medium">Repeat monthly</Label>
          <p className="text-xs text-muted-foreground">Auto-run this analysis every 30 days</p>
        </div>
        <Switch
          id="repeat"
          checked={watch("repeatMonthly")}
          onCheckedChange={(checked) => setValue("repeatMonthly", checked)}
        />
      </div>

      <Button type="submit" className="w-full" disabled={!brand.trim() || selectedModels.length === 0}>
        {selectedModels.length > 1
          ? `Run ${selectedModels.length} Models`
          : "Start Analysis"}
      </Button>
    </form>
  );
}
