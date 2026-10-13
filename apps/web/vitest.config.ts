import path from "node:path";

import { defineConfig } from "vitest/config";

export default defineConfig({
  // tsconfig uses "jsx": "preserve" (Next compiles JSX); tests need it transformed.
  oxc: { jsx: { runtime: "automatic" } },
  test: {
    environment: "jsdom",
    include: ["**/__tests__/**/*.test.{ts,tsx}"],
    exclude: ["node_modules/**", ".next/**"],
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
