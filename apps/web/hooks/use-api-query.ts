"use client";

import { keepPreviousData, useQuery, type QueryKey } from "@tanstack/react-query";

import type { ApiState } from "@/hooks/use-api";
import { ApiError } from "@/lib/api";

/**
 * React Query adapter that returns the same `ApiState` shape as `useApi`, so
 * pages migrate without touching their loading / error / empty UI.
 *
 * Previous data is kept while a new key loads (filter changes) and reported
 * through `isRefetching`, matching `useApi`'s behaviour.
 */
export function useApiQuery<T>(queryKey: QueryKey, fetcher: () => Promise<T>): ApiState<T> {
  const query = useQuery({
    queryKey,
    queryFn: fetcher,
    placeholderData: keepPreviousData,
  });

  const error = query.error;
  const isError = query.isError;
  return {
    data: query.data ?? null,
    isLoading: query.isPending,
    isRefetching: query.isFetching && !query.isPending,
    error: isError
      ? error instanceof Error
        ? error.message
        : "Unexpected error"
      : null,
    requestId: isError && error instanceof ApiError ? error.requestId : null,
    retry: () => {
      void query.refetch();
    },
  };
}
