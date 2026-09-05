"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { SectionState } from "@/components/data-state";
import { SectionEmpty, SectionError } from "@/components/data-state";
import type { ReactNode } from "react";

/** Shared shell for chart sections: uniform loading / error / empty / success. */
export function ChartCard({
  title,
  description,
  state,
  isEmpty,
  emptyMessage,
  emptyHint,
  action,
  children,
}: {
  title: string;
  description?: string;
  state: SectionState;
  isEmpty: boolean;
  emptyMessage: string;
  emptyHint?: string;
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
          <Skeleton className="h-[240px] w-full" />
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
