"use client";

import Link from "next/link";

import { TableCard } from "@/components/data-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { formatUsd } from "@/lib/format";

const LIFECYCLE: Array<{ key: string; label: string; hint: string }> = [
  { key: "OPEN", label: "Potential", hint: "estimated by the rules (not yet approved)" },
  { key: "APPROVED", label: "Approved", hint: "human decision recorded" },
  { key: "IMPLEMENTED", label: "Implemented", hint: "change performed outside the platform" },
  { key: "VERIFIED", label: "Verified", hint: "before/after measured from actual data" },
];

export default function SavingsPage() {
  const savings = useApi(() => api.getSavings(), []);
  const data = savings.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Savings</h1>
        <p className="text-sm text-muted-foreground">
          Potential vs realized savings across the recommendation lifecycle. Realized savings come
          only from VERIFIED recommendations with actual before/after measurements — simulated
          estimates are never called realized.
        </p>
      </div>

      {savings.isLoading ? (
        <div className="grid gap-4 md:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : savings.error ? (
        <Card>
          <CardContent className="pt-6 text-sm text-destructive">{savings.error}</CardContent>
        </Card>
      ) : data ? (
        <>
          {/* Lifecycle pipeline */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
            <StageCard
              title="Potential"
              value={formatUsd(data.potential_savings)}
              sub={`${data.by_status.OPEN?.count ?? 0} open recommendations`}
            />
            <StageCard
              title="Approved"
              value={formatUsd(data.approved_savings)}
              sub={`${data.by_status.APPROVED?.count ?? 0} approved`}
            />
            <StageCard
              title="Implemented"
              value={formatUsd(data.implemented.potential_savings)}
              sub={`${data.implemented.count} implemented`}
            />
            <StageCard
              title="Verified"
              value={formatUsd(data.verified.potential_savings)}
              sub={`${data.verified.count} verified`}
            />
            <StageCard
              title="Realized"
              value={formatUsd(data.realized_savings)}
              sub="measured after change"
              highlight
            />
          </div>

          {/* Status breakdown */}
          <TableCard
            title="Lifecycle breakdown"
            description="Per-status counts and potential savings (estimates) — realized appears only after verification"
            state={savings}
            isEmpty={false}
            emptyMessage="No data"
          >
            <div className="space-y-2">
              {LIFECYCLE.map((stage) => {
                const status = data.by_status[stage.key as keyof typeof data.by_status];
                return (
                  <div key={stage.key} className="rounded-md border px-4 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <span className="text-sm font-medium">{stage.label}</span>
                        <span className="ml-2 text-xs text-muted-foreground">{stage.hint}</span>
                      </div>
                      <div className="flex items-center gap-6 text-sm tabular-nums">
                        <span className="text-muted-foreground">
                          {status?.count ?? 0} recommendation(s)
                        </span>
                        <span className="font-semibold">{formatUsd(status?.potential_savings ?? 0)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
              <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="text-sm font-medium">Rejected</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      savings foregone by human decision
                    </span>
                  </div>
                  <div className="flex items-center gap-6 text-sm tabular-nums">
                    <span className="text-muted-foreground">
                      {data.by_status.REJECTED?.count ?? 0} recommendation(s)
                    </span>
                    <span className="font-semibold">
                      {formatUsd(data.rejected_savings_foregone)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </TableCard>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">How verification works</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>
                Verify compares the <span className="text-foreground">actual</span> daily net cost
                30 days before the implementation date with the{" "}
                <span className="text-foreground">actual</span> daily net cost after it (at least 7
                days of after-data required). The realized number is the monthly-equivalent
                difference of those two measured rates.
              </p>
              <p>
                If post-implementation data does not exist yet, verification refuses (409) — the
                saving stays <span className="text-foreground">potential</span>. A negative result
                (costs went up) is stored as measured, never clamped.
              </p>
              <p>
                Actions happen outside the platform; Implement/Verify only record them in the audit
                trail. Open a recommendation detail page to record Implement/Verify decisions.
              </p>
            </CardContent>
          </Card>
        </>
      ) : null}

      <p className="text-xs text-muted-foreground">
        Recommendations live in{" "}
        <Link href="/recommendations" className="underline underline-offset-2">
          Recommendations
        </Link>
        .
      </p>
    </div>
  );
}

function StageCard({
  title,
  value,
  sub,
  highlight,
}: {
  title: string;
  value: string;
  sub: string;
  highlight?: boolean;
}) {
  return (
    <Card className={`h-full ${highlight ? "border-emerald-500/40" : ""}`}>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p
          className={`text-xl font-semibold tabular-nums tracking-tight ${
            highlight ? "text-emerald-600 dark:text-emerald-400" : ""
          }`}
        >
          {value}
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>
      </CardContent>
    </Card>
  );
}
