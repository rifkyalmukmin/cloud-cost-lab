import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SiteHeader } from "@/components/site-header";

let pathname = "/";
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

// jsdom cannot navigate; keep link clicks from logging "not implemented".
document.addEventListener("click", (event) => event.preventDefault());

describe("SiteHeader mobile navigation", () => {
  beforeEach(() => {
    pathname = "/";
  });

  it("has a toggle wired with aria-expanded and aria-controls, closed by default", () => {
    render(<SiteHeader />);
    const toggle = screen.getByRole("button", { name: "Open navigation menu" });

    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    const panel = document.getElementById(toggle.getAttribute("aria-controls") ?? "");
    expect(panel).not.toBeNull();
    expect(panel?.hidden).toBe(true);
  });

  it("opens the menu with the links and the API key control", () => {
    render(<SiteHeader />);
    const toggle = screen.getByRole("button", { name: "Open navigation menu" });

    fireEvent.click(toggle);

    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(toggle.getAttribute("aria-label")).toBe("Close navigation menu");
    const panel = document.getElementById("mobile-nav") as HTMLElement;
    expect(panel.hidden).toBe(false);
    expect(panel.querySelectorAll("a").length).toBe(10);
    expect(panel.textContent).toContain("API key");
  });

  it("closes on Escape and returns focus to the toggle", () => {
    render(<SiteHeader />);
    const toggle = screen.getByRole("button", { name: "Open navigation menu" });
    fireEvent.click(toggle);

    fireEvent.keyDown(document, { key: "Escape" });

    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(toggle);
  });

  it("closes when a link is chosen and when the route changes", () => {
    const { rerender } = render(<SiteHeader />);
    const toggle = screen.getByRole("button", { name: "Open navigation menu" });
    fireEvent.click(toggle);
    const panel = document.getElementById("mobile-nav") as HTMLElement;

    fireEvent.click(panel.querySelectorAll("a")[1]);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    pathname = "/cost";
    rerender(<SiteHeader />);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
  });

  it("marks the current page with aria-current", () => {
    pathname = "/budget";
    render(<SiteHeader />);
    const current = document.querySelectorAll('a[aria-current="page"]');
    expect(current.length).toBeGreaterThan(0);
    expect(current[0].textContent).toBe("Budget");
  });
});
