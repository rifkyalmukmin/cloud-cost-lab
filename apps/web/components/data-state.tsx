"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatUsd } from "@/lib/format";
import type { ReactNode } from "react";

/** Shared async-section state consumed by every dashboard card. */
export interface SectionState {
  isLoading: boolean;
  isRefetching: boolean;
  error: string | null;
  requestId: string | null;
  retry: () => void;
}

export function SectionError({ state }: { state: SectionState }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Failed to load data</AlertTitle>
      <AlertDescription>
        <p>{state.error}</p>
        {state.requestId ? (
          <p className="mt-1 font-mono text-xs opacity-80">request id: {state.requestId}</p>
        ) : null}
        <Button size="sm" variant="outline" className="mt-3" onClick={state.retry}>
          Retry
        </Button>
      </AlertDescription>
    </Alert>
  );
}

export function SectionEmpty({ message, hint }: { message: string; hint?: string }) {
  return (
    <div className="flex min-h-32 flex-col items-center justify-center gap-1 rounded-md border border-dashed p-6 text-center">
      <p className="text-sm font-medium">{message}</p>
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

/**
 * Uniform card shell for every data section: title + description, then one of
 * loading / error / empty / success — the four states every section must have.
 */
export function ChartCard({
  title,
  description,
  state,
  isEmpty,
  emptyMessage,
  emptyHint,
  children,
  action,
}: {
  title: string;
  description?: string;
  state: SectionState;
  isEmpty: boolean;
  emptyMessage: string;
  emptyHint?: string;
  children: ReactNode;
  action?: ReactNode;
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
          <div className="space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-[220px] w-full" />
          </div>
        ) : state.error ? (
          <SectionError state={state} />
        ) : isEmpty ? (
          <SectionEmpty message={emptyMessage} hint={emptyHint} />
        ) : (
          <div className={state.isRefetching ? "opacity-70 transition-opacity" : undefined}>{children}</div>
        )}
      </CardContent>
    </Card>
  );
}

/** Table variant of the shared states (skeleton rows instead of a chart box). */
export function TableCard({
  title,
  description,
  state,
  isEmpty,
  emptyMessage,
  children,
  footer,
}: {
  title: string;
  description?: string;
  state: SectionState;
  isEmpty: boolean;
  emptyMessage: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {state.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : state.error ? (
          <SectionError state={state} />
        ) : isEmpty ? (
          <SectionEmpty message={emptyMessage} />
        ) : (
          <>
            <div className={state.isRefetching ? "opacity-70 transition-opacity" : undefined}>{children}</div>
            {footer}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/** Large number used by summary cards: USD, tabular numerals. */
export function CostValue({ value, isRefetching }: { value: number | null; isRefetching?: boolean }) {
  if (value === null) {
    return <span className="text-2xl font-semibold text-muted-foreground">—</span>;
  }
  return (
    <span className={`font-semibold tabular-nums ${isRefetching ? "opacity-70" : ""}`}>
      <span className="text-muted-foreground text-base font-normal">$</span>
      <span className="text-2xl">{formatUsd(value).replace("$", "")}</span>
    </span>
  );
}
