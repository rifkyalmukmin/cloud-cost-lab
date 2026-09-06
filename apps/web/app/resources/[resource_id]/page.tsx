"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { EnvironmentBadge } from "@/components/cost/environment-badge";
import { CostTrendChart } from "@/components/cost/cost-trend-chart";
import { ChartCard } from "@/components/cost/chart-card";
import { DetailCard, OwnershipValue, UnallocatedBadge, UtilizationMeter } from "@/components/resources/resource-ui";
import { UtilizationChart } from "@/components/resources/utilization-chart";
import { SectionError } from "@/components/data-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { api, type ResourceDetailResponse } from "@/lib/api";
import { formatDate, formatUsd } from "@/lib/format";

function isNotFound(error: string | null): boolean {
  return error !== null && error.includes("was not found");
}

export default function ResourceDetailPage() {
  const params = useParams<{ resource_id: string }>();
  const resourceId = decodeURIComponent(typeof params.resource_id === "string" ? params.resource_id : "");

  const detail = useApi(() => api.getResource(resourceId), [resourceId]);
  const data: ResourceDetailResponse | null = detail.data;

  if (detail.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
        <Skeleton className="h-[260px]" />
      </div>
    );
  }

  if (detail.error && isNotFound(detail.error)) {
    return (
      <div className="space-y-4">
        <SectionError state={detail} />
        <Button asChild variant="outline" size="sm">
          <Link href="/resources">← Back to Resource Inventory</Link>
        </Button>
      </div>
    );
  }

  if (detail.error || !data) {
    return (
      <div className="space-y-4">
        <SectionError state={detail} />
      </div>
    );
  }

  const unallocated = data.owner === null || data.team === null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/resources" className="text-xs text-muted-foreground hover:text-foreground">
          ← Resource Inventory
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight">{data.resource_name}</h1>
          <span className="font-mono text-xs text-muted-foreground">{data.resource_id}</span>
          <Badge variant="outline">{data.status}</Badge>
          <EnvironmentBadge environment={data.environment} />
          {unallocated ? <UnallocatedBadge /> : null}
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {data.service_name} · {data.machine_type ?? data.resource_type} · {data.region}
          {data.zone ? ` (${data.zone})` : ""}
        </p>
      </div>

      {/* Cost summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Monthly Cost (30d)"
          value={data.monthly_cost !== null ? formatUsd(data.monthly_cost) : null}
          sub={
            data.monthly_net_cost !== null && data.window
              ? `net ${formatUsd(data.monthly_net_cost)} · ${data.window.start} → ${data.window.end}`
              : "no cost data"
          }
        />
        <MetricCard
          title="Credits (30d)"
          value={data.monthly_credits !== null ? formatUsd(data.monthly_credits) : null}
          sub="discounts applied in the window"
        />
        <MetricCard
          title="Total Cost (all time)"
          value={data.total_cost !== null ? formatUsd(data.total_cost) : null}
          sub={data.total_net_cost !== null ? `net ${formatUsd(data.total_net_cost)}` : undefined}
        />
        <MetricCard
          title="Latest Utilization"
          value={null}
          sub={null}
          custom={
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <span className="w-14 text-xs text-muted-foreground">CPU</span>
                <UtilizationMeter value={data.cpu_utilization} />
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="w-14 text-xs text-muted-foreground">Memory</span>
                <UtilizationMeter value={data.memory_utilization} />
              </div>
            </div>
          }
        />
      </div>

      {/* Cost history */}
      <ChartCard
        title="Cost history"
        description={
          data.cost_history.length > 0
            ? `Daily gross cost · ${data.cost_history[0].date} → ${data.cost_history[data.cost_history.length - 1].date} (USD)`
            : "Daily gross cost (USD)"
        }
        state={detail}
        isEmpty={data.cost_history.length === 0}
        emptyMessage="No cost history for this resource"
      >
        <CostTrendChart
          points={data.cost_history.map((point) => ({
            period: point.date,
            cost: point.cost,
            credits: point.credits,
            net_cost: point.net_cost,
          }))}
        />
      </ChartCard>

      {/* Utilization */}
      <ChartCard
        title="Utilization"
        description="CPU and memory over time (%) — not every resource exposes every metric"
        state={detail}
        isEmpty={data.utilization.length === 0}
        emptyMessage="No utilization data for this resource"
      >
        <UtilizationChart points={data.utilization} />
      </ChartCard>

      {/* Ownership + metadata */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ownership</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <OwnershipRow label="Owner">
              <OwnershipValue value={data.owner} unallocatedHint />
            </OwnershipRow>
            <OwnershipRow label="Team">
              <OwnershipValue value={data.team} unallocatedHint />
            </OwnershipRow>
            <OwnershipRow label="Application">
              <OwnershipValue value={data.application} />
            </OwnershipRow>
            {unallocated ? (
              <p className="text-xs text-muted-foreground">
                Ownership labels are missing — cost for this resource is reported as UNALLOCATED, never attributed by
                guesswork.
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <OwnershipRow label="Type">
              <span className="font-mono text-xs">{data.resource_type}</span>
            </OwnershipRow>
            <OwnershipRow label="Service">
              <span>
                {data.service_name} <span className="font-mono text-xs text-muted-foreground">({data.service_id})</span>
              </span>
            </OwnershipRow>
            <OwnershipRow label="Project">
              <span>
                {data.project_name}{" "}
                <span className="font-mono text-xs text-muted-foreground">({data.project_id})</span>
              </span>
            </OwnershipRow>
            <OwnershipRow label="Region">
              <span className="font-mono text-xs">
                {data.region}
                {data.zone ? ` · ${data.zone}` : ""}
              </span>
            </OwnershipRow>
            <OwnershipRow label="Created">
              <span className="text-xs">{data.created_at ? formatDate(data.created_at.slice(0, 10)) : "—"}</span>
            </OwnershipRow>
            <OwnershipRow label="Last seen">
              <span className="text-xs">{data.last_seen ? formatDate(data.last_seen.slice(0, 10)) : "—"}</span>
            </OwnershipRow>
          </CardContent>
        </Card>
      </div>

      {/* Labels */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Labels</CardTitle>
        </CardHeader>
        <CardContent>
          {Object.keys(data.labels).length === 0 ? (
            <p className="text-sm text-muted-foreground">No labels — this resource is unattributed.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {Object.entries(data.labels).map(([key, value]) => (
                <Badge key={key} variant="secondary" className="font-mono text-xs">
                  {key}={value}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function MetricCard({
  title,
  value,
  sub,
  custom,
}: {
  title: string;
  value: string | null;
  sub?: string | null;
  custom?: React.ReactNode;
}) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {custom ?? (
          <>
            {value === null ? (
              <span className="text-2xl font-semibold text-muted-foreground">—</span>
            ) : (
              <p className="font-semibold tabular-nums text-2xl tracking-tight">{value}</p>
            )}
            {sub ? <p className="mt-1 text-xs text-muted-foreground">{sub}</p> : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function OwnershipRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}
