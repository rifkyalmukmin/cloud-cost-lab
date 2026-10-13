import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Vitest globals are off, so Testing Library cannot auto-register cleanup.
afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
});
