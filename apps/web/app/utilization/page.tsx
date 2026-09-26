"use client";

import Link from "next/link";
import { useState } from "react";

import { TableCard, ChartCard } from "@/components/data-state";
import { EnvironmentBadge } from "@/components/cost/environment-badge";
import { CostUtilizationScatter } from "@/components/utilization/cost-utilization-scatter";
import { SignalBadges } from "@/components/utilization/signal-ui";
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
import {
  api,
  type Environment,
  type UtilizationItem,
  type UtilizationQueryFilters,
} from "@/lib/api";
import { formatUsd } from "@/lib/format";

interface PageFilters {
  projectId: string;
  service: string;
  environment: string;
}

const EMPTY_FILTERS: PageFilters = { projectId: "", service: "", environment: "" };
const PAGE_SIZES = [10, 25, 50] as const;

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(1)}%`;
}

export default function UtilizationPage() {
  const [filters, setFilters] = useState<PageFilters>({ ...EMPTY_FILTERS });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Filter option sources come from the API, not hardcoded lists.
  const projectOptions = useApi(() => api.costByProject({}), []);
  const serviceOptions = useApi(() => api.costByService({}), []);

  const queryFilters: UtilizationQueryFilters = {
    projectId: filters.projectId || undefined,
    service: filters.service || undefined,
    environment: (filters.environment || undefined) as Environment | undefined,
    page,
    pageSize,
  };
  const utilization = useApi(() => api.listUtilization(queryFilters), [
    filters.projectId,
    filters.service,
    filters.environment,
    page,
    pageSize,
  ]);

  const setFilter = (patch: Partial<PageFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  };
  const hasActiveFilters = Object.values(filters).some((value) => value !== "");

  const counts = utilization.data?.signal_counts;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Utilization Analysis</h1>
        <p className="text-sm text-muted-foreground">
          How utilized each resource is (avg / min / max / P95 / stddev) joined with the cost of the
          same window — evidence only, recommendations come later.
        </p>
        {utilization.data?.window ? (
          <p className="text-xs text-muted-foreground">
            Analysis window: {utilization.data.window.start} → {utilization.data.window.end} (anchored to
            the data, not the clock)
          </p>
        ) : null}
      </div>

      {/* Evidence summary — counts over the FULL filtered set */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <SignalCountCard label="Low utilization" value={counts?.low_utilization} hint="avg CPU < 20%" tone="amber" />
        <SignalCountCard label="High utilization" value={counts?.high_utilization} hint="avg CPU > 80%" tone="red" />
        <SignalCountCard
          label="Unstable"
          value={counts?.unstable_utilization}
          hint="CPU stddev > 15 pts"
          tone="purple"
        />
        <SignalCountCard label="No CPU data" value={counts?.missing_cpu} hint="metric missing, not zero" tone="gray" />
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 gap-3 rounded-lg border p-4 md:grid-cols-4">
        <div className="space-y-1.5">
          <Label htmlFor="filter-util-project" className="text-xs text-muted-foreground">Project</Label>
          <Select
            value={filters.projectId || "all"}
            onValueChange={(value) => setFilter({ projectId: value === "all" || value === null ? "" : value })}
          >
            <SelectTrigger id="filter-util-project" className="w-full">
              <SelectValue placeholder="All projects" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All projects</SelectItem>
              {(projectOptions.data?.rows ?? []).map((row) => (
                <SelectItem key={row.project_id} value={row.project_id}>
                  {row.project_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="filter-util-service" className="text-xs text-muted-foreground">Service</Label>
          <Select
            value={filters.service || "all"}
            onValueChange={(value) => setFilter({ service: value === "all" || value === null ? "" : value })}
          >
            <SelectTrigger id="filter-util-service" className="w-full">
              <SelectValue placeholder="All services" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All services</SelectItem>
              {(serviceOptions.data?.rows ?? []).map((row) => (
                <SelectItem key={row.service} value={row.service}>
                  {row.service_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="filter-util-env" className="text-xs text-muted-foreground">Environment</Label>
          <Select
            value={filters.environment || "all"}
            onValueChange={(value) => setFilter({ environment: value === "all" || value === null ? "" : value })}
          >
            <SelectTrigger id="filter-util-env" className="w-full">
              <SelectValue placeholder="All environments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All environments</SelectItem>
              <SelectItem value="development">development</SelectItem>
              <SelectItem value="staging">staging</SelectItem>
              <SelectItem value="production">production</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-end">
          <Button variant="outline" disabled={!hasActiveFilters} onClick={() => setFilter({ ...EMPTY_FILTERS })}>
            Reset filters
          </Button>
        </div>
      </div>

      {/* Cost vs Utilization */}
      <ChartCard
        title="Cost vs Utilization"
        description="Cost over the analysis window vs average CPU — one bubble per resource; dashed lines are the 20% / 80% evidence thresholds"
        state={utilization}
        isEmpty={(utilization.data?.items.length ?? 0) === 0}
        emptyMessage="No resources match the filters"
      >
        <CostUtilizationScatter items={utilization.data?.items ?? []} />
        <p className="mt-2 text-xs text-muted-foreground">
          amber = low · red = high · purple = unstable · green = within band · resources without CPU samples
          plot nothing here and stay visible in the table
        </p>
      </ChartCard>

      {/* Per-resource stats */}
      <TableCard
        title="Per-resource metrics"
        description={
          utilization.data
            ? `${utilization.data.pagination.total_items} resources · sorted by avg CPU (no-data last)`
            : "Avg / P95 / stddev per resource"
        }
        state={utilization}
        isEmpty={(utilization.data?.items.length ?? 0) === 0}
        emptyMessage="No resources match the filters"
        footer={
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">
              {utilization.data
                ? `Page ${utilization.data.pagination.page} of ${utilization.data.pagination.total_pages}`
                : ""}
            </span>
            <div className="flex items-center gap-2">
              <Select
                value={String(pageSize)}
                onValueChange={(value) => {
                  setPageSize(Number(value));
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-[110px]" aria-label="Rows per page">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZES.map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size} / page
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                disabled={(utilization.data?.pagination.page ?? 1) <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={
                  (utilization.data?.pagination.page ?? 1) >=
                  (utilization.data?.pagination.total_pages ?? 1)
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
                <TableHead>Resource</TableHead>
                <TableHead>Project</TableHead>
                <TableHead>Env</TableHead>
                <TableHead className="text-right">Avg CPU</TableHead>
                <TableHead className="text-right">P95 CPU</TableHead>
                <TableHead className="text-right">Avg Mem</TableHead>
                <TableHead className="text-right">CPU σ</TableHead>
                <TableHead className="text-right">Cost (window)</TableHead>
                <TableHead>Evidence</TableHead>
                <TableHead className="text-right">Missing</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(utilization.data?.items ?? []).map((item) => (
                <UtilizationRow key={item.resource_id} item={item} />
              ))}
            </TableBody>
          </Table>
        </div>
      </TableCard>

      <p className="text-xs text-muted-foreground">
        Metrics with no samples in the window are listed as missing — never shown as 0%. A 0% CPU
        observation is a real zero and stays in the stats. Latency is part of the model but the mock
        dataset contains no latency samples, so it appears as missing for every resource. These flags are
        project-specific heuristics — evidence for the future recommendation engine, not automatic advice.
      </p>
    </div>
  );
}

function UtilizationRow({ item }: { item: UtilizationItem }) {
  const cpu = item.metrics.cpu_utilization;
  const memory = item.metrics.memory_utilization;
  return (
    <TableRow className="hover:bg-muted/40">
      <TableCell>
        <Link href={`/resources/${encodeURIComponent(item.resource_id)}`} className="group block">
          <span className="font-medium underline-offset-2 group-hover:underline">{item.resource_name}</span>
          <span className="block font-mono text-xs text-muted-foreground">{item.resource_id}</span>
        </Link>
      </TableCell>
      <TableCell className="text-xs">{item.project_name}</TableCell>
      <TableCell>
        <EnvironmentBadge environment={item.environment} />
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">{pct(item.avg_cpu)}</TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">{pct(cpu ? cpu.p95 : null)}</TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">{pct(memory ? memory.avg : null)}</TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        {cpu && cpu.stddev !== null ? `±${cpu.stddev.toFixed(1)}` : "—"}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        {item.cost_in_window !== null ? formatUsd(item.cost_in_window) : "—"}
      </TableCell>
      <TableCell>
        <SignalBadges signals={item.signals} missingMetrics={item.missing_metrics} />
      </TableCell>
      <TableCell className="text-right font-mono text-xs text-muted-foreground">
        {item.missing_metrics.length > 0 ? item.missing_metrics.length : "—"}
      </TableCell>
    </TableRow>
  );
}

function SignalCountCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: number | undefined;
  hint: string;
  tone: "amber" | "red" | "purple" | "gray";
}) {
  const toneClass = {
    amber: "text-amber-600 dark:text-amber-400",
    red: "text-destructive",
    purple: "text-purple-600 dark:text-purple-400",
    gray: "text-muted-foreground",
  }[tone];
  return (
    <div className="rounded-lg border p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${toneClass}`}>
        {value === undefined ? "—" : value}
      </p>
      <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}
