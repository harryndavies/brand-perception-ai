import { useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Label,
  Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_COLORS, CHART_COLOR_DEFAULT } from "@/lib/chart";
import type { CompetitorPosition } from "@/types";

interface CompetitorChartProps {
  positions: CompetitorPosition[];
  primaryBrand: string;
}

const COMPETITOR_PALETTE = [
  CHART_COLOR_DEFAULT,
  CHART_COLORS.opus ?? "#a855f7",
  CHART_COLORS.haiku ?? "#f59e0b",
  CHART_COLORS["gpt-4o"] ?? "#10b981",
];

export function CompetitorChart({ positions, primaryBrand }: CompetitorChartProps) {
  const data = useMemo(
    () => positions.map((p) => ({ ...p, x: p.lifestyle_score, y: p.premium_score })),
    [positions],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          Competitive Positioning
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={320}>
          <ScatterChart margin={{ top: 10, right: 30, bottom: 30, left: 30 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[0, 1]}
              tickCount={5}
              className="text-xs"
              stroke="hsl(var(--muted-foreground))"
            >
              <Label
                value="Functional → Lifestyle"
                position="bottom"
                offset={10}
                className="fill-muted-foreground text-xs"
              />
            </XAxis>
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, 1]}
              tickCount={5}
              className="text-xs"
              stroke="hsl(var(--muted-foreground))"
            >
              <Label
                value="Mass Market → Premium"
                angle={-90}
                position="left"
                offset={10}
                className="fill-muted-foreground text-xs"
              />
            </YAxis>
            <Tooltip
              content={({ payload }) => {
                if (!payload?.length) return null;
                const item = payload[0].payload as CompetitorPosition & { x: number; y: number };
                return (
                  <div className="rounded-md border bg-background px-3 py-2 text-sm shadow-md">
                    <p className="font-medium">{item.brand}</p>
                    <p className="text-muted-foreground">
                      Premium: {(item.premium_score * 100).toFixed(0)}% · Lifestyle: {(item.lifestyle_score * 100).toFixed(0)}%
                    </p>
                  </div>
                );
              }}
            />
            <Scatter data={data} fill={CHART_COLOR_DEFAULT}>
              {data.map((entry, index) => {
                const isPrimary = entry.brand === primaryBrand;
                return (
                  <Cell
                    key={entry.brand}
                    fill={isPrimary ? CHART_COLOR_DEFAULT : COMPETITOR_PALETTE[index % COMPETITOR_PALETTE.length]}
                    r={isPrimary ? 8 : 6}
                    stroke={isPrimary ? CHART_COLORS.opus ?? "#4f46e5" : "none"}
                    strokeWidth={2}
                  />
                );
              })}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
        <div className="mt-2 flex flex-wrap justify-center gap-4">
          {positions.map((p, i) => {
            const isPrimary = p.brand === primaryBrand;
            return (
              <div key={p.brand} className="flex items-center gap-1.5 text-xs">
                <div
                  className="h-2.5 w-2.5 rounded-full"
                  style={{
                    backgroundColor: isPrimary ? CHART_COLOR_DEFAULT : COMPETITOR_PALETTE[i % COMPETITOR_PALETTE.length],
                  }}
                />
                <span className={isPrimary ? "font-medium" : "text-muted-foreground"}>
                  {p.brand}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
