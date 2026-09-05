"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReactNode } from "react";

/**
 * Overview metric card. `state === "loading" | "error" | "empty" | "success"`
 * is derived by the caller; the card only renders the right variant.
 */
export function CostSummaryCard({
  title,
  description,
  value,
  badge,
  sub,
  state,
}: {
  title: string;
  description?: string;
  /** Preformatted display value, or null for the empty/placeholder state. */
  value: string | null;
  badge?: ReactNode;
  sub?: ReactNode;
  state: "loading" | "error" | "empty" | "success";
}) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {title}
          </CardTitle>
          {badge}
        </div>
        {description ? <CardDescription className="text-xs">{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {state === "loading" ? (
          <Skeleton className="h-8 w-24" />
        ) : state === "error" ? (
          <p className="text-sm text-destructive">Unavailable — see section error</p>
        ) : state === "empty" || value === null ? (
          <span className="text-2xl font-semibold text-muted-foreground">—</span>
        ) : (
          <p className="font-semibold tabular-nums text-2xl tracking-tight">{value}</p>
        )}
        {state !== "loading" && state !== "error" && sub ? (
          <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
