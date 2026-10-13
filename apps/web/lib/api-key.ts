/**
 * Write-endpoint API key, kept for the browser tab only (sessionStorage).
 *
 * Deliberately NOT a NEXT_PUBLIC_* variable: those are inlined into the public
 * JS bundle, which would publish the credential to every visitor. The person
 * operating the dashboard pastes their key; it is cleared when the tab closes.
 */
const STORAGE_KEY = "costlab.apiKey";

export function getApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(STORAGE_KEY);
}

export function setApiKey(key: string): void {
  const trimmed = key.trim();
  if (trimmed) window.sessionStorage.setItem(STORAGE_KEY, trimmed);
  else window.sessionStorage.removeItem(STORAGE_KEY);
}
