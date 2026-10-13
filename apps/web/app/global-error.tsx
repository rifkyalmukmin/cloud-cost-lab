"use client";

import { useEffect } from "react";

import { ErrorPanel } from "@/components/error-panel";

import "./globals.css";

/** Last-resort boundary for errors in the root layout itself. It replaces the
 * layout, so it must render its own <html> and <body>. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-screen items-center justify-center p-6 antialiased">
        <ErrorPanel digest={error.digest} onRetry={reset} />
      </body>
    </html>
  );
}
