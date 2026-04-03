import { sentimentLabel, sentimentColor, formatSentiment } from "@/lib/format";

export function SentimentBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-muted-foreground">--</span>;
  return (
    <span className={sentimentColor(score)}>
      {sentimentLabel(score)} ({formatSentiment(score)})
    </span>
  );
}
