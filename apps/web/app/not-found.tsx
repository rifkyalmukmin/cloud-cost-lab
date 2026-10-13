import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center gap-3 rounded-lg border p-8 text-center">
      <h1 className="text-xl font-semibold tracking-tight">Page not found</h1>
      <p className="text-sm text-muted-foreground">
        This page does not exist in Cloud Cost Lab.
      </p>
      <Link href="/" className={buttonVariants()}>
        Back to Overview
      </Link>
    </div>
  );
}
