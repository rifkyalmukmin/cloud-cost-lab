"use client";

import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { UtilizationItem } from "@/lib/api";
import { formatUsd } from "@/lib/format";
import { signalColor } from "@/components/utilization/signal-ui";
import { CartesianGrid, Cell, ReferenceLine, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from "recharts";

/** Cost vs Utilization: one bubble per resource — cost over the analysis
 * window (y) vs average CPU (x). Bubble color carries the evidence signal.
 * Resources without CPU or cost samples do not plot (they remain in the
 * table with their missing-metrics list). */
export function CostUtilizationScatter({ items }: { items: UtilizationItem[] }) {
  const points = items
    .filter((item) => item.avg_cpu !== null && item.cost_in_window !== null)
    .map((item) => ({
      resource_id: item.resource_id,
      resource_name: item.resource_name,
      environment: item.environment,
      avg_cpu: item.avg_cpu as number,
      cost: item.cost_in_window as number,
      color: signalColor(item),
    }));

  // The high-CPU reference line must always be on screen, so the domain grows
  // beyond 80% when the data does — never silently cropped.
  const maxCpu = points.reduce((max, point) => Math.max(max, point.avg_cpu), 0);
  const xMax = Math.max(90, Math.ceil(maxCpu / 10) * 10 + 10);

  const config = {
    cost: { label: "Cost in window" },
    avg_cpu: { label: "Avg CPU %" },
  } as const;

  return (
    <ChartContainer config={config} className="h-[280px] w-full">
      <ScatterChart margin={{ top: 12, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          type="number"
          dataKey="avg_cpu"
          name="Avg CPU"
          domain={[0, xMax]}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value: number) => `${value}%`}
          label={{ value: "avg CPU %", position: "insideBottomRight", offset: -4, fontSize: 11 }}
        />
        <YAxis
          type="number"
          dataKey="cost"
          name="Cost"
          tickLine={false}
          axisLine={false}
          width={56}
          tickFormatter={(value: number) => `$${value}`}
        />
        <ZAxis range={[70, 70]} />
        {/* evidence thresholds — project-specific heuristics, not standards */}
        <ReferenceLine x={20} stroke="var(--muted-foreground)" strokeDasharray="4 4" strokeOpacity={0.35} />
        <ReferenceLine x={80} stroke="var(--muted-foreground)" strokeDasharray="4 4" strokeOpacity={0.35} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelKey="resource_name"
              formatter={(value, name) => (
                <span className="font-mono font-medium tabular-nums">
                  {name === "cost" ? formatUsd(Number(value)) : `${Number(value).toFixed(1)}%`} · {name}
                </span>
              )}
            />
          }
        />
        <Scatter data={points} isAnimationActive={false}>
          {points.map((point) => (
            <Cell key={point.resource_id} fill={point.color} fillOpacity={0.75} />
          ))}
        </Scatter>
      </ScatterChart>
    </ChartContainer>
  );
}
