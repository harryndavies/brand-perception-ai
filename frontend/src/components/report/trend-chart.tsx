import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TrendPoint } from "@/types";

interface TrendChartProps {
  data: TrendPoint[];
}

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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          Perception Trend
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
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
                    <p className="font-medium">
                      Sentiment: {Number(payload[0].value) > 0 ? "+" : ""}
                      {Number(payload[0].value).toFixed(2)}
                    </p>
                  </div>
                );
              }}
            />
            <Line
              type="monotone"
              dataKey="sentiment"
              stroke="#6366f1"
              strokeWidth={2}
              dot={{ fill: "#6366f1", r: 3 }}
              activeDot={{ r: 5, stroke: "#4f46e5", strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
