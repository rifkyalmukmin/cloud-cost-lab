import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { useApiQuery } from "@/hooks/use-api-query";
import { ApiError } from "@/lib/api";

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe("useApiQuery", () => {
  it("maps a successful query to the ApiState shape", async () => {
    const { wrapper } = setup();
    const { result } = renderHook(() => useApiQuery(["k"], () => Promise.resolve(42)), { wrapper });

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.data).toBe(42));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("maps ApiError to message and request id, and retry() refetches", async () => {
    const { wrapper } = setup();
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(500, "boom", "req-9"))
      .mockResolvedValueOnce("ok");
    const { result } = renderHook(() => useApiQuery(["k"], fetcher), { wrapper });

    await waitFor(() => expect(result.current.error).toBe("boom"));
    expect(result.current.requestId).toBe("req-9");

    act(() => result.current.retry());
    await waitFor(() => expect(result.current.data).toBe("ok"));
    expect(result.current.error).toBeNull();
  });

  it("keeps previous data while a new key loads and reports isRefetching", async () => {
    const { wrapper } = setup();
    let resolveB: (value: string) => void = () => {};
    const fetcher = vi.fn((filter: string) =>
      filter === "a" ? Promise.resolve("A") : new Promise<string>((r) => (resolveB = r)),
    );
    const { result, rerender } = renderHook(
      ({ filter }) => useApiQuery(["data", filter], () => fetcher(filter)),
      { wrapper, initialProps: { filter: "a" } },
    );
    await waitFor(() => expect(result.current.data).toBe("A"));

    rerender({ filter: "b" });
    await waitFor(() => expect(result.current.isRefetching).toBe(true));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBe("A");

    act(() => resolveB("B"));
    await waitFor(() => expect(result.current.data).toBe("B"));
    expect(result.current.isRefetching).toBe(false);
  });
});
