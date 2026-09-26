"use client";

import { Badge } from "@/components/ui/badge";

/** Severity colors are evidence semantics, not verdicts: amber = medium
 * caution, red = high care, green = low. */
export function RiskBadge({ risk }: { risk: "LOW" | "MEDIUM" | "HIGH" }) {
  const cls =
    risk === "HIGH"
      ? "border-destructive/40 text-destructive"
      : risk === "MEDIUM"
        ? "border-amber-500/40 text-amber-600 dark:text-amber-400"
        : "border-emerald-500/40 text-emerald-600 dark:text-emerald-400";
  return (
    <Badge variant="outline" className={`text-[10px] uppercase tracking-wide ${cls}`}>
      risk {risk}
    </Badge>
  );
}

export function PriorityBadge({ priority }: { priority: "HIGH" | "MEDIUM" | "LOW" }) {
  const cls =
    priority === "HIGH"
      ? "border-destructive/40 text-destructive"
      : priority === "MEDIUM"
        ? "border-amber-500/40 text-amber-600 dark:text-amber-400"
        : "border-border text-muted-foreground";
  return <Badge variant="outline" className={`text-[10px] uppercase tracking-wide ${cls}`}>{priority}</Badge>;
}

export function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "APPROVED"
      ? "border-emerald-500/40 text-emerald-600 dark:text-emerald-400"
      : status === "REJECTED"
        ? "border-destructive/40 text-destructive"
        : status === "OPEN"
          ? "border-sky-500/40 text-sky-600 dark:text-sky-400"
          : "border-border text-muted-foreground";
  return <Badge variant="outline" className={`text-[10px] uppercase tracking-wide ${cls}`}>{status}</Badge>;
}

const RULE_LABELS: Record<string, string> = {
  idle_compute: "Idle compute",
  oversized_compute: "Oversized",
  unused_disk: "Unused disk",
  storage_retention: "Storage retention",
  cost_anomaly: "Cost anomaly",
};

export function RuleBadge({ ruleId }: { ruleId: string }) {
  return (
    <Badge variant="secondary" className="text-[10px]">
      {RULE_LABELS[ruleId] ?? ruleId}
    </Badge>
  );
}

export function ConfidenceEffortBadges({
  confidence,
  effort,
}: {
  confidence: string;
  effort: string;
}) {
  return (
    <span className="flex flex-wrap items-center gap-1">
      <Badge variant="outline" className="text-[10px] text-muted-foreground">
        confidence {confidence.toLowerCase()}
      </Badge>
      <Badge variant="outline" className="text-[10px] text-muted-foreground">
        effort {effort.toLowerCase()}
      </Badge>
    </span>
  );
}
