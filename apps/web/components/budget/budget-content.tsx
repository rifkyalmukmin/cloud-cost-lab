"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { BudgetStatus } from "@/lib/api";
import { getBudget } from "@/lib/api";

function money(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function BudgetContent() {
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getBudget()
      .then((data) => {
        if (!cancelled) {
          setBudget(data);
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
    return <Skeleton className="h-40 w-full" />;
  }

  if (error || !budget) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="py-8">
          <p className="text-sm text-destructive">Failed to load budget</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Limit</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{money(budget.budget.limit)}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Warning {budget.budget.warning_threshold}% · Critical {budget.budget.critical_threshold}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Current spend</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{money(budget.current.spend)}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {budget.current.utilization_pct.toFixed(1)}% used · {money(budget.current.remaining)} remaining
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Current status</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{budget.current.status}</p>
            <p className="text-xs text-muted-foreground mt-1">HEALTHY, WARNING, CRITICAL, or EXCEEDED</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Projected status</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{budget.projected.status}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {money(budget.projected.spend)} · {budget.projected.utilization_pct.toFixed(1)}% of the limit
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          {budget.alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No budget alerts. Status is {budget.current.status}.</p>
          ) : (
            <ul className="space-y-3">
              {budget.alerts.map((alert) => (
                <li key={`${alert.severity}-${alert.message}`} className="text-sm">
                  <p>
                    <span className="font-medium">{alert.severity}:</span> {alert.message}
                  </p>
                  <p className="text-muted-foreground">{alert.recommendation}</p>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
