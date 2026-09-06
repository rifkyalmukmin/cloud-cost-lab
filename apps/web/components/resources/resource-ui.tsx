"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { SectionState } from "@/components/data-state";
import { SectionEmpty, SectionError } from "@/components/data-state";
import type { ReactNode } from "react";

/** Shared shell for resource detail sections (same four states as charts). */
export function DetailCard({
  title,
  description,
  state,
  isEmpty,
  emptyMessage,
  action,
  children,
}: {
  title: string;
  description?: string;
  state: SectionState;
  isEmpty: boolean;
  emptyMessage: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            {description ? <CardDescription>{description}</CardDescription> : null}
          </div>
          {action}
        </div>
      </CardHeader>
      <CardContent>
        {state.isLoading ? (
          <Skeleton className="h-[220px] w-full" />
        ) : state.error ? (
          <SectionError state={state} />
        ) : isEmpty ? (
          <SectionEmpty message={emptyMessage} />
        ) : (
          <div className={state.isRefetching ? "opacity-70 transition-opacity" : undefined}>{children}</div>
        )}
      </CardContent>
    </Card>
  );
}

/** CPU / Memory mini meter used in the inventory table. */
export function UtilizationMeter({ value }: { value: number | null }) {
  if (value === null) {
    return <span className="text-xs text-muted-foreground">no data</span>;
  }
  const clamped = Math.max(0, Math.min(100, value));
  const tone = clamped < 10 ? "bg-amber-500" : clamped > 80 ? "bg-destructive" : "bg-emerald-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-14 overflow-hidden rounded-full bg-muted">
        <div className={`h-full ${tone}`} style={{ width: `${clamped}%` }} />
      </div>
      <span className="font-mono text-xs tabular-nums">{value.toFixed(1)}%</span>
    </div>
  );
}

export function UnallocatedBadge() {
  return (
    <Badge variant="outline" className="border-amber-500/40 text-amber-600 dark:text-amber-400">
      UNALLOCATED
    </Badge>
  );
}

export function OwnershipValue({ value, unallocatedHint }: { value: string | null; unallocatedHint?: boolean }) {
  if (value === null || value === "") {
    return unallocatedHint ? <UnallocatedBadge /> : <span className="text-xs text-muted-foreground">—</span>;
  }
  return <span className="text-sm">{value}</span>;
}
