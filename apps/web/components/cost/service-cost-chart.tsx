"use client";

import { ChartLegend, ChartLegendContent, ChartContainer, ChartTooltipContent } from "@/components/ui/chart";
import type { ServiceBreakdownRow } from "@/lib/api";
import { formatShare, formatUsd } from "@/lib/format";
import { Cell, Pie, PieChart, Tooltip } from "recharts";

const SLICE_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

/** Cost share by service as a donut chart (labels in legend, values in tooltip). */
export function ServiceCostChart({ rows }: { rows: ServiceBreakdownRow[] }) {
  const config: Record<string, { label: string; color: string }> = {};
  rows.forEach((row, index) => {
    config[row.service] = {
      label: `${row.service_name} (${formatShare(row.share_pct)})`,
      color: SLICE_COLORS[index % SLICE_COLORS.length],
    };
  });

  const data = rows.map((row) => ({
    ...row,
    fill: config[row.service]?.color ?? "var(--chart-1)",
  }));

  return (
    <ChartContainer config={config} className="mx-auto h-[240px] w-full">
      <PieChart>
        <Tooltip
          content={
            <ChartTooltipContent
              nameKey="service"
              labelKey="service"
              formatter={(value, name) => (
                <span className="font-mono font-medium tabular-nums">
                  {formatUsd(Number(value))} · {name}
                </span>
              )}
            />
          }
        />
        <ChartLegend content={<ChartLegendContent nameKey="service" />} className="flex-wrap" />
        <Pie
          data={data}
          dataKey="cost"
          nameKey="service"
          innerRadius={56}
          outerRadius={88}
          paddingAngle={2}
          strokeWidth={2}
        >
          {data.map((entry) => (
            <Cell key={entry.service} fill={entry.fill} />
          ))}
        </Pie>
      </PieChart>
    </ChartContainer>
  );
}
