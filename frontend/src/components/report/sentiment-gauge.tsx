import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { sentimentColorCompact, formatSentiment } from "@/lib/format";

interface SentimentGaugeProps {
  score: number;
  brand: string;
}

function sentimentLabelDetailed(score: number): string {
  if (score >= 0.6) return "Very Positive";
  if (score >= 0.2) return "Positive";
  if (score >= -0.2) return "Neutral";
  if (score >= -0.6) return "Negative";
  return "Very Negative";
}

export function SentimentGauge({ score, brand }: SentimentGaugeProps) {
  const percentage = ((score + 1) / 2) * 100;
  const label = sentimentLabelDetailed(score);
  const color = sentimentColorCompact(score);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">
          Overall Sentiment
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <div className="relative flex h-24 w-24 items-center justify-center">
            <svg viewBox="0 0 100 100" className="h-24 w-24 -rotate-90">
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="currentColor"
                strokeWidth="8"
                className="text-muted/30"
              />
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="currentColor"
                strokeWidth="8"
                strokeDasharray={`${percentage * 2.51} ${251 - percentage * 2.51}`}
                strokeLinecap="round"
                className={color}
              />
            </svg>
            <span className={`absolute text-lg font-bold ${color}`}>
              {formatSentiment(score)}
            </span>
          </div>
          <div>
            <p className={`text-lg font-semibold ${color}`}>{label}</p>
            <p className="text-sm text-muted-foreground">
              Aggregate sentiment for {brand} across all analysis perspectives.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
