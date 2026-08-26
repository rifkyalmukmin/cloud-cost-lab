"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { CostByDimension } from "@/lib/api";

interface BreakdownChartProps {
  title: string;
  data: CostByDimension[] | null;
  loading?: boolean;
  error?: boolean;
}

const COLORS = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706"];

function formatCurrency(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function BreakdownChart({ title, data, loading, error }: BreakdownChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-48 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-48 flex items-center justify-center">
            <p className="text-sm text-destructive">Failed to load data</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-48 flex items-center justify-center">
            <p className="text-sm text-muted-foreground">No data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
          >
            <XAxis
              type="number"
              tickFormatter={(v) => `$${v}`}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="value"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={140}
            />
            <Tooltip
              formatter={(value) => [formatCurrency(Number(value)), "Cost"]}
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid hsl(var(--border))",
                backgroundColor: "hsl(var(--card))",
              }}
            />
            <Bar dataKey="net_cost" radius={[0, 4, 4, 0]}>
              {data.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-3 space-y-1">
          {data.map((item, index) => (
            <div key={item.value} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-sm"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                />
                <span className="text-muted-foreground">{item.value}</span>
              </div>
              <span className="font-medium">
                {formatCurrency(item.net_cost)} ({item.percentage}%)
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
