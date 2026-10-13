"use client";

import { useEffect } from "react";

import { ErrorPanel } from "@/components/error-panel";

/** Route-level error boundary: renders inside the root layout (header stays). */
export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Full details go to the browser console only, never into the UI.
    console.error(error);
  }, [error]);

  return <ErrorPanel digest={error.digest} onRetry={reset} />;
}
