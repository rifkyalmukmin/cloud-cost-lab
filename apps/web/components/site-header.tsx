"use client";

import { MenuIcon, XIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ApiKeyControl } from "@/components/api-key-control";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/resources", label: "Resources" },
  { href: "/utilization", label: "Utilization" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/savings", label: "Savings" },
  { href: "/forecast", label: "Forecast" },
  { href: "/anomalies", label: "Anomalies" },
  { href: "/budget", label: "Budget" },
  { href: "/policies", label: "Policies" },
  { href: "/cost", label: "Cost Explorer" },
] as const;

const MOBILE_NAV_ID = "mobile-nav";

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function DemoBadge() {
  return (
    <Badge variant="outline" className="border-amber-500/40 text-amber-600 dark:text-amber-400">
      DEMO MODE
    </Badge>
  );
}

/**
 * Header with a full inline nav on wide screens and a collapsible menu below
 * the `xl` breakpoint. The ten links plus the API-key control do not fit in
 * one row on tablets, so `xl` (not `md`) is where the inline nav takes over.
 */
export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);

  // Close after navigating (the pathname changed).
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Escape closes the menu and returns focus to the toggle.
  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-semibold tracking-tight">
            Cloud Cost Lab
          </Link>
          <span className="hidden text-xs text-muted-foreground 2xl:inline">
            GCP FinOps &amp; Cloud Cost Optimization
          </span>
        </div>

        {/* Wide screens: inline nav */}
        <nav aria-label="Primary" className="hidden items-center gap-1 xl:flex">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? "bg-muted font-medium text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
          <div className="ml-2">
            <ApiKeyControl />
          </div>
          <div className="ml-2">
            <DemoBadge />
          </div>
        </nav>

        {/* Narrow screens: menu toggle */}
        <div className="flex items-center gap-2 xl:hidden">
          <DemoBadge />
          <Button
            ref={toggleRef}
            variant="outline"
            size="icon"
            aria-label={open ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={open}
            aria-controls={MOBILE_NAV_ID}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <XIcon aria-hidden /> : <MenuIcon aria-hidden />}
          </Button>
        </div>
      </div>

      {/* Always in the DOM so aria-controls resolves; contents mount only when open. */}
      <div id={MOBILE_NAV_ID} hidden={!open} className="border-t xl:hidden">
        {open ? (
          <nav aria-label="Primary" className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-3 sm:px-6">
            {NAV_ITEMS.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setOpen(false)}
                  className={`rounded-md px-3 py-2 text-sm transition-colors ${
                    active
                      ? "bg-muted font-medium text-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
            <div className="mt-2 border-t pt-3">
              <ApiKeyControl />
            </div>
          </nav>
        ) : null}
      </div>
    </header>
  );
}
