import type { CostFilters, Granularity } from "@/lib/api";

/**
 * Central query-key factory. Keys include every input of the fetcher (filters,
 * granularity) so a filter change is a different cache entry, and share
 * prefixes so a mutation can invalidate a whole family at once.
 */
export const queryKeys = {
  freshness: ["freshness"] as const,
  savings: ["savings"] as const,
  cost: {
    all: ["cost"] as const,
    trend: (filters: CostFilters, granularity: Granularity) =>
      ["cost", "trend", filters, granularity] as const,
    byService: (filters: CostFilters) => ["cost", "by-service", filters] as const,
    byProject: (filters: CostFilters) => ["cost", "by-project", filters] as const,
    byEnvironment: (filters: CostFilters) => ["cost", "by-environment", filters] as const,
    records: (filters: CostFilters) => ["cost", "records", filters] as const,
  },
};
