"use client";

import { useEffect, useState } from "react";
import { CostSummaryCard } from "./cost-summary-card";
import { CostTrendChart } from "./cost-trend-chart";
import { BreakdownChart } from "./breakdown-chart";
import type {
  CostSummary,
  CostTrendResponse,
  CostBreakdownResponse,
} from "@/lib/api";
import {
  getCostSummary,
  getCostTrend,
  getCostByService,
  getCostByProject,
  getCostByEnvironment,
} from "@/lib/api";
import { formatIsoTimestamp } from "@/lib/dates";

function formatCurrency(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function DashboardContent() {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [trend, setTrend] = useState<CostTrendResponse | null>(null);
  const [byService, setByService] = useState<CostBreakdownResponse | null>(null);
  const [byProject, setByProject] = useState<CostBreakdownResponse | null>(null);
  const [byEnvironment, setByEnvironment] = useState<CostBreakdownResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(false);
        const [s, t, svc, proj, env] = await Promise.all([
          getCostSummary(),
          getCostTrend(),
          getCostByService(),
          getCostByProject(),
          getCostByEnvironment(),
        ]);
        setSummary(s);
        setTrend(t);
        setByService(svc);
        setByProject(proj);
        setByEnvironment(env);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <CostSummaryCard
          title="Current Month"
          value={summary ? formatCurrency(summary.current_month_cost) : "—"}
          trend={
            summary
              ? { value: summary.mom_change_percent, label: "vs last month" }
              : undefined
          }
          loading={loading}
          error={error}
        />
        <CostSummaryCard
          title="Previous Month"
          value={summary ? formatCurrency(summary.previous_month_cost) : "—"}
          loading={loading}
          error={error}
        />
        <CostSummaryCard
          title="MoM Change"
          value={
            summary
              ? `${summary.mom_change_percent > 0 ? "+" : ""}${summary.mom_change_percent.toFixed(1)}%`
              : "—"
          }
          loading={loading}
          error={error}
        />
        <CostSummaryCard
          title="Projected Cost"
          value={summary ? formatCurrency(summary.projected_month_cost) : "—"}
          subtitle="30-day projection"
          loading={loading}
          error={error}
        />
        <CostSummaryCard
          title="Potential Savings"
          value={summary ? formatCurrency(summary.potential_savings) : "—"}
          subtitle="Estimated"
          loading={loading}
          error={error}
        />
      </div>

      <CostTrendChart
        data={trend?.daily_costs ?? null}
        loading={loading}
        error={error}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <BreakdownChart
          title="Cost by Service"
          data={byService?.breakdown ?? null}
          loading={loading}
          error={error}
        />
        <BreakdownChart
          title="Cost by Project"
          data={byProject?.breakdown ?? null}
          loading={loading}
          error={error}
        />
        <BreakdownChart
          title="Cost by Environment"
          data={byEnvironment?.breakdown ?? null}
          loading={loading}
          error={error}
        />
      </div>

      {summary && (
        <div className="text-xs text-muted-foreground text-right space-y-1">
          <div>
            Data freshness: {summary.freshness_status} · {formatIsoTimestamp(summary.data_freshness)}
          </div>
          {summary.snapshot_label ? <div>Snapshot: {summary.snapshot_label}</div> : null}
        </div>
      )}
    </div>
  );
}
