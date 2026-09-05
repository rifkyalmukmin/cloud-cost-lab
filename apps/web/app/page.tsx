"use client";

import { CostSummaryCard } from "@/components/cost/cost-summary-card";
import { ChartCard } from "@/components/cost/chart-card";
import { CostTrendChart } from "@/components/cost/cost-trend-chart";
import { EnvironmentCostChart } from "@/components/cost/environment-cost-chart";
import { ProjectCostChart } from "@/components/cost/project-cost-chart";
import { ServiceCostChart } from "@/components/cost/service-cost-chart";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { formatDate, formatMonthKey, formatPct, formatShare, formatUsd } from "@/lib/format";
import { monthlyComparison, lastTwoMonthlyMonths } from "@/lib/metrics";
import { Badge } from "@/components/ui/badge";

function changeBadge(changePct: number | null) {
  if (changePct === null) return <Badge variant="outline">n/a</Badge>;
  if (changePct > 0.05) return <Badge variant="destructive">{formatPct(changePct)}</Badge>;
  if (changePct < -0.05) {
    return (
      <Badge variant="outline" className="border-emerald-500/40 text-emerald-600 dark:text-emerald-400">
        {formatPct(changePct)}
      </Badge>
    );
  }
  return <Badge variant="secondary">{formatPct(changePct)}</Badge>;
}

export default function OverviewPage() {
  const monthly = useApi(() => api.costTrend({}, "month"), []);
  const daily = useApi(() => api.costTrend({}, "day"), []);
  const byService = useApi(() => api.costByService({}), []);
  const byProject = useApi(() => api.costByProject({}), []);
  const byEnvironment = useApi(() => api.costByEnvironment({}), []);

  const comparison =
    monthly.data && daily.data ? monthlyComparison(monthly.data.points, daily.data.points) : null;
  const months = monthly.data ? lastTwoMonthlyMonths(monthly.data.points) : null;
  const netSub = (net: number) => `net ${formatUsd(net)} after credits`;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Cost Overview</h1>
        {monthly.data ? (
          <p className="text-sm text-muted-foreground">
            Data period {formatDate(monthly.data.period.start)} – {formatDate(monthly.data.period.end)} · all values
            estimated (synthetic demo data)
          </p>
        ) : null}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <CostSummaryCard
          title="Current Month Cost"
          description={comparison ? formatMonthKey(comparison.current.monthKey) : undefined}
          badge={comparison ? <Badge variant="outline">MTD · {comparison.current.daysElapsed}d</Badge> : undefined}
          value={comparison ? formatUsd(comparison.current.mtdCost) : null}
          sub={
            months && comparison
              ? netSub(months.current.net_cost)
              : monthly.data && monthly.data.points.length === 0
                ? "No data available"
                : undefined
          }
          state={monthly.isLoading || daily.isLoading ? "loading" : monthly.error || daily.error ? "error" : "success"}
        />
        <CostSummaryCard
          title="Previous Month Cost"
          description={comparison ? formatMonthKey(comparison.previous.monthKey) : undefined}
          badge={<Badge variant="outline">full month</Badge>}
          value={months ? formatUsd(months.previous.cost) : null}
          sub={months ? netSub(months.previous.net_cost) : undefined}
          state={monthly.isLoading ? "loading" : monthly.error ? "error" : "success"}
        />
        <CostSummaryCard
          title="MoM Change"
          description="Month-to-date vs prior MTD"
          badge={changeBadge(comparison?.momChangePct ?? null)}
          value={comparison?.momChangePct !== undefined && comparison?.momChangePct !== null ? formatPct(comparison.momChangePct) : null}
          sub={comparison ? `${comparison.current.daysElapsed} days compared on both sides` : undefined}
          state={monthly.isLoading || daily.isLoading ? "loading" : monthly.error || daily.error ? "error" : "success"}
        />
        <CostSummaryCard
          title="Projected Month-End"
          description="Linear run-rate projection"
          badge={<Badge variant="outline" className="border-sky-500/40 text-sky-600 dark:text-sky-400">estimate</Badge>}
          value={comparison ? formatUsd(comparison.projectedCost) : null}
          sub={
            comparison
              ? `${formatUsd(comparison.current.mtdCost / comparison.current.daysElapsed)}/day × ${comparison.current.daysInMonth} days`
              : undefined
          }
          state={monthly.isLoading || daily.isLoading ? "loading" : monthly.error || daily.error ? "error" : "success"}
        />
        <CostSummaryCard
          title="Potential Savings"
          description="From optimization recommendations"
          badge={<Badge variant="outline">Phase 4</Badge>}
          value={null}
          sub="The recommendation engine is not built yet — no savings number can honestly exist."
          state="empty"
        />
      </div>

      {/* Daily trend */}
      <ChartCard
        title="Daily cost trend"
        description={daily.data ? `${daily.data.period.start} → ${daily.data.period.end} · gross cost per day (USD)` : "Gross cost per day (USD)"}
        state={daily}
        isEmpty={(daily.data?.points.length ?? 0) === 0}
        emptyMessage="No daily cost data available"
        emptyHint="Seed the demo dataset in the backend, then retry."
      >
        {daily.data ? <CostTrendChart points={daily.data.points} /> : null}
      </ChartCard>

      {/* Breakdowns */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard
          title="Cost by Service"
          description={
            byService.data
              ? `Total ${formatUsd(byService.data.total.cost)} · net ${formatUsd(byService.data.total.net_cost)}`
              : "Share of total gross cost"
          }
          state={byService}
          isEmpty={(byService.data?.rows.length ?? 0) === 0}
          emptyMessage="No service breakdown available"
        >
          {byService.data ? <ServiceCostChart rows={byService.data.rows} /> : null}
        </ChartCard>

        <ChartCard
          title="Cost by Project"
          description={
            byProject.data
              ? `Top project: ${byProject.data.rows[0]?.project_name ?? "—"} (${formatShare(byProject.data.rows[0]?.share_pct ?? 0)})`
              : "Gross cost per project"
          }
          state={byProject}
          isEmpty={(byProject.data?.rows.length ?? 0) === 0}
          emptyMessage="No project breakdown available"
        >
          {byProject.data ? <ProjectCostChart rows={byProject.data.rows} /> : null}
        </ChartCard>

        <ChartCard
          title="Cost by Environment"
          description={byEnvironment.data ? "development · staging · production" : "Gross cost per environment"}
          state={byEnvironment}
          isEmpty={(byEnvironment.data?.rows.length ?? 0) === 0}
          emptyMessage="No environment breakdown available"
        >
          {byEnvironment.data ? <EnvironmentCostChart rows={byEnvironment.data.rows} /> : null}
        </ChartCard>
      </div>
    </div>
  );
}
