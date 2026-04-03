import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TrendPoint } from "@/types";

interface TrendChartProps {
  data: TrendPoint[];
}

const MODEL_COLORS: Record<string, string> = {
  sonnet: "#6366f1",
  haiku: "#f59e0b",
  opus: "#a855f7",
};

const MODEL_LABELS: Record<string, string> = {
  sonnet: "Sonnet",
  haiku: "Haiku",
  opus: "Opus",
};

export function TrendChart({ data }: TrendChartProps) {
  if (data.length < 1) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Perception Trend
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
            Not enough data yet. Run more analyses over time to see trends.
          </div>
        </CardContent>
      </Card>
    );
  }

  // Find all unique models in the data
  const models = [...new Set(data.map((d) => d.model || "sonnet"))];

  // Transform data: each row has a date and a sentiment value per model
  const dateMap = new Map<string, Record<string, number | null>>();
  for (const point of data) {
    const model = point.model || "sonnet";
    const existing = dateMap.get(point.date) ?? {};
    existing[model] = point.sentiment;
    dateMap.set(point.date, existing);
  }

  const chartData = [...dateMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, values]) => ({
      date,
      ...Object.fromEntries(models.map((m) => [m, values[m] ?? null])),
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          Perception Trend
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="date"
              className="text-xs"
              stroke="hsl(var(--muted-foreground))"
              tickFormatter={(d: string) =>
                new Date(d).toLocaleDateString("en-GB", {
                  month: "short",
                  day: "numeric",
                })
              }
            />
            <YAxis
              domain={[-1, 1]}
              className="text-xs"
              stroke="hsl(var(--muted-foreground))"
              tickCount={5}
            />
            <Tooltip
              content={({ payload, label }) => {
                if (!payload?.length) return null;
                return (
                  <div className="rounded-md border bg-background px-3 py-2 text-sm shadow-md">
                    <p className="text-muted-foreground">
                      {new Date(label as string).toLocaleDateString("en-GB", {
                        month: "long",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </p>
                    {payload.map((entry) => (
                      <p key={entry.dataKey as string} style={{ color: entry.color }} className="font-medium">
                        {MODEL_LABELS[entry.dataKey as string] ?? entry.dataKey as string}:{" "}
                        {Number(entry.value) > 0 ? "+" : ""}
                        {Number(entry.value).toFixed(2)}
                      </p>
                    ))}
                  </div>
                );
              }}
            />
            {models.length > 1 && (
              <Legend
                formatter={(value: string) => MODEL_LABELS[value] ?? value}
              />
            )}
            {models.map((model) => (
              <Line
                key={model}
                type="monotone"
                dataKey={model}
                name={model}
                stroke={MODEL_COLORS[model] ?? "#6366f1"}
                strokeWidth={2}
                dot={{ fill: MODEL_COLORS[model] ?? "#6366f1", r: 3 }}
                activeDot={{ r: 5, strokeWidth: 2 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
