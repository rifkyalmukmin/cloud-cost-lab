import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

/**
 * Friendly full-section error shell shared by app/error.tsx and
 * app/global-error.tsx. It deliberately never renders `error.message` or the
 * stack: those can contain internal details. The digest is a server-generated
 * hash that lets an operator find the matching server log line.
 */
export function ErrorPanel({
  digest,
  onRetry,
  children,
}: {
  digest?: string;
  onRetry: () => void;
  children?: ReactNode;
}) {
  return (
    <div
      role="alert"
      className="mx-auto flex max-w-lg flex-col items-center gap-3 rounded-lg border p-8 text-center"
    >
      <h1 className="text-xl font-semibold tracking-tight">Something went wrong</h1>
      <p className="text-sm text-muted-foreground">
        The page hit an unexpected error. Your data was not changed. Try again, and if the problem
        persists, check that the Cloud Cost Lab API is running.
      </p>
      {digest ? (
        <p className="font-mono text-xs text-muted-foreground">error digest: {digest}</p>
      ) : null}
      <div className="flex gap-2">
        <Button onClick={onRetry}>Try again</Button>
        {children}
      </div>
    </div>
  );
}
