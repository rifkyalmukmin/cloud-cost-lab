import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CostExplorerPage from "@/app/cost/page";
import OverviewPage from "@/app/page";
import { createQueryClient } from "@/lib/query-client";

// Recharts needs real layout; the pages' data flow is what is under test here.
vi.mock("@/components/cost/cost-trend-chart", () => ({ CostTrendChart: () => <svg /> }));
vi.mock("@/components/cost/service-cost-chart", () => ({ ServiceCostChart: () => <svg /> }));
vi.mock("@/components/cost/project-cost-chart", () => ({ ProjectCostChart: () => <svg /> }));
vi.mock("@/components/cost/environment-cost-chart", () => ({ EnvironmentCostChart: () => <svg /> }));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      getFreshness: vi.fn(),
      getSavings: vi.fn(),
      costTrend: vi.fn(),
      costByService: vi.fn(),
      costByProject: vi.fn(),
      costByEnvironment: vi.fn(),
      listCostRecords: vi.fn(),
    },
  };
});

import { api } from "@/lib/api";

const period = { start: "2026-08-01", end: "2026-09-10" };
const total = { cost: 100, credits: 0, net_cost: 100 };

function mockHappyPath() {
  vi.mocked(api.getFreshness).mockResolvedValue({
    status: "FRESH",
    last_updated: "2026-09-10T00:00:00Z",
    data_age_hours: 3,
    max_age_hours: 24,
  });
  vi.mocked(api.getSavings).mockResolvedValue({
    potential_savings: 0,
    approved_savings: 0,
    implemented: { count: 0, potential_savings: 0 },
    verified: { count: 0, potential_savings: 0 },
    realized_savings: 0,
    rejected_savings_foregone: 0,
    by_status: {
      OPEN: { count: 0, potential_savings: 0 },
      APPROVED: { count: 0, potential_savings: 0 },
      REJECTED: { count: 0, potential_savings: 0 },
      IMPLEMENTED: { count: 0, potential_savings: 0 },
      VERIFIED: { count: 0, potential_savings: 0 },
    },
  });
  vi.mocked(api.costTrend).mockResolvedValue({
    period,
    granularity: "day",
    points: [
      { period: "2026-09-01", cost: 2, credits: 0, net_cost: 2 },
      { period: "2026-09-02", cost: 3, credits: 0, net_cost: 3 },
    ],
  });
  vi.mocked(api.costByService).mockResolvedValue({
    period,
    total,
    rows: [{ service: "compute", service_name: "Compute Engine", cost: 100, credits: 0, net_cost: 100, share_pct: 100 }],
  });
  vi.mocked(api.costByProject).mockResolvedValue({
    period,
    total,
    rows: [{ project_id: "cc-lab-dev", project_name: "Dev", cost: 100, credits: 0, net_cost: 100, share_pct: 100 }],
  });
  vi.mocked(api.costByEnvironment).mockResolvedValue({
    period,
    total,
    rows: [{ environment: "development", cost: 100, credits: 0, net_cost: 100, share_pct: 100 }],
  });
  vi.mocked(api.listCostRecords).mockResolvedValue({
    period,
    pagination: { page: 1, page_size: 25, total_items: 0, total_pages: 1 },
    summary: total,
    items: [],
  });
}

function renderWithClient(ui: ReactNode) {
  return render(<QueryClientProvider client={createQueryClient()}>{ui}</QueryClientProvider>);
}

describe("React Query migrated pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHappyPath();
  });

  it("Overview fetches each resource once and gives charts a text alternative", async () => {
    renderWithClient(<OverviewPage />);

    await screen.findByRole("img", { name: "Daily gross cost trend chart (USD)" });
    expect(screen.getByText(/2 points from 2026-09-01 to 2026-09-02/)).toBeTruthy();
    expect(screen.getByRole("img", { name: "Cost share by service chart" })).toBeTruthy();
    expect(api.costTrend).toHaveBeenCalledTimes(2); // day + month
    expect(api.costByService).toHaveBeenCalledTimes(1);
  });

  it("Cost Explorer refetches with the filter in the request when it changes", async () => {
    renderWithClient(<CostExplorerPage />);
    await screen.findByRole("img", { name: "Cost trend chart, aggregated by day" });
    expect(api.costTrend).toHaveBeenLastCalledWith(
      expect.not.objectContaining({ startDate: expect.anything() }),
      "day",
    );

    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-09-01" } });

    await waitFor(() =>
      expect(api.costTrend).toHaveBeenLastCalledWith(
        expect.objectContaining({ startDate: "2026-09-01" }),
        "day",
      ),
    );
    expect(api.costByService).toHaveBeenLastCalledWith(
      expect.objectContaining({ startDate: "2026-09-01" }),
    );
    // Only the records query is paginated.
    expect(api.listCostRecords).toHaveBeenLastCalledWith(
      expect.objectContaining({ startDate: "2026-09-01", page: 1, pageSize: 25 }),
    );
  });
});
