"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { SectionError } from "@/components/data-state";
import {
  ConfidenceEffortBadges,
  PriorityBadge,
  RiskBadge,
  RuleBadge,
  StatusBadge,
} from "@/components/recommendations/rec-ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { formatUsd } from "@/lib/format";

export default function RecommendationDetailPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(typeof params.id === "string" ? params.id : "");
  const detail = useApi(() => api.getRecommendation(id), [id]);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const data = detail.data;

  const decide = async (kind: "approve" | "reject") => {
    setBusy(true);
    setDecisionError(null);
    try {
      if (kind === "approve") {
        await api.approveRecommendation(id);
      } else {
        await api.rejectRecommendation(id);
      }
      detail.retry();
    } catch (cause) {
      setDecisionError(cause instanceof Error ? cause.message : "Decision failed");
    } finally {
      setBusy(false);
    }
  };

  if (detail.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-72" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
        <Skeleton className="h-[220px]" />
      </div>
    );
  }
  if (detail.error || !data) {
    return (
      <div className="space-y-4">
        <SectionError state={detail} />
        <Button render={<Link href="/recommendations" />} variant="outline" size="sm">
          ← Back to Recommendations
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/recommendations" className="text-xs text-muted-foreground hover:text-foreground">
          ← Recommendations
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight">{data.title}</h1>
          <RuleBadge ruleId={data.rule_id} />
          <StatusBadge status={data.status} />
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {data.resource_id ? (
            <>
              Resource{" "}
              <Link
                href={`/resources/${encodeURIComponent(data.resource_id)}`}
                className="underline underline-offset-2"
              >
                {data.resource_label}
              </Link>
            </>
          ) : (
            <>Scope: {data.resource_label}</>
          )}
          {data.window ? ` · window ${data.window.start} → ${data.window.end}` : ""}
        </p>
      </div>

      {/* Money cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard title="Current cost (window)" value={formatUsd(data.current_cost)} />
        <MetricCard title="Potential cost" value={formatUsd(data.potential_cost)} />
        <MetricCard
          title="Potential saving"
          value={formatUsd(data.potential_savings)}
          sub={`${data.savings_percentage}% of current — estimate, not realized savings`}
          highlight
        />
      </div>

      {/* Answering the seven questions (CLAUDE.md §22) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">What is wrong?</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">{data.problem}</CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evidence</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {data.evidence.map((item, index) => (
              <li key={index} className="flex gap-2 text-sm">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/50" />
                <span>
                  {item.statement}
                  {item.value !== null ? (
                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                      [{item.metric ?? "evidence"} = {item.value}
                      {item.unit ? ` ${item.unit}` : ""}
                      {item.threshold !== null ? ` · threshold ${item.threshold}` : ""}]
                    </span>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recommendation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>{data.recommendation}</p>
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge risk={data.risk} />
            <ConfidenceEffortBadges confidence={data.confidence} effort={data.effort} />
            <PriorityBadge priority={data.priority} />
            <span className="text-xs text-muted-foreground">
              priority score {data.priority_score.toFixed(1)} — project-specific heuristic
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Human approval */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Human approval</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.status === "OPEN" ? (
            <>
              <p className="text-sm text-muted-foreground">
                Approving records a human decision only — the platform will not modify any
                infrastructure. Implementation and verification belong to later phases.
              </p>
              <div className="flex items-center gap-2">
                <Button disabled={busy} onClick={() => decide("approve")}>
                  Approve
                </Button>
                <Button variant="destructive" disabled={busy} onClick={() => decide("reject")}>
                  Reject
                </Button>
              </div>
              {decisionError ? <p className="text-sm text-destructive">{decisionError}</p> : null}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Decision recorded: <StatusBadge status={data.status} /> Only OPEN recommendations can
              change state.
            </p>
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
  highlight,
}: {
  title: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p
          className={`text-2xl font-semibold tabular-nums tracking-tight ${
            highlight ? "text-emerald-600 dark:text-emerald-400" : ""
          }`}
        >
          {value}
        </p>
        {sub ? <p className="mt-1 text-xs text-muted-foreground">{sub}</p> : null}
      </CardContent>
    </Card>
  );
}
