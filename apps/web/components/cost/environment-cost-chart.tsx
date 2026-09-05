"use client";

import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { EnvironmentBreakdownRow } from "@/lib/api";
import { formatAxisUsd, formatUsd } from "@/lib/format";
import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from "recharts";

const ENV_COLORS: Record<string, string> = {
  production: "var(--chart-1)",
  staging: "var(--chart-4)",
  development: "var(--chart-2)",
};

/** Cost by environment — fixed semantic color per environment. */
export function EnvironmentCostChart({ rows }: { rows: EnvironmentBreakdownRow[] }) {
  const config: Record<string, { label: string; color: string }> = {
    cost: { label: "Cost (USD)", color: "var(--chart-1)" },
  };
  for (const row of rows) {
    config[row.environment] = { label: row.environment, color: ENV_COLORS[row.environment] ?? "var(--chart-3)" };
  }

  const data = rows.map((row) => ({ ...row, fill: ENV_COLORS[row.environment] ?? "var(--chart-3)" }));

  return (
    <ChartContainer config={config} className="h-[240px] w-full">
      <BarChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis dataKey="environment" tickLine={false} axisLine={false} tickMargin={8} />
        <YAxis tickLine={false} axisLine={false} width={52} tickFormatter={formatAxisUsd} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelKey="environment"
              formatter={(value) => (
                <span className="font-mono font-medium tabular-nums">{formatUsd(Number(value))}</span>
              )}
            />
          }
        />
        <Bar dataKey="cost" radius={6} maxBarSize={64}>
          {data.map((entry) => (
            <Cell key={entry.environment} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
}
