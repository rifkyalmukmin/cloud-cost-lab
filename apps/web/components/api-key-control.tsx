"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getApiKey, setApiKey } from "@/lib/api-key";
import { useEffect, useState } from "react";

/**
 * Header control for the write-endpoint API key. The key lives in
 * sessionStorage only (see lib/api-key.ts) and is sent solely on POSTs.
 */
export function ApiKeyControl() {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [hasKey, setHasKey] = useState(false);

  // sessionStorage is browser-only: read it after mount to keep SSR markup stable.
  useEffect(() => setHasKey(getApiKey() !== null), []);

  function save(event: React.FormEvent) {
    event.preventDefault();
    setApiKey(draft);
    setHasKey(draft.trim() !== "");
    setDraft("");
    setOpen(false);
  }

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)} aria-expanded={false}>
        {hasKey ? "API key set" : "API key"}
      </Button>
    );
  }
  return (
    <form onSubmit={save} className="flex items-center gap-1">
      <Input
        type="password"
        autoComplete="off"
        aria-label="API key for write actions"
        placeholder="Paste API key (empty clears)"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        className="h-7 w-48"
        autoFocus
      />
      <Button type="submit" size="sm">
        Save
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </form>
  );
}
