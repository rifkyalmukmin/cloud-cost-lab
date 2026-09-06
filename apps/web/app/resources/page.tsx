"use client";

import Link from "next/link";
import { useState } from "react";

import { TableCard } from "@/components/data-state";
import { EnvironmentBadge } from "@/components/cost/environment-badge";
import { OwnershipValue, UnallocatedBadge, UtilizationMeter } from "@/components/resources/resource-ui";
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
import { useApi } from "@/hooks/use-api";
import { api, type Environment, type ResourceFilters as ApiResourceFilters, type ResourceItem } from "@/lib/api";
import { formatUsd } from "@/lib/format";

interface InventoryFilters {
  projectId: string;
  service: string;
  environment: string;
  status: string;
  owner: string;
  team: string;
  region: string;
  unallocated: boolean;
}

const EMPTY_FILTERS: InventoryFilters = {
  projectId: "",
  service: "",
  environment: "",
  status: "",
  owner: "",
  team: "",
  region: "",
  unallocated: false,
};

const PAGE_SIZES = [10, 25, 50] as const;

function toApiFilters(filters: InventoryFilters, page: number, pageSize: number): ApiResourceFilters {
  return {
    projectId: filters.projectId || undefined,
    service: filters.service || undefined,
    environment: (filters.environment || undefined) as Environment | undefined,
    status: filters.status || undefined,
    owner: filters.owner || undefined,
    team: filters.team || undefined,
    region: filters.region || undefined,
    unallocated: filters.unallocated || undefined,
    page,
    pageSize,
  };
}

