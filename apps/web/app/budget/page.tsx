"use client";

import { useState } from "react";

import { TableCard } from "@/components/data-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { api, type BudgetStatus } from "@/lib/api";
import { formatUsd } from "@/lib/format";

const STATUS_TONE: Record<BudgetStatus, string> = {
  HEALTHY: "border-emerald-500/40 text-emerald-600 dark:text-emerald-400",
  WARNING: "border-amber-500/40 text-amber-600 dark:text-amber-400",
  CRITICAL: "border-orange-500/40 text-orange-600 dark:text-orange-400",
  EXCEEDED: "border-destructive/40 text-destructive",
};

function StatusBadge({ status }: { status: BudgetStatus | null }) {
  if (status === null) {
    return <span className="text-xs text-muted-foreground">no data</span>;
  }
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${STATUS_TONE[status]}`}
    >
      {status}
    </span>
  );
}

export default function BudgetPage() {
  const budgets = useApi(() => api.listBudgets(), []);
  const [formOpen, setFormOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Budget</h1>
          <p className="text-sm text-muted-foreground">
            Monthly spending limits with warning / critical thresholds, evaluated against the latest
            month in the data (net of credits).
          </p>
          {budgets.data?.summary.evaluation_month ? (
            <p className="text-xs text-muted-foreground">
              Evaluation month: {budgets.data.summary.evaluation_month} (through{" "}
              {budgets.data.summary.data_end}) · {budgets.data.summary.forecast_over_budget_count}{" "}
              budget(s) forecast to exceed their limit
            </p>
          ) : null}
        </div>
        <Button variant="outline" size="sm" onClick={() => setFormOpen((open) => !open)}>
          {formOpen ? "Cancel" : "New budget"}
        </Button>
      </div>

      {formOpen ? <CreateBudgetForm onDone={() => { setFormOpen(false); budgets.retry(); }} /> : null}

      {budgets.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : budgets.error ? (
        <Card>
          <CardContent className="pt-6 text-sm text-destructive">{budgets.error}</CardContent>
        </Card>
      ) : (budgets.data?.budgets.length ?? 0) === 0 ? (
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            No budgets yet — create one to start tracking.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {budgets.data?.budgets.map((budget: import("@/lib/api").BudgetOut) => (
            <BudgetCard key={budget.id} budget={budget} />
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Status bands are inclusive: exactly at the warning threshold is WARNING, at critical is
        CRITICAL, at 100% is EXCEEDED. The projected month-end is a linear run-rate estimate — never
        a guarantee. Reaching a threshold raises an alert; the platform takes no automatic action on
        your cloud resources.
      </p>
    </div>
  );
}

function BudgetCard({ budget }: { budget: import("@/lib/api").BudgetOut }) {
  const pct = budget.spend_percentage ?? 0;
  const warnPct = budget.warning_threshold;
  const critPct = budget.critical_threshold;
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="text-base">{budget.name}</CardTitle>
          <p className="text-xs text-muted-foreground">
            {budget.period} · scope {budget.scope_type}
            {budget.scope_value ? `: ${budget.scope_value}` : " (everything)"} · limit{" "}
            {formatUsd(budget.limit)}
          </p>
        </div>
        <StatusBadge status={budget.status} />
      </CardHeader>
      <CardContent className="space-y-3">
        {/* progress bar with threshold markers */}
        <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full ${
              budget.status === "EXCEEDED"
                ? "bg-destructive"
                : budget.status === "CRITICAL"
                  ? "bg-orange-500"
                  : budget.status === "WARNING"
                    ? "bg-amber-500"
                    : "bg-emerald-500"
            }`}
            style={{ width: `${Math.min(100, pct)}%` }}
          />
          <div
            className="absolute top-0 h-full w-px bg-amber-600/70"
            style={{ left: `${warnPct}%` }}
            aria-hidden
          />
          <div
            className="absolute top-0 h-full w-px bg-destructive/70"
            style={{ left: `${critPct}%` }}
            aria-hidden
          />
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm md:grid-cols-4">
          <Metric label="Spend (MTD)" value={budget.spend ? formatUsd(budget.spend.amount) : "—"} />
          <Metric
            label="Remaining"
            value={budget.remaining === null ? "—" : formatUsd(budget.remaining)}
          />
          <Metric
            label="Daily average"
            value={budget.spend ? formatUsd(budget.spend.daily_average) : "—"}
          />
          <Metric
            label="Projected month-end (estimate)"
            value={
              budget.projected_month_end === null
                ? "—"
                : formatUsd(budget.projected_month_end)
            }
            warn={budget.forecast_over_budget === true}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          {pct.toFixed(1)}% of limit · warning at {warnPct}% · critical at {critPct}%
          {budget.forecast_over_budget
            ? " · forecast-over-budget: the run-rate would exceed the limit"
            : ""}
        </p>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`font-semibold tabular-nums ${warn ? "text-amber-600 dark:text-amber-400" : ""}`}>
        {value}
      </p>
    </div>
  );
}

function CreateBudgetForm({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("");
  const [scopeType, setScopeType] = useState<string>("all");
  const [scopeValue, setScopeValue] = useState("");
  const [limit, setLimit] = useState("");
  const [warning, setWarning] = useState("70");
  const [critical, setCritical] = useState("90");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.createBudget({
        name,
        scope_type: scopeType as "all" | "project" | "service" | "environment",
        scope_value: scopeType === "all" ? null : scopeValue,
        limit: Number(limit),
        warning_threshold: Number(warning),
        critical_threshold: Number(critical),
      });
      onDone();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Failed to create budget");
    } finally {
      setBusy(false);
    }
  };

  return (
    <TableCard title="Create budget" description="Validated server-side; data-only operation" state={{ isLoading: false, isRefetching: false, error: null, requestId: null, retry: () => {} }} isEmpty={false} emptyMessage="">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
        <div className="col-span-2 space-y-1.5">
          <Label htmlFor="budget-name" className="text-xs text-muted-foreground">Name</Label>
          <Input id="budget-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Lab monthly budget" />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">Scope</Label>
          <Select value={scopeType} onValueChange={(v) => setScopeType(v ?? "all")}>
            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="project">Project</SelectItem>
              <SelectItem value="service">Service</SelectItem>
              <SelectItem value="environment">Environment</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="budget-scope-value" className="text-xs text-muted-foreground">Scope value</Label>
          <Input
            id="budget-scope-value"
            value={scopeValue}
            disabled={scopeType === "all"}
            onChange={(e) => setScopeValue(e.target.value)}
            placeholder={scopeType === "environment" ? "production" : "id"}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="budget-limit" className="text-xs text-muted-foreground">Monthly limit ($)</Label>
          <Input id="budget-limit" type="number" min="0.01" step="0.01" value={limit} onChange={(e) => setLimit(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1.5">
            <Label htmlFor="budget-warn" className="text-xs text-muted-foreground">Warn %</Label>
            <Input id="budget-warn" type="number" min="1" max="99" value={warning} onChange={(e) => setWarning(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="budget-crit" className="text-xs text-muted-foreground">Crit %</Label>
            <Input id="budget-crit" type="number" min="1" max="99" value={critical} onChange={(e) => setCritical(e.target.value)} />
          </div>
        </div>
      </div>
      {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
      <div className="mt-4">
        <Button disabled={busy || !name || !limit} onClick={submit}>
          {busy ? "Creating…" : "Create budget"}
        </Button>
      </div>
    </TableCard>
  );
}
