import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Use happy-dom so browser globals like atob/btoa are available
    // (matching the Cloudflare Workers runtime environment)
    environment: "happy-dom",
    include: ["src/__tests__/**/*.test.ts"],
  },
});
