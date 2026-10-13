import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChartCard, type SectionState } from "@/components/data-state";

const READY: SectionState = {
  isLoading: false,
  isRefetching: false,
  error: null,
  requestId: null,
  retry: () => {},
};

function renderCard(overrides: Partial<React.ComponentProps<typeof ChartCard>> = {}) {
  return render(
    <ChartCard
      title="Daily cost"
      state={READY}
      isEmpty={false}
      emptyMessage="Nothing here"
      chartLabel="Daily cost chart"
      summary="3 points. Maximum $5.00 on 2026-09-02."
      {...overrides}
    >
      <svg data-testid="chart" />
    </ChartCard>,
  );
}

describe("ChartCard", () => {
  it("wraps the chart as a labelled image described by a screen-reader summary", () => {
    renderCard();

    const image = screen.getByRole("img", { name: "Daily cost chart" });
    expect(image.querySelector('[data-testid="chart"]')).not.toBeNull();

    const summary = screen.getByText("3 points. Maximum $5.00 on 2026-09-02.");
    expect(summary.className).toContain("sr-only");
    expect(image.getAttribute("aria-describedby")).toBe(summary.id);
  });

  it("keeps the visible note outside the image wrapper", () => {
    renderCard({ note: <p>Method note</p> });

    const image = screen.getByRole("img", { name: "Daily cost chart" });
    expect(image.contains(screen.getByText("Method note"))).toBe(false);
  });

  it("renders no chart image or summary while loading, on error, or when empty", () => {
    const { rerender } = renderCard({ state: { ...READY, isLoading: true } });
    expect(screen.queryByRole("img")).toBeNull();

    rerender(
      <ChartCard
        title="Daily cost"
        state={{ ...READY, error: "Failed", retry: vi.fn() }}
        isEmpty={false}
        emptyMessage="Nothing here"
        chartLabel="Daily cost chart"
        summary="hidden"
      >
        <svg />
      </ChartCard>,
    );
    expect(screen.getByText("Failed")).toBeTruthy();
    expect(screen.queryByText("hidden")).toBeNull();

    rerender(
      <ChartCard
        title="Daily cost"
        state={READY}
        isEmpty
        emptyMessage="Nothing here"
        chartLabel="Daily cost chart"
        summary={null}
      >
        <svg />
      </ChartCard>,
    );
    expect(screen.getByText("Nothing here")).toBeTruthy();
    expect(screen.queryByRole("img")).toBeNull();
  });
});
