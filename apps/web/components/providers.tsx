"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { createQueryClient } from "@/lib/query-client";

/** Client-side providers for the App Router layout (server component). */
export function Providers({ children }: { children: ReactNode }) {
  // useState keeps one client per browser session and avoids sharing a cache
  // between requests during server rendering.
  const [queryClient] = useState(createQueryClient);
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
