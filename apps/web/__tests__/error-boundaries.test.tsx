import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RouteError from "@/app/error";

describe("app/error.tsx", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => vi.restoreAllMocks());

  it("shows a friendly message, the digest, and no internal error text", () => {
    const error = Object.assign(new Error("SELECT * FROM secret_table failed at /srv/app.py"), {
      digest: "abc123",
    });
    render(<RouteError error={error} reset={() => {}} />);

    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByText("Something went wrong")).toBeTruthy();
    expect(screen.getByText(/abc123/)).toBeTruthy();
    expect(document.body.textContent).not.toContain("secret_table");
    expect(document.body.textContent).not.toContain("/srv/app.py");
  });

  it("omits the digest line when there is none", () => {
    render(<RouteError error={new Error("x")} reset={() => {}} />);
    expect(screen.queryByText(/error digest/)).toBeNull();
  });

  it("calls reset when 'Try again' is clicked", () => {
    const reset = vi.fn();
    render(<RouteError error={new Error("x")} reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("logs the full error to the console only", () => {
    const error = new Error("detail");
    render(<RouteError error={error} reset={() => {}} />);
    expect(console.error).toHaveBeenCalledWith(error);
  });
});
