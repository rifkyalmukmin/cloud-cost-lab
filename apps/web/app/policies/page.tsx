"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { api, type PolicyStatus } from "@/lib/api";

const STATUS_TONE: Record<PolicyStatus, string> = {
  PASS: "border-emerald-500/40 text-emerald-600 dark:text-emerald-400",
  WARNING: "border-amber-500/40 text-amber-600 dark:text-amber-400",
  VIOLATION: "border-destructive/40 text-destructive",
};

function StatusBadge({ status }: { status: PolicyStatus }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${STATUS_TONE[status]}`}
    >
      {status}
    </span>
  );
}

export default function PoliciesPage() {
  const policies = useApi(() => api.listPolicies(), []);
  const summary = policies.data?.summary;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Governance Policies</h1>
        <p className="text-sm text-muted-foreground">
          Cost guardrails evaluated against the current data. Outcomes are advisory only — a
          violation produces a warning, evidence and audit information, never an automated action.
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Pass</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
            {summary ? summary.by_status.PASS : "—"}
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Warning</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-amber-600 dark:text-amber-400">
            {summary ? summary.by_status.WARNING : "—"}
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Violation</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-destructive">
            {summary ? summary.by_status.VIOLATION : "—"}
          </p>
        </div>
      </div>

      {policies.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : policies.error ? (
        <Card>
          <CardContent className="pt-6 text-sm text-destructive">{policies.error}</CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {(policies.data?.policies ?? []).map((policy) => (
            <Card key={policy.policy_id}>
              <CardHeader className="flex-row items-start justify-between space-y-0">
                <div>
                  <CardTitle className="text-base">{policy.name}</CardTitle>
                  <p className="mt-0.5 max-w-3xl text-xs text-muted-foreground">
                    {policy.description}
                  </p>
                </div>
                <StatusBadge status={policy.status} />
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm">{policy.summary}</p>
                {Object.keys(policy.config).length > 0 ? (
                  <p className="font-mono text-xs text-muted-foreground">
                    config:{" "}
                    {Object.entries(policy.config)
                      .map(([key, value]) => `${key}=${value}`)
                      .join(", ")}
                  </p>
                ) : null}
                {policy.findings.length > 0 ? (
                  <ul className="space-y-1.5">
                    {policy.findings.map((finding, index) => (
                      <li
                        key={finding.resource_id ?? index}
                        className="rounded-md border bg-muted/30 px-3 py-2 text-xs"
                      >
                        <span className="font-medium">{finding.resource_name}</span>
                        {finding.resource_id ? (
                          <span className="ml-2 font-mono text-muted-foreground">
                            {finding.resource_id}
                          </span>
                        ) : null}
                        <span className="mt-0.5 block text-muted-foreground">{finding.detail}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        NO_PUBLIC_DATABASE deliberately reports WARNING (cannot verify) instead of PASS when the data
        lacks reachability information — an unverifiable control is never treated as compliant.
      </p>
    </div>
  );
}
