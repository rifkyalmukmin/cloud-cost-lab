"use client";

import { useState } from "react";

import { ChartCard } from "@/components/cost/chart-card";
import { CostTrendChart } from "@/components/cost/cost-trend-chart";
import { EnvironmentBadge } from "@/components/cost/environment-badge";
import { TableCard } from "@/components/data-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import { api, type CostFilters as ApiCostFilters, type Environment, type Granularity } from "@/lib/api";
import { formatDate, formatShare, formatUsd } from "@/lib/format";

interface ExplorerFilters {
  startDate: string;
  endDate: string;
  service: string;
  projectId: string;
  environment: string;
}

const EMPTY_FILTERS: ExplorerFilters = {
  startDate: "",
  endDate: "",
  service: "",
  projectId: "",
  environment: "",
};

const PAGE_SIZES = [10, 25, 50] as const;

function toApiFilters(filters: ExplorerFilters, page: number, pageSize: number): ApiCostFilters {
  return {
    startDate: filters.startDate || undefined,
    endDate: filters.endDate || undefined,
    service: filters.service || undefined,
    projectId: filters.projectId || undefined,
    environment: (filters.environment || undefined) as Environment | undefined,
    page,
    pageSize,
  };
}

export default function CostExplorerPage() {
  const [filters, setFilters] = useState<ExplorerFilters>({ ...EMPTY_FILTERS });
  const [granularity, setGranularity] = useState<Granularity>("day");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(25);

  // Filter option sources: the API itself (full-range breakdowns), not hardcoded lists.
  const serviceOptions = useApi(() => api.costByService({}), []);
  const projectOptions = useApi(() => api.costByProject({}), []);

  const trend = useApi(() => api.costTrend(toApiFilters(filters, 1, 1), granularity), [
    filters.startDate,
    filters.endDate,
    filters.service,
    filters.projectId,
    filters.environment,
    granularity,
  ]);
  const byService = useApi(() => api.costByService(toApiFilters(filters, 1, 1)), [
    filters.startDate,
    filters.endDate,
    filters.service,
    filters.projectId,
    filters.environment,
  ]);
  const byProject = useApi(() => api.costByProject(toApiFilters(filters, 1, 1)), [
    filters.startDate,
    filters.endDate,
    filters.service,
    filters.projectId,
    filters.environment,
  ]);
  const byEnvironment = useApi(() => api.costByEnvironment(toApiFilters(filters, 1, 1)), [
    filters.startDate,
    filters.endDate,
    filters.service,
    filters.projectId,
    filters.environment,
  ]);
  const records = useApi(() => api.listCostRecords(toApiFilters(filters, page, pageSize)), [
    filters.startDate,
    filters.endDate,
    filters.service,
    filters.projectId,
    filters.environment,
    page,
    pageSize,
  ]);

  const setFilter = (patch: Partial<typeof EMPTY_FILTERS>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  };

  const hasActiveFilters = Object.values(filters).some((value) => value !== "");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Cost Explorer</h1>
        <p className="text-sm text-muted-foreground">
          Filter, break down, and page through cost records served by the Cloud Cost Lab API.
        </p>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 gap-3 rounded-lg border p-4 md:grid-cols-3 xl:grid-cols-6">
        <div className="space-y-1.5">
          <Label htmlFor="start-date" className="text-xs text-muted-foreground">
            Start date
          </Label>
          <Input id="start-date" type="date" value={filters.startDate} onChange={(e) => setFilter({ startDate: e.target.value })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="end-date" className="text-xs text-muted-foreground">
            End date
          </Label>
          <Input id="end-date" type="date" value={filters.endDate} onChange={(e) => setFilter({ endDate: e.target.value })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="filter-service" className="text-xs text-muted-foreground">Service</Label>
          <Select value={filters.service || "all"} onValueChange={(value) => setFilter({ service: value === "all" || value === null ? "" : value })}>
            <SelectTrigger id="filter-service" className="w-full">
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
          <Label htmlFor="filter-project" className="text-xs text-muted-foreground">Project</Label>
          <Select value={filters.projectId || "all"} onValueChange={(value) => setFilter({ projectId: value === "all" || value === null ? "" : value })}>
            <SelectTrigger id="filter-project" className="w-full">
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
          <Label htmlFor="filter-environment" className="text-xs text-muted-foreground">Environment</Label>
          <Select
            value={filters.environment || "all"}
            onValueChange={(value) => setFilter({ environment: value === "all" || value === null ? "" : value })}
          >
            <SelectTrigger id="filter-environment" className="w-full">
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
          <Button
            variant="outline"
            className="w-full"
            disabled={!hasActiveFilters}
            onClick={() => setFilter({ ...EMPTY_FILTERS })}
          >
            Reset filters
          </Button>
        </div>
      </div>

      {/* Trend with granularity switch */}
      <ChartCard
        title="Cost trend"
        description={`Aggregated by ${granularity} · gross cost (USD)`}
        state={trend}
        isEmpty={(trend.data?.points.length ?? 0) === 0}
        emptyMessage="No cost data for the selected filters"
        emptyHint="Widen the date range or clear a filter."
        action={
          <Tabs value={granularity} onValueChange={(value) => setGranularity(value as Granularity)}>
            <TabsList>
              <TabsTrigger value="day">Daily</TabsTrigger>
              <TabsTrigger value="week">Weekly</TabsTrigger>
              <TabsTrigger value="month">Monthly</TabsTrigger>
            </TabsList>
          </Tabs>
        }
      >
        {trend.data ? <CostTrendChart points={trend.data.points} /> : null}
      </ChartCard>

      {/* Breakdown tables (respect the active filters) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <TableCard
          title="By Service"
          state={byService}
          isEmpty={(byService.data?.rows.length ?? 0) === 0}
          emptyMessage="No service cost for these filters"
        >
          <BreakdownTable
            headers={["Service", "Cost", "Share"]}
            rows={(byService.data?.rows ?? []).map((row) => [
              row.service_name,
              formatUsd(row.cost),
              formatShare(row.share_pct),
            ])}
          />
        </TableCard>
        <TableCard
          title="By Project"
          state={byProject}
          isEmpty={(byProject.data?.rows.length ?? 0) === 0}
          emptyMessage="No project cost for these filters"
        >
          <BreakdownTable
            headers={["Project", "Cost", "Share"]}
            rows={(byProject.data?.rows ?? []).map((row) => [row.project_name, formatUsd(row.cost), formatShare(row.share_pct)])}
          />
        </TableCard>
        <TableCard
          title="By Environment"
          state={byEnvironment}
          isEmpty={(byEnvironment.data?.rows.length ?? 0) === 0}
          emptyMessage="No environment cost for these filters"
        >
          <BreakdownTable
            headers={["Environment", "Cost", "Share"]}
            rows={(byEnvironment.data?.rows ?? []).map((row) => [row.environment, formatUsd(row.cost), formatShare(row.share_pct)])}
          />
        </TableCard>
      </div>

      {/* Cost records */}
      <TableCard
        title="Cost records"
        description={
          records.data
            ? `${records.data.pagination.total_items.toLocaleString("en-US")} records · summary ${formatUsd(
                records.data.summary.cost,
              )} gross / ${formatUsd(records.data.summary.net_cost)} net`
            : "Newest first · server-side pagination"
        }
        state={records}
        isEmpty={(records.data?.items.length ?? 0) === 0}
        emptyMessage="No cost records match the filters"
        footer={
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">
              {records.data
                ? `Page ${records.data.pagination.page} of ${records.data.pagination.total_pages}`
                : ""}
            </span>
            <div className="flex items-center gap-2">
              <Select value={String(pageSize)} onValueChange={(value) => { setPageSize(Number(value)); setPage(1); }}>
                <SelectTrigger size="sm" className="w-[110px]">
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
                disabled={(records.data?.pagination.page ?? 1) <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={(records.data?.pagination.page ?? 1) >= (records.data?.pagination.total_pages ?? 1)}
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
                <TableHead>Date</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Project</TableHead>
                <TableHead>Region</TableHead>
                <TableHead>Environment</TableHead>
                <TableHead className="text-right">Cost</TableHead>
                <TableHead className="text-right">Net cost</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(records.data?.items ?? []).map((item, index) => (
                <TableRow key={`${item.usage_date}-${item.resource_id ?? "none"}-${index}`}>
                  <TableCell className="whitespace-nowrap">{formatDate(item.usage_date)}</TableCell>
                  <TableCell className="font-mono text-xs">{item.resource_id ?? "—"}</TableCell>
                  <TableCell>{item.service_name}</TableCell>
                  <TableCell className="font-mono text-xs">{item.project_id}</TableCell>
                  <TableCell className="font-mono text-xs">{item.region}</TableCell>
                  <TableCell>
                    <EnvironmentBadge environment={item.environment} />
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{formatUsd(item.cost)}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{formatUsd(item.net_cost)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </TableCard>
    </div>
  );
}

function BreakdownTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {headers.map((header, index) => (
              <TableHead key={header} className={index > 0 ? "text-right" : undefined}>
                {header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={`${row[0]}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <TableCell
                  key={`${row[0]}-${headers[cellIndex]}`}
                  className={`text-xs ${cellIndex > 0 ? "text-right font-mono tabular-nums" : "font-medium"}`}
                >
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
