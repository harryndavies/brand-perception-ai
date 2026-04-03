import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { formatSentiment } from "@/lib/format";
import type { ModelPerception } from "@/types";

interface ModelComparisonProps {
  models: ModelPerception[];
}

function sentimentBadge(score: number): { label: string; variant: "default" | "secondary" | "destructive" } {
  if (score >= 0.5) return { label: "Positive", variant: "default" };
  if (score >= 0) return { label: "Neutral", variant: "secondary" };
  return { label: "Negative", variant: "destructive" };
}

export function ModelComparison({ models }: ModelComparisonProps) {
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-40">Analysis</TableHead>
            <TableHead>Summary</TableHead>
            <TableHead className="w-28">Sentiment</TableHead>
            <TableHead>Key Themes</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {models.map((model) => {
            const { label, variant } = sentimentBadge(model.sentiment);
            return (
              <TableRow key={model.model}>
                <TableCell className="font-medium">{model.model}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {model.summary}
                </TableCell>
                <TableCell>
                  <Badge variant={variant}>{label} ({formatSentiment(model.sentiment)})</Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {model.key_themes.map((theme) => (
                      <Badge key={theme} variant="outline" className="text-xs">
                        {theme}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
