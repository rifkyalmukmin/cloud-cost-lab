import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BudgetPage from "@/app/budget/page";
import { ApiError, type BudgetListResponse, type BudgetOut } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, api: { listBudgets: vi.fn(), createBudget: vi.fn() } };
});

import { api } from "@/lib/api";

const listBudgets = vi.mocked(api.listBudgets);

const BUDGET: BudgetOut = {
  id: "b1",
  name: "Lab monthly budget",
  scope_type: "all",
  scope_value: null,
  period: "monthly",
  limit: 100,
  warning_threshold: 70,
  critical_threshold: 90,
  status: "WARNING",
  spend: {
    amount: 75,
    gross_amount: 80,
    daily_average: 5,
    period: { start: "2026-09-01", end: "2026-09-15", days_elapsed: 15, days_in_month: 30 },
  },
  remaining: 25,
  spend_percentage: 75,
  projected_month_end: 150,
  forecast_over_budget: true,
};

function listResponse(budgets: BudgetOut[]): BudgetListResponse {
  return {
    summary: {
      evaluation_month: "2026-09",
      data_end: "2026-09-15",
      budget_count: budgets.length,
      by_status: { HEALTHY: 0, WARNING: budgets.length, CRITICAL: 0, EXCEEDED: 0 },
      forecast_over_budget_count: budgets.length,
    },
    budgets,
  };
}

describe("Budget page", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows a skeleton while loading", () => {
    listBudgets.mockReturnValue(new Promise(() => {}));
    const { container } = render(<BudgetPage />);

    expect(container.querySelector('[data-slot="skeleton"]')).not.toBeNull();
    expect(screen.queryByText("No budgets yet — create one to start tracking.")).toBeNull();
  });

  it("shows the error message when loading fails", async () => {
    listBudgets.mockRejectedValue(new ApiError(500, "Budget service unavailable"));
    render(<BudgetPage />);

    await screen.findByText("Budget service unavailable");
  });

  it("renders budgets with status, spend and the projection labelled as an estimate", async () => {
    listBudgets.mockResolvedValue(listResponse([BUDGET]));
    render(<BudgetPage />);

    await screen.findByText("Lab monthly budget");
    expect(screen.getByText("WARNING")).toBeTruthy();
    expect(screen.getByText("$75.00")).toBeTruthy();
    expect(screen.getByText("$25.00")).toBeTruthy();
    expect(screen.getByText("Projected month-end (estimate)")).toBeTruthy();
    expect(screen.getByText("$150.00")).toBeTruthy();
    expect(screen.getByText(/forecast-over-budget/)).toBeTruthy();
  });

  it("shows the empty state when there are no budgets", async () => {
    listBudgets.mockResolvedValue(listResponse([]));
    render(<BudgetPage />);

    await screen.findByText("No budgets yet — create one to start tracking.");
  });

  it("opens the create form from the header button", async () => {
    listBudgets.mockResolvedValue(listResponse([]));
    render(<BudgetPage />);
    await screen.findByText("No budgets yet — create one to start tracking.");

    fireEvent.click(screen.getByRole("button", { name: "New budget" }));

    expect(screen.getByLabelText("Name")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeTruthy();
  });
});
