"use client";

import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { UtilizationPoint } from "@/lib/api";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

/** CPU vs Memory utilization over time (percent). */
export function UtilizationChart({ points }: { points: UtilizationPoint[] }) {
  const config = {
    cpu_utilization: { label: "CPU %", color: "var(--chart-1)" },
    memory_utilization: { label: "Memory %", color: "var(--chart-2)" },
  } as const;

  return (
    <ChartContainer config={config} className="h-[220px] w-full">
      <LineChart data={points} margin={{ left: 4, right: 8, top: 8 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="date"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          minTickGap={28}
          tickFormatter={(value: string) => (value.length >= 10 ? value.slice(5).replace("-", "/") : value)}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          width={40}
          domain={[0, 100]}
          tickFormatter={(value: number) => `${value}%`}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(label) => `Date: ${label}`}
              formatter={(value, name) => (
                <span className="font-mono font-medium tabular-nums">
                  {Number(value).toFixed(1)}% · {name}
                </span>
              )}
            />
          }
        />
        <ChartLegend content={<ChartLegendContent />} />
        <Line
          dataKey="cpu_utilization"
          type="monotone"
          stroke="var(--color-cpu_utilization)"
          strokeWidth={2}
          dot={false}
          name="CPU %"
        />
        <Line
          dataKey="memory_utilization"
          type="monotone"
          stroke="var(--color-memory_utilization)"
          strokeWidth={2}
          dot={false}
          name="Memory %"
        />
      </LineChart>
    </ChartContainer>
  );
}