export default function ResourcesPage() {
  const [filters, setFilters] = useState<InventoryFilters>({ ...EMPTY_FILTERS });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Filter option sources come from the API, not hardcoded lists.
  const projectOptions = useApi(() => api.costByProject({}), []);
  const serviceOptions = useApi(() => api.costByService({}), []);

  const resources = useApi(() => api.listResources(toApiFilters(filters, page, pageSize)), [
    filters.projectId,
    filters.service,
    filters.environment,
    filters.status,
    filters.owner,
    filters.team,
    filters.region,
    filters.unallocated,
    page,
    pageSize,
  ]);

  const setFilter = (patch: Partial<InventoryFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  };

  const hasActiveFilters =
    Object.entries(filters).some(([key, value]) => key !== "unallocated" && value !== "") || filters.unallocated;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Resource Inventory</h1>
        <p className="text-sm text-muted-foreground">
          Cloud resources joined with their cost (trailing 30 days of data) and latest utilization.
        </p>
        {resources.data?.window ? (
          <p className="text-xs text-muted-foreground">
            Monthly cost window: {resources.data.window.start} → {resources.data.window.end} · filtered total{" "}
            {resources.data.summary ? formatUsd(resources.data.summary.monthly_cost) : "—"} gross
            {resources.data.summary ? ` / ${formatUsd(resources.data.summary.monthly_net_cost)} net` : ""}
          </p>
        ) : null}
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 gap-3 rounded-lg border p-4 md:grid-cols-4 xl:grid-cols-8">
        <div className="space-y-1.5">
          <Label htmlFor="filter-res-project" className="text-xs text-muted-foreground">Project</Label>
          <Select
            value={filters.projectId || "all"}
            onValueChange={(value) => setFilter({ projectId: value === "all" || value === null ? "" : value })}
          >
            <SelectTrigger id="filter-res-project" className="w-full">
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
          <Label htmlFor="filter-res-service" className="text-xs text-muted-foreground">Service</Label>
          <Select
            value={filters.service || "all"}
            onValueChange={(value) => setFilter({ service: value === "all" || value === null ? "" : value })}
          >
            <SelectTrigger id="filter-res-service" className="w-full">
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
          <Label htmlFor="filter-res-environment" className="text-xs text-muted-foreground">Environment</Label>
          <Select
            value={filters.environment || "all"}
            onValueChange={(value) => setFilter({ environment: value === "all" || value === null ? "" : value })}
          >
            <SelectTrigger id="filter-res-environment" className="w-full">
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
        <div className="space-y-1.5">
          <Label htmlFor="filter-res-status" className="text-xs text-muted-foreground">
            Status
          </Label>
          <Input
            id="filter-res-status"
            placeholder="e.g. RUNNING"
            value={filters.status}
            onChange={(e) => setFilter({ status: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="filter-res-region" className="text-xs text-muted-foreground">
            Region
          </Label>
          <Input
            id="filter-res-region"
            placeholder="e.g. us-central1"
            value={filters.region}
            onChange={(e) => setFilter({ region: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="filter-res-owner" className="text-xs text-muted-foreground">
            Owner
          </Label>
          <Input
            id="filter-res-owner"
            placeholder="exact match"
            value={filters.owner}
            onChange={(e) => setFilter({ owner: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="filter-res-team" className="text-xs text-muted-foreground">
            Team
          </Label>
          <Input
            id="filter-res-team"
            placeholder="exact match"
            value={filters.team}
            onChange={(e) => setFilter({ team: e.target.value })}
          />
        </div>
        <div className="flex flex-col justify-end gap-2">
          <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              className="h-3.5 w-3.5 accent-amber-500"
              checked={filters.unallocated}
              onChange={(e) => setFilter({ unallocated: e.target.checked })}
            />
            UNALLOCATED only
          </label>
          <Button variant="outline" disabled={!hasActiveFilters} onClick={() => setFilter({ ...EMPTY_FILTERS })}>
            Reset filters
          </Button>
        </div>
      </div>

      {/* Inventory table */}
      <TableCard
        title="Resources"
        description={
          resources.data
            ? `${resources.data.pagination.total_items.toLocaleString("en-US")} resources · sorted by monthly cost`
            : "Sorted by monthly cost (highest first)"
        }
        state={resources}
        isEmpty={(resources.data?.items.length ?? 0) === 0}
        emptyMessage="No resources match the filters"
        footer={
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">
              {resources.data ? `Page ${resources.data.pagination.page} of ${resources.data.pagination.total_pages}` : ""}
            </span>
            <div className="flex items-center gap-2">
              <Select value={String(pageSize)} onValueChange={(value) => { setPageSize(Number(value)); setPage(1); }}>
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
                disabled={(resources.data?.pagination.page ?? 1) <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={(resources.data?.pagination.page ?? 1) >= (resources.data?.pagination.total_pages ?? 1)}
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
                <TableHead>Type</TableHead>
                <TableHead>Project</TableHead>
                <TableHead>Region</TableHead>
                <TableHead>Environment</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Monthly Cost</TableHead>
                <TableHead>CPU</TableHead>
                <TableHead>Memory</TableHead>
                <TableHead className="text-right">Potential Saving</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(resources.data?.items ?? []).map((item) => (
                <InventoryRow key={item.resource_id} item={item} />
              ))}
            </TableBody>
          </Table>
        </div>
      </TableCard>

      <p className="text-xs text-muted-foreground">
        Potential Saving stays empty until the recommendation engine exists (Phase 4) — this dashboard never
        invents savings numbers. Ownership shows <span className="font-medium">UNALLOCATED</span> when owner/team
        labels are missing.
      </p>
    </div>
  );
}

function InventoryRow({ item }: { item: ResourceItem }) {
  const unallocated = item.owner === null || item.team === null;
  return (
    <TableRow className="hover:bg-muted/40">
      <TableCell>
        <Link href={`/resources/${encodeURIComponent(item.resource_id)}`} className="group block">
          <span className="font-medium underline-offset-2 group-hover:underline">{item.resource_name}</span>
          <span className="block font-mono text-xs text-muted-foreground">{item.resource_id}</span>
          <span className="mt-1 block">
            {unallocated ? (
              <UnallocatedBadge />
            ) : (
              <span className="text-xs text-muted-foreground">
                {item.owner} · {item.team}
              </span>
            )}
          </span>
        </Link>
      </TableCell>
      <TableCell className="text-xs">{item.resource_type}</TableCell>
      <TableCell className="text-xs">{item.project_name}</TableCell>
      <TableCell className="font-mono text-xs">{item.region}</TableCell>
      <TableCell>
        <EnvironmentBadge environment={item.environment} />
      </TableCell>
      <TableCell className="font-mono text-xs">{item.status}</TableCell>
      <TableCell className="text-right">
        {item.monthly_cost !== null ? (
          <span className="font-mono text-sm tabular-nums">{formatUsd(item.monthly_cost)}</span>
        ) : (
          <span className="text-xs text-muted-foreground">no cost data</span>
        )}
      </TableCell>
      <TableCell>
        <UtilizationMeter value={item.cpu_utilization} />
      </TableCell>
      <TableCell>
        <UtilizationMeter value={item.memory_utilization} />
      </TableCell>
      <TableCell className="text-right text-muted-foreground">—</TableCell>
    </TableRow>
  );
}
