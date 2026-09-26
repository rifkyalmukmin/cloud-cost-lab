"use client";

import { useMemo } from "react";

import { ChartCard } from "@/components/data-state";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { formatUsd } from "@/lib/format";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts";

export default function ForecastPage() {
  const forecast = useApi(() => api.getForecast({ horizonDays: 30 }), []);
  const data = forecast.data;

  // Historical daily cost for the last 45 days + forecast continuation.
  const trend = useApi(
    () => api.costTrend({}, "day"),
    [],
  );

  const chartData = useMemo(() => {
    if (!data || !data.sufficient_data || !trend.data) return [];
    const history = trend.data.points.slice(-45);
    const rows: Array<{
      period: string;
      cost: number | null;
      expected: number | null;
      lower: number | null;
      upper: number | null;
    }> = history.map((point) => ({
      period: point.period,
      cost: point.net_cost,
      expected: null,
      lower: null,
      upper: null,
    }));
    // Bridge the gap between history and forecast so the lines connect.
    if (rows.length > 0) {
      rows[rows.length - 1].expected = data.history?.daily_average ?? null;
      rows[rows.length - 1].lower = data.history?.daily_average ?? null;
      rows[rows.length - 1].upper = data.history?.daily_average ?? null;
    }
    for (const point of data.forecast) {
      rows.push({
        period: point.date,
        cost: null,
        expected: point.expected,
        lower: point.lower_bound,
        upper: point.upper_bound,
      });
    }
    return rows;
  }, [data, trend.data]);

  if (forecast.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-[320px] w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Forecast</h1>
        <p className="text-sm text-muted-foreground">
          30-day cost projection from a 14-day moving average and a linear trend — always shown as a
          range, never as a certain value.
        </p>
      </div>

      {!data || !data.sufficient_data ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Not enough data yet</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {data?.message ?? "Forecasting needs at least 14 days of cost history."}
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Summary */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <SummaryCard
              label="Expected (30d)"
              value={data.totals ? formatUsd(data.totals.expected_30d) : "—"}
            />
            <SummaryCard
              label="Range (30d)"
              value={
                data.totals
                  ? `${formatUsd(data.totals.lower_bound_30d)} – ${formatUsd(data.totals.upper_bound_30d)}`
                  : "—"
              }
              hint={data.interval ?? undefined}
            />
            <SummaryCard label="Confidence" value={data.confidence ?? "—"} hint={`history ${data.history_days} days`} />
            <SummaryCard label="Trend" value={data.trend ?? "—"} hint={`slope ${data.methods?.linear_trend?.slope_per_day ?? 0} $/day`} />
          </div>

          {/* Chart */}
          <ChartCard
            title="Daily cost — history and forecast"
            description="Solid: observed daily net cost · dashed: projected expected with the shaded ~80% interval"
            state={forecast}
            isEmpty={chartData.length === 0}
            emptyMessage="No data to chart"
          >
            <ChartContainer
              config={{
                cost: { label: "Observed" },
                expected: { label: "Expected" },
                band: { label: "80% interval" },
              }}
              className="h-[320px] w-full"
            >
              <ComposedChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="period" tickLine={false} axisLine={false} minTickGap={32} />
                <YAxis tickLine={false} axisLine={false} width={52} tickFormatter={(v: number) => `$${v}`} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="upper"
                  stroke="none"
                  fill="var(--color-expected)"
                  fillOpacity={0.12}
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="lower"
                  stroke="none"
                  fill="var(--background)"
                  fillOpacity={0.9}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="cost"
                  stroke="var(--chart-1)"
                  strokeWidth={2}
                  dot={false}
                  name="Observed"
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="expected"
                  stroke="var(--chart-2)"
                  strokeDasharray="6 4"
                  strokeWidth={2}
                  dot={false}
                  name="Expected"
                  connectNulls
                  isAnimationActive={false}
                />
                {data.history ? (
                  <ReferenceLine
                    x={data.history.end}
                    stroke="var(--muted-foreground)"
                    strokeOpacity={0.4}
                    label={{ value: "today (data)", fontSize: 10, position: "insideTopRight" }}
                  />
                ) : null}
              </ComposedChart>
            </ChartContainer>
            <p className="mt-2 text-xs text-muted-foreground">
              Method: 50/50 blend of the {data.methods?.moving_average?.window_days ?? 14}-day moving
              average (${data.methods?.moving_average?.level ?? 0}/day) and an OLS linear trend (R²{" "}
              {data.methods?.linear_trend?.r_squared ?? 0}). This is an ESTIMATE with an explicit
              range — not a guarantee, not realized savings.
            </p>
          </ChartCard>
        </>
      )}
    </div>
  );
}

function SummaryCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xl font-semibold tabular-nums tracking-tight">{value}</p>
        {hint ? <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}
