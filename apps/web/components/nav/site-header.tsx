"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/cost", label: "Cost Explorer" },
  { href: "/resources", label: "Resources" },
  { href: "/utilization", label: "Utilization" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/approvals", label: "Approvals" },
  { href: "/budget", label: "Budget" },
  { href: "/forecast", label: "Forecast" },
];

function isCurrent(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="border-b bg-card">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:border focus:bg-background focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2 flex flex-wrap items-center gap-x-4 gap-y-1">
        <Link href="/" className="font-semibold text-sm min-h-11 inline-flex items-center">
          Cloud Cost Lab
        </Link>
        <nav aria-label="Primary" className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted-foreground">
          {LINKS.map((link) => {
            const current = isCurrent(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={current ? "page" : undefined}
                className={`inline-flex items-center min-h-11 px-1 ${
                  current
                    ? "text-foreground font-medium underline underline-offset-4"
                    : "hover:text-foreground"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
