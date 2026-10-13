import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api";

/** Reads are cheap but the data only changes when the backend is re-seeded or a
 * human records a decision, so 30 s of freshness avoids refetch storms while
 * navigating between pages. */
export const QUERY_STALE_TIME_MS = 30_000;

/**
 * Retry only failures that can plausibly succeed on a second attempt: network
 * errors (status 0) and 5xx responses. A 4xx (validation, auth, not found) is
 * deterministic, so retrying only delays the error state. One retry keeps the
 * error UI reachable within a couple of seconds.
 */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
    return false;
  }
  return failureCount < 1;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: QUERY_STALE_TIME_MS,
        retry: shouldRetryQuery,
        refetchOnWindowFocus: false,
      },
      // Write actions are never retried automatically.
      mutations: { retry: false },
    },
  });
}
