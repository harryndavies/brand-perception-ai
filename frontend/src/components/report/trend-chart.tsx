import { useMemo } from "react";
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
import { CHART_COLORS, CHART_COLOR_DEFAULT, MODEL_LABELS } from "@/lib/chart";
import { formatSentiment, formatDateShort, formatDateLong } from "@/lib/format";
import type { TrendPoint } from "@/types";

interface TrendChartProps {
  data: TrendPoint[];
}

export function TrendChart({ data }: TrendChartProps) {
  const { models, chartData } = useMemo(() => {
    const uniqueModels = [...new Set(data.map((d) => d.model || "sonnet"))];

    const dateMap = new Map<string, Record<string, number | null>>();
    for (const point of data) {
      const model = point.model || "sonnet";
      const existing = dateMap.get(point.date) ?? {};
      existing[model] = point.sentiment;
      dateMap.set(point.date, existing);
    }

    const sorted = [...dateMap.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, values]) => ({
        date,
        ...Object.fromEntries(uniqueModels.map((m) => [m, values[m] ?? null])),
      }));

    return { models: uniqueModels, chartData: sorted };
  }, [data]);

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
              tickFormatter={formatDateShort}
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
                      {formatDateLong(label as string)}
                    </p>
                    {payload.map((entry) => (
                      <p key={entry.dataKey as string} style={{ color: entry.color }} className="font-medium">
                        {MODEL_LABELS[entry.dataKey as string] ?? entry.dataKey as string}:{" "}
                        {formatSentiment(Number(entry.value))}
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
            {models.map((model) => {
              const color = CHART_COLORS[model] ?? CHART_COLOR_DEFAULT;
              return (
                <Line
                  key={model}
                  type="monotone"
                  dataKey={model}
                  name={model}
                  stroke={color}
                  strokeWidth={2}
                  dot={{ fill: color, r: 3 }}
                  activeDot={{ r: 5, strokeWidth: 2 }}
                  connectNulls
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
