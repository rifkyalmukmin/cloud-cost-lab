"use client";

import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ZAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { CostVsUtilData } from "@/lib/api";

interface CostVsUtilChartProps {
  data: CostVsUtilData[] | null;
  loading?: boolean;
  error?: boolean;
}

export function CostVsUtilChart({ data, loading, error }: CostVsUtilChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cost vs CPU Utilization</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-80 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-base">Cost vs CPU Utilization</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80 flex items-center justify-center">
            <p className="text-sm text-destructive">Failed to load chart data</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cost vs CPU Utilization</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80 flex items-center justify-center">
            <p className="text-sm text-muted-foreground">No data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const chartData = data
    .filter((d) => d.cpu_avg !== null)
    .map((d) => ({
      name: d.name,
      x: d.cpu_avg,
      y: d.cost,
      z: d.cost,
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Cost vs CPU Utilization</CardTitle>
        <p className="text-xs text-muted-foreground">
          Resources in the bottom-left quadrant (low CPU, low cost) are candidates for
          downsizing. Resources in the top-left (low CPU, high cost) should be optimized.
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={320}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 30, left: 50 }}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis
              type="number"
              dataKey="x"
              name="CPU"
              unit="%"
              domain={[0, 100]}
              label={{ value: "CPU Utilization (%)", position: "bottom", offset: 10 }}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Cost"
              unit="$"
              label={{
                value: "Monthly Cost ($)",
                angle: -90,
                position: "left",
                offset: 30,
              }}
              tick={{ fontSize: 12 }}
            />
            <ZAxis type="number" dataKey="z" range={[50, 400]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              formatter={(value, name) => {
                const numVal = Number(value);
                if (name === "CPU") return [`${numVal.toFixed(1)}%`, "CPU Utilization"];
                if (name === "Cost") return [`$${numVal.toFixed(2)}`, "Monthly Cost"];
                return [value, name];
              }}
              labelFormatter={(label) => chartData[Number(label)]?.name || ""}
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid hsl(var(--border))",
                backgroundColor: "hsl(var(--card))",
              }}
            />
            <Scatter name="Resources" data={chartData} fill="#2563eb" />
          </ScatterChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
