import type { ShortestConfig } from "@antiwork/shortest";

export default {
  headless: false,
  baseUrl: "http://localhost:3000",
  browser: {
    contextOptions: {
      ignoreHTTPSErrors: true,
    },
  },
  testPattern: "**/*.test.ts",
  ai: {
    provider: "anthropic",
  },
} satisfies ShortestConfig;
