"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api";

export interface ApiState<T> {
  data: T | null;
  /** True while the first load for the current inputs is in flight. */
  isLoading: boolean;
  /** True while a refetch is in flight after data was already shown. */
  isRefetching: boolean;
  error: string | null;
  requestId: string | null;
  /** Manually re-run the fetcher (used by error-state retry buttons). */
  retry: () => void;
}

/**
 * Small fetch-state hook: every dashboard section gets consistent
 * loading / error / success handling with abort-on-unmount and a retry path.
 * The fetcher identity is captured per render; `deps` control refetching.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: readonly unknown[]): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefetching, setIsRefetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const hasDataRef = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setError(null);
    setRequestId(null);
    if (hasDataRef.current) {
      setIsRefetching(true);
    } else {
      setIsLoading(true);
    }

    fetcherRef
      .current()
      .then((result) => {
        if (!active) return;
        hasDataRef.current = true;
        setData(result);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!active || controller.signal.aborted) return;
        if (cause instanceof ApiError) {
          setError(cause.message);
          setRequestId(cause.requestId);
        } else {
          setError(cause instanceof Error ? cause.message : "Unexpected error");
        }
      })
      .finally(() => {
        if (!active) return;
        setIsLoading(false);
        setIsRefetching(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return { data, isLoading, isRefetching, error, requestId, retry };
}
