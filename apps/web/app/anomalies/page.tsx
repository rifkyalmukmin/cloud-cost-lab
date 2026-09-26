"use client";

import Link from "next/link";
import { useState } from "react";

import { TableCard } from "@/components/data-state";
import { Badge } from "@/components/ui/badge";
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
import { api, type AnomalyFilters, type AnomalyItem } from "@/lib/api";
import { formatUsd } from "@/lib/format";

const PAGE_SIZES = [10, 25, 50] as const;

function SeverityBadge({ severity }: { severity: "LOW" | "MEDIUM" | "HIGH" }) {
  const cls =
    severity === "HIGH"
      ? "border-destructive/40 text-destructive"
      : severity === "MEDIUM"
        ? "border-amber-500/40 text-amber-600 dark:text-amber-400"
        : "border-border text-muted-foreground";
  return (
    <Badge variant="outline" className={`text-[10px] uppercase tracking-wide ${cls}`}>
      {severity}
    </Badge>
  );
}

export default function AnomaliesPage() {
  const [severity, setSeverity] = useState<string>("");
  const [minZ, setMinZ] = useState<string>("2");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(10);

  const anomalies = useApi(
    () =>
      api.listAnomalies({
        severity: (severity || undefined) as AnomalyFilters["severity"],
        minZScore: Number(minZ) || undefined,
        page,
        pageSize,
      }),
    [severity, minZ, page, pageSize],
  );

  const summary = anomalies.data?.summary;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Cost Anomalies</h1>
        <p className="text-sm text-muted-foreground">
          Unexpected daily cost increases vs a 14-day rolling baseline (z-score) — increases only,
          with an absolute noise floor. Detection is advisory; nothing is acted upon automatically.
        </p>
        {summary ? (
          <p className="text-xs text-muted-foreground">
            {summary.total} anomalies · high {summary.by_severity.HIGH} · medium{" "}
            {summary.by_severity.MEDIUM} · low {summary.by_severity.LOW}
          </p>
        ) : null}
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 gap-3 rounded-lg border p-4 md:grid-cols-4">
        <div className="space-y-1.5">
          <Label htmlFor="anom-severity" className="text-xs text-muted-foreground">Severity</Label>
          <Select
            value={severity || "all"}
            onValueChange={(v) => {
              setSeverity(v === "all" || v === null ? "" : v);
              setPage(1);
            }}
          >
            <SelectTrigger id="anom-severity" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              <SelectItem value="HIGH">HIGH</SelectItem>
              <SelectItem value="MEDIUM">MEDIUM</SelectItem>
              <SelectItem value="LOW">LOW</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="anom-z" className="text-xs text-muted-foreground">Min z-score</Label>
          <Select
            value={minZ}
            onValueChange={(v) => {
              setMinZ(v ?? "2");
              setPage(1);
            }}
          >
            <SelectTrigger id="anom-z" className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="2">2.0 (default)</SelectItem>
              <SelectItem value="3">3.0 (stricter)</SelectItem>
              <SelectItem value="4">4.0 (strickest)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="col-span-2 flex items-end justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={severity === "" && minZ === "2"}
            onClick={() => {
              setSeverity("");
              setMinZ("2");
              setPage(1);
            }}
          >
            Reset filters
          </Button>
        </div>
      </div>

      <TableCard
        title="Detected increases"
        description={
          anomalies.data
            ? `${anomalies.data.pagination.total_items} findings · sorted newest first`
            : "Newest first"
        }
        state={anomalies}
        isEmpty={(anomalies.data?.items.length ?? 0) === 0}
        emptyMessage="No anomalies detected with these filters"
        footer={
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">
              {anomalies.data
                ? `Page ${anomalies.data.pagination.page} of ${anomalies.data.pagination.total_pages}`
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
                disabled={(anomalies.data?.pagination.page ?? 1) <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={
                  (anomalies.data?.pagination.page ?? 1) >=
                  (anomalies.data?.pagination.total_pages ?? 1)
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
                <TableHead>Date</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Service</TableHead>
                <TableHead className="text-right">Actual</TableHead>
                <TableHead className="text-right">Expected</TableHead>
                <TableHead className="text-right">Difference</TableHead>
                <TableHead className="text-right">Change</TableHead>
                <TableHead className="text-right">z-score</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead className="text-right">Confidence</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(anomalies.data?.items ?? []).map((item) => (
                <AnomalyRow key={`${item.date}-${item.resource_id ?? "scope"}`} item={item} />
              ))}
            </TableBody>
          </Table>
        </div>
      </TableCard>

      <p className="text-xs text-muted-foreground">
        Expected = mean of the previous 14 available days for the same project/service/resource.
        The warm-up period (first 14 days) is never flagged, and a difference under $0.05 is treated
        as noise. Severity: HIGH ≥ z 4 or +100% · MEDIUM ≥ z 3 or +60% · LOW otherwise. z-score is
        null for perfectly flat baselines (step-changes via the percentage path, LOW confidence).
      </p>
    </div>
  );
}

function AnomalyRow({ item }: { item: AnomalyItem }) {
  return (
    <TableRow className="hover:bg-muted/40">
      <TableCell className="font-mono text-xs">{item.date}</TableCell>
      <TableCell className="text-xs">
        {item.resource_id ? (
          <Link
            href={`/resources/${encodeURIComponent(item.resource_id)}`}
            className="font-medium underline-offset-2 hover:underline"
          >
            {item.resource_name}
          </Link>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
        <span className="block text-muted-foreground">{item.project_name}</span>
      </TableCell>
      <TableCell className="text-xs">{item.service_name}</TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        {formatUsd(item.actual)}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums text-muted-foreground">
        {formatUsd(item.expected)}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums text-destructive">
        +{formatUsd(item.difference)}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        +{item.percentage_change.toFixed(0)}%
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        {item.z_score !== null ? item.z_score.toFixed(1) : "—"}
      </TableCell>
      <TableCell><SeverityBadge severity={item.severity} /></TableCell>
      <TableCell className="text-right text-xs text-muted-foreground">
        {item.confidence.toLowerCase()} ({item.baseline_samples}d)
      </TableCell>
    </TableRow>
  );
}
