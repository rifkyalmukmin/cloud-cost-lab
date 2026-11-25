"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ForecastResponse } from "@/lib/api";
import { getForecast } from "@/lib/api";
import { formatIsoDate } from "@/lib/dates";

function money(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function ForecastContent() {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getForecast()
      .then((data) => {
        if (!cancelled) {
          setForecast(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (error || !forecast || forecast.error || !forecast.monthly_summary || !forecast.daily_forecast) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="py-8">
          <p className="text-sm text-destructive">{forecast?.error ?? "Failed to load forecast"}</p>
        </CardContent>
      </Card>
    );
  }

  const summary = forecast.monthly_summary;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">30-day range</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm">
            Expected {money(summary.expected)}. Lower bound {money(summary.lower_bound)}. Upper bound{" "}
            {money(summary.upper_bound)}.
          </p>
          <p className="text-sm text-muted-foreground">
            Range {summary.range_description}. Method: {forecast.method}. Confidence on each day is labeled in the table.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Daily expected cost</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={forecast.daily_forecast} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis dataKey="date" tickFormatter={(value) => formatIsoDate(String(value))} tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={(value) => `$${value}`} tick={{ fontSize: 12 }} width={50} />
                <Tooltip
                  formatter={(value, name) => [money(Number(value)), String(name)]}
                  labelFormatter={(label) => formatIsoDate(String(label))}
                />
                <Area type="monotone" dataKey="upper_bound" stroke="#94a3b8" fill="#e2e8f0" name="Upper bound" />
                <Area type="monotone" dataKey="expected" stroke="#2563eb" fill="#bfdbfe" name="Expected" />
                <Area type="monotone" dataKey="lower_bound" stroke="#64748b" fill="#ffffff" name="Lower bound" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Daily values</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Daily forecast with expected cost and bounds</caption>
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Date</th>
                <th className="py-2 pr-4 font-medium">Expected</th>
                <th className="py-2 pr-4 font-medium">Lower bound</th>
                <th className="py-2 pr-4 font-medium">Upper bound</th>
                <th className="py-2 font-medium">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {forecast.daily_forecast.map((point) => (
                <tr key={point.date} className="border-t">
                  <td className="py-2 pr-4">{formatIsoDate(point.date)}</td>
                  <td className="py-2 pr-4">{money(point.expected)}</td>
                  <td className="py-2 pr-4">{money(point.lower_bound)}</td>
                  <td className="py-2 pr-4">{money(point.upper_bound)}</td>
                  <td className="py-2">{point.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
