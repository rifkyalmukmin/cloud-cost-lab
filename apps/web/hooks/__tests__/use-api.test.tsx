import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useApi } from "@/hooks/use-api";
import { ApiError } from "@/lib/api";

describe("useApi", () => {
  it("starts loading, then exposes the data", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 1 });
    const { result } = renderHook(() => useApi(fetcher, []));

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeNull();

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toEqual({ value: 1 });
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("surfaces ApiError message and request id", async () => {
    const fetcher = vi.fn().mockRejectedValue(new ApiError(500, "boom", "req-123"));
    const { result } = renderHook(() => useApi(fetcher, []));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe("boom");
    expect(result.current.requestId).toBe("req-123");
    expect(result.current.data).toBeNull();
  });

  it("falls back to a generic message for non-Error rejections", async () => {
    const fetcher = vi.fn().mockRejectedValue("nope");
    const { result } = renderHook(() => useApi(fetcher, []));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe("Unexpected error");
  });

  it("retry() re-runs the fetcher and clears the error on success", async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(503, "down"))
      .mockResolvedValueOnce("ok");
    const { result } = renderHook(() => useApi(fetcher, []));

    await waitFor(() => expect(result.current.error).toBe("down"));

    act(() => result.current.retry());
    await waitFor(() => expect(result.current.data).toBe("ok"));
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("refetches when deps change and keeps previous data while refetching", async () => {
    let resolveSecond: (value: string) => void = () => {};
    const fetcher = vi
      .fn<(arg: string) => Promise<string>>()
      .mockResolvedValueOnce("first")
      .mockImplementationOnce(() => new Promise<string>((resolve) => (resolveSecond = resolve)));

    const { result, rerender } = renderHook(({ arg }) => useApi(() => fetcher(arg), [arg]), {
      initialProps: { arg: "a" },
    });
    await waitFor(() => expect(result.current.data).toBe("first"));

    rerender({ arg: "b" });
    await waitFor(() => expect(result.current.isRefetching).toBe(true));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBe("first");

    act(() => resolveSecond("second"));
    await waitFor(() => expect(result.current.data).toBe("second"));
    expect(result.current.isRefetching).toBe(false);
    expect(fetcher).toHaveBeenNthCalledWith(2, "b");
  });

  it("ignores a result that arrives after unmount", async () => {
    let resolve: (value: string) => void = () => {};
    const fetcher = vi.fn(() => new Promise<string>((r) => (resolve = r)));
    const { result, unmount } = renderHook(() => useApi(fetcher, []));
    unmount();
    resolve("late");
    // No state update after unmount: data stays at its last rendered value.
    expect(result.current.data).toBeNull();
  });
});
