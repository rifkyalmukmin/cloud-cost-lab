"use client";

import { Badge } from "@/components/ui/badge";
import type { EvidenceSignals, UtilizationItem } from "@/lib/api";

/** Evidence signal rendering. Colors are semantic: amber = low, red = high,
 * purple = unstable, muted = no data — never green/red "verdicts", these are
 * signals for humans, not recommendations. */
export function signalColor(item: UtilizationItem): string {
  if (item.avg_cpu === null) return "var(--color-signal-missing, #94a3b8)";
  if (item.signals.high_utilization) return "#ef4444";
  if (item.signals.low_utilization) return "#f59e0b";
  if (item.signals.unstable_utilization) return "#a855f7";
  return "#10b981";
}

function SignalBadge({ label, className }: { label: string; className: string }) {
  return <Badge variant="outline" className={`text-[10px] uppercase tracking-wide ${className}`}>{label}</Badge>;
}

/** All evidence badges for one resource — empty when nothing applies. */
export function SignalBadges({ signals, missingMetrics }: { signals: EvidenceSignals; missingMetrics: string[] }) {
  const missingCore = missingMetrics.includes("cpu_utilization");
  return (
    <div className="flex flex-wrap items-center gap-1">
      {signals.low_utilization ? (
        <SignalBadge label="low" className="border-amber-500/40 text-amber-600 dark:text-amber-400" />
      ) : null}
      {signals.high_utilization ? (
        <SignalBadge label="high" className="border-destructive/40 text-destructive" />
      ) : null}
      {signals.unstable_utilization ? (
        <SignalBadge label="unstable" className="border-purple-500/40 text-purple-600 dark:text-purple-400" />
      ) : null}
      {missingCore ? (
        <SignalBadge label="no cpu data" className="border-border text-muted-foreground" />
      ) : null}
      {!signals.low_utilization && !signals.high_utilization && !signals.unstable_utilization && !missingCore ? (
        <span className="text-xs text-muted-foreground">—</span>
      ) : null}
    </div>
  );
}
