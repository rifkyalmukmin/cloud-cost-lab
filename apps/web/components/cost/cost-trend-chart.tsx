"use client";

import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { TrendPoint } from "@/lib/api";
import { formatAxisUsd, formatUsd } from "@/lib/format";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

/** Daily (or weekly/monthly) cost trend as an area chart. */
export function CostTrendChart({ points }: { points: TrendPoint[] }) {
  const config = {
    cost: { label: "Cost (USD)", color: "var(--chart-1)" },
  } as const;

  return (
    <ChartContainer config={config} className="h-[240px] w-full">
      <AreaChart data={points} margin={{ left: 4, right: 8, top: 8 }}>
        <defs>
          <linearGradient id="costTrendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-cost)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--color-cost)" stopOpacity={0.03} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="period"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          minTickGap={28}
          tickFormatter={(value: string) => (value.length >= 10 ? value.slice(5).replace("-", "/") : value)}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          width={52}
          tickFormatter={formatAxisUsd}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(label) => `Date: ${label}`}
              formatter={(value) => <span className="font-mono font-medium tabular-nums">{formatUsd(Number(value))}</span>}
            />
          }
        />
        <Area
          dataKey="cost"
          type="monotone"
          stroke="var(--color-cost)"
          fill="url(#costTrendFill)"
          strokeWidth={2}
          name="Cost (USD)"
        />
      </AreaChart>
    </ChartContainer>
  );
}
