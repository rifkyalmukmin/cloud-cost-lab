"use client";

import Link from "next/link";
import { useState } from "react";

import { TableCard } from "@/components/data-state";
import {
  PriorityBadge,
  RiskBadge,
  RuleBadge,
  StatusBadge,
} from "@/components/recommendations/rec-ui";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import { api, type RecommendationFilters, type RecommendationItem } from "@/lib/api";
import { formatUsd } from "@/lib/format";

const PAGE_SIZES = [10, 25, 50] as const;
const RULE_OPTIONS = [
  { value: "idle_compute", label: "Idle compute" },
  { value: "oversized_compute", label: "Oversized" },
  { value: "unused_disk", label: "Unused disk" },
  { value: "storage_retention", label: "Storage retention" },
  { value: "cost_anomaly", label: "Cost anomaly" },
];

export default function RecommendationsPage() {
  const [status, setStatus] = useState<string>("OPEN");
  const [ruleId, setRuleId] = useState<string>("");
  const [risk, setRisk] = useState<string>("");
  const [priority, setPriority] = useState<string>("");
  const [sort, setSort] = useState<"priority" | "savings" | "recent">("priority");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [runKey, setRunKey] = useState(0);

  const filters: RecommendationFilters = {
    status: (status || undefined) as RecommendationFilters["status"],
    ruleId: ruleId || undefined,
    risk: (risk || undefined) as RecommendationFilters["risk"],
    priority: (priority || undefined) as RecommendationFilters["priority"],
    sort,
    page,
    pageSize,
  };
  const recommendations = useApi(() => api.listRecommendations(filters), [
    status,
    ruleId,
    risk,
    priority,
    sort,
    page,
    pageSize,
    runKey,
  ]);

  const runEngine = useApi(() => api.runRecommendationEngine(), [runKey]);

  const setFilter = (apply: () => void) => {
    apply();
    setPage(1);
  };

  const summary = recommendations.data?.summary;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Recommendations</h1>
          <p className="text-sm text-muted-foreground">
            Evidence-backed optimization findings. Every recommendation requires human approval — the
            platform never changes infrastructure automatically.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={runEngine.isLoading}
          onClick={() => setRunKey((k) => k + 1)}
        >
          {runEngine.isLoading ? "Running…" : "Run analysis"}
        </Button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <SummaryCard label="Open" value={summary?.by_status.OPEN} tone="sky" />
        <SummaryCard label="Approved" value={summary?.by_status.APPROVED} tone="green" />
        <SummaryCard label="Rejected" value={summary?.by_status.REJECTED} tone="red" />
        <SummaryCard
          label="Potential savings (open+approved)"
          value={summary === undefined ? undefined : formatUsd(summary.open_potential_savings)}
          tone="amber"
        />
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 gap-3 rounded-lg border p-4 md:grid-cols-5">
        <div className="space-y-1.5">
          <Label htmlFor="rec-status" className="text-xs text-muted-foreground">Status</Label>
          <Select
            value={status || "all"}
            onValueChange={(v) => setFilter(() => setStatus(v === "all" || v === null ? "" : v))}
          >
            <SelectTrigger id="rec-status" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="OPEN">OPEN</SelectItem>
              <SelectItem value="APPROVED">APPROVED</SelectItem>
              <SelectItem value="REJECTED">REJECTED</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="rec-rule" className="text-xs text-muted-foreground">Rule</Label>
          <Select
            value={ruleId || "all"}
            onValueChange={(v) => setFilter(() => setRuleId(v === "all" || v === null ? "" : v))}
          >
            <SelectTrigger id="rec-rule" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All rules</SelectItem>
              {RULE_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="rec-risk" className="text-xs text-muted-foreground">Risk (severity)</Label>
          <Select
            value={risk || "all"}
            onValueChange={(v) => setFilter(() => setRisk(v === "all" || v === null ? "" : v))}
          >
            <SelectTrigger id="rec-risk" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severity</SelectItem>
              <SelectItem value="LOW">LOW</SelectItem>
              <SelectItem value="MEDIUM">MEDIUM</SelectItem>
              <SelectItem value="HIGH">HIGH</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="rec-priority" className="text-xs text-muted-foreground">Priority</Label>
          <Select
            value={priority || "all"}
            onValueChange={(v) => setFilter(() => setPriority(v === "all" || v === null ? "" : v))}
          >
            <SelectTrigger id="rec-priority" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All priorities</SelectItem>
              <SelectItem value="HIGH">HIGH</SelectItem>
              <SelectItem value="MEDIUM">MEDIUM</SelectItem>
              <SelectItem value="LOW">LOW</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="rec-sort" className="text-xs text-muted-foreground">Sort by</Label>
          <Select value={sort} onValueChange={(v) => setFilter(() => setSort(v as typeof sort))}>
            <SelectTrigger id="rec-sort" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="priority">Priority score</SelectItem>
              <SelectItem value="savings">Potential savings</SelectItem>
              <SelectItem value="recent">Recently updated</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      <TableCard
        title="Findings"
        description={
          recommendations.data
            ? `${recommendations.data.pagination.total_items} recommendations · sorted by ${sort}`
            : "Priority-ranked optimization findings"
        }
        state={recommendations}
        isEmpty={(recommendations.data?.items.length ?? 0) === 0}
        emptyMessage="No recommendations match the filters"
        footer={
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">
              {recommendations.data
                ? `Page ${recommendations.data.pagination.page} of ${recommendations.data.pagination.total_pages}`
                : ""}
            </span>
            <div className="flex items-center gap-2">
              <Select
                value={String(pageSize)}
                onValueChange={(v) => {
                  setPageSize(Number(v));
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-[110px]" aria-label="Rows per page">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZES.map((s) => (
                    <SelectItem key={s} value={String(s)}>{s} / page</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                disabled={(recommendations.data?.pagination.page ?? 1) <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={
                  (recommendations.data?.pagination.page ?? 1) >=
                  (recommendations.data?.pagination.total_pages ?? 1)
                }
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        }
      >
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Recommendation</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead className="text-right">Current</TableHead>
                <TableHead className="text-right">Potential</TableHead>
                <TableHead className="text-right">Saving</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(recommendations.data?.items ?? []).map((item) => (
                <RecRow key={item.id} item={item} />
              ))}
            </TableBody>
          </Table>
        </div>
      </TableCard>

      <p className="text-xs text-muted-foreground">
        Savings are estimates derived strictly from observed evidence (trailing-window costs and
        utilization statistics); nothing is realized until a change is made and verified in a later
        phase. Approving or rejecting records a human decision — it never triggers an action.
      </p>
    </div>
  );
}

function RecRow({ item }: { item: RecommendationItem }) {
  return (
    <TableRow className="hover:bg-muted/40">
      <TableCell>
        <Link
          href={`/recommendations/${encodeURIComponent(item.id)}`}
          className="group block"
        >
          <span className="font-medium underline-offset-2 group-hover:underline">{item.title}</span>
          <span className="mt-1 block"><RuleBadge ruleId={item.rule_id} /></span>
        </Link>
      </TableCell>
      <TableCell className="text-xs">{item.resource_label}</TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        {formatUsd(item.current_cost)}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        {formatUsd(item.potential_cost)}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        <span className="font-medium text-emerald-600 dark:text-emerald-400">
          {formatUsd(item.potential_savings)}
        </span>
        <span className="block text-xs text-muted-foreground">{item.savings_percentage}%</span>
      </TableCell>
      <TableCell><PriorityBadge priority={item.priority} /></TableCell>
      <TableCell><RiskBadge risk={item.risk} /></TableCell>
      <TableCell><StatusBadge status={item.status} /></TableCell>
    </TableRow>
  );
}

function SummaryCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string | undefined;
  tone: "sky" | "green" | "red" | "amber";
}) {
  const toneClass = {
    sky: "text-sky-600 dark:text-sky-400",
    green: "text-emerald-600 dark:text-emerald-400",
    red: "text-destructive",
    amber: "text-amber-600 dark:text-amber-400",
  }[tone];
  return (
    <div className="rounded-lg border p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${toneClass}`}>
        {value === undefined ? "—" : value}
      </p>
    </div>
  );
}
