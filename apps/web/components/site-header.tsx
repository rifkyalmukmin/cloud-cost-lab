"use client";

import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/cost", label: "Cost Explorer" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-semibold tracking-tight">
            Cloud Cost Lab
          </Link>
          <span className="hidden text-xs text-muted-foreground md:inline">GCP FinOps &amp; Cloud Cost Optimization</span>
        </div>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                  active ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
          <Badge variant="outline" className="ml-2 border-amber-500/40 text-amber-600 dark:text-amber-400">
            DEMO MODE
          </Badge>
        </nav>
      </div>
    </header>
  );
}
