import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import { createQueryClient, QUERY_STALE_TIME_MS, shouldRetryQuery } from "@/lib/query-client";

describe("query client defaults", () => {
  it("never retries 4xx responses", () => {
    expect(shouldRetryQuery(0, new ApiError(404, "not found"))).toBe(false);
    expect(shouldRetryQuery(0, new ApiError(422, "invalid"))).toBe(false);
    expect(shouldRetryQuery(0, new ApiError(401, "key"))).toBe(false);
  });

  it("retries network and 5xx failures once", () => {
    expect(shouldRetryQuery(0, new ApiError(0, "cannot reach"))).toBe(true);
    expect(shouldRetryQuery(0, new ApiError(503, "down"))).toBe(true);
    expect(shouldRetryQuery(0, new Error("boom"))).toBe(true);
    expect(shouldRetryQuery(1, new ApiError(503, "down"))).toBe(false);
  });

  it("configures stale time, no focus refetch and no mutation retries", () => {
    const options = createQueryClient().getDefaultOptions();
    expect(options.queries?.staleTime).toBe(QUERY_STALE_TIME_MS);
    expect(options.queries?.refetchOnWindowFocus).toBe(false);
    expect(options.mutations?.retry).toBe(false);
  });
});
