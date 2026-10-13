import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RecommendationsPage from "@/app/recommendations/page";
import { ApiError, type RecommendationListResponse } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      listRecommendations: vi.fn(),
      runRecommendationEngine: vi.fn(),
    },
  };
});

import { api } from "@/lib/api";

const listRecommendations = vi.mocked(api.listRecommendations);
const runRecommendationEngine = vi.mocked(api.runRecommendationEngine);

const EMPTY_LIST: RecommendationListResponse = {
  summary: {
    by_status: { OPEN: 0, APPROVED: 0, REJECTED: 0, IMPLEMENTED: 0, VERIFIED: 0 },
    open_potential_savings: 0,
  },
  pagination: { page: 1, page_size: 10, total_items: 0, total_pages: 1 },
  items: [],
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return render(<RecommendationsPage />, { wrapper });
}

describe("Recommendations page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listRecommendations.mockResolvedValue(EMPTY_LIST);
  });

  it("only reads the list on mount and never runs the engine", async () => {
    renderPage();

    await waitFor(() => expect(listRecommendations).toHaveBeenCalled());
    await screen.findByText("No recommendations match the filters");
    expect(runRecommendationEngine).not.toHaveBeenCalled();
  });

  it("explains that running the engine is a write action needing an API key", async () => {
    renderPage();
    await screen.findByText("No recommendations match the filters");
    expect(screen.getByText(/write\s+action/)).toBeTruthy();
    expect(screen.getByText(/requires an API\s+key/)).toBeTruthy();
  });

  it("runs the engine once after the button is clicked and shows the result", async () => {
    runRecommendationEngine.mockResolvedValue({ generated: 4, status_preserved: 2, removed: 1 });
    renderPage();
    await screen.findByText("No recommendations match the filters");
    const callsBefore = listRecommendations.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: "Run recommendation engine" }));

    await screen.findByText("Recommendation engine finished");
    expect(runRecommendationEngine).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/4 generated/)).toBeTruthy();
    // The list is re-read after a successful run.
    await waitFor(() => expect(listRecommendations.mock.calls.length).toBeGreaterThan(callsBefore));
  });

  it("disables the button while running", async () => {
    runRecommendationEngine.mockReturnValue(new Promise(() => {}));
    renderPage();
    await screen.findByText("No recommendations match the filters");

    fireEvent.click(screen.getByRole("button", { name: "Run recommendation engine" }));

    const running = await screen.findByRole("button", { name: "Running…" });
    expect((running as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows the API error (e.g. missing API key) when the run fails", async () => {
    runRecommendationEngine.mockRejectedValue(new ApiError(401, "This action needs an API key."));
    renderPage();
    await screen.findByText("No recommendations match the filters");

    fireEvent.click(screen.getByRole("button", { name: "Run recommendation engine" }));

    await screen.findByText("Recommendation engine failed");
    expect(screen.getByText("This action needs an API key.")).toBeTruthy();
  });
});
