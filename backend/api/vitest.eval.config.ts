import { defineConfig } from "vitest/config";

// Runs the assistant evaluation against live models: `npm run eval`.
// Kept apart from the unit tests because it needs a model server and takes minutes, not seconds.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/evals/**/*.eval.ts"],
    testTimeout: 0,
    hookTimeout: 0,
    reporters: ["default"],
  },
});
