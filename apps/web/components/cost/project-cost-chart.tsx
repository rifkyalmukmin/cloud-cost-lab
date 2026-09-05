"use client";

import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { ProjectBreakdownRow } from "@/lib/api";
import { formatAxisUsd, formatUsd } from "@/lib/format";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

/** Cost by project as a bar chart, highest first (API returns sorted rows). */
export function ProjectCostChart({ rows }: { rows: ProjectBreakdownRow[] }) {
  const config: Record<string, { label: string; color: string }> = {
    cost: { label: "Cost (USD)", color: "var(--chart-2)" },
  };

  return (
    <ChartContainer config={config} className="h-[240px] w-full">
      <BarChart data={rows} margin={{ left: 4, right: 8, top: 8 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="project_id"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          tickFormatter={(value: string) => value.replace(/^cc-lab-/, "")}
        />
        <YAxis tickLine={false} axisLine={false} width={52} tickFormatter={formatAxisUsd} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelKey="project_id"
              formatter={(value) => (
                <span className="font-mono font-medium tabular-nums">{formatUsd(Number(value))}</span>
              )}
            />
          }
        />
        <Bar dataKey="cost" fill="var(--color-cost)" radius={6} maxBarSize={56} />
      </BarChart>
    </ChartContainer>
  );
}
