import { describe, it, expect } from "vitest";
import { severityFromCvss } from "../threats";

describe("severityFromCvss", () => {
  it("returns NONE for null score", () => {
    expect(severityFromCvss(null)).toBe("NONE");
  });

  it("returns NONE for score of 0", () => {
    expect(severityFromCvss(0)).toBe("NONE");
  });

  it("returns LOW for score just above 0", () => {
    expect(severityFromCvss(0.1)).toBe("LOW");
  });

  it("returns LOW for score of 3.9", () => {
    expect(severityFromCvss(3.9)).toBe("LOW");
  });

  it("returns MEDIUM at the 4.0 boundary", () => {
    expect(severityFromCvss(4.0)).toBe("MEDIUM");
  });

  it("returns MEDIUM for score of 6.9", () => {
    expect(severityFromCvss(6.9)).toBe("MEDIUM");
  });

  it("returns HIGH at the 7.0 boundary", () => {
    expect(severityFromCvss(7.0)).toBe("HIGH");
  });

  it("returns HIGH for score of 8.9", () => {
    expect(severityFromCvss(8.9)).toBe("HIGH");
  });

  it("returns CRITICAL at the 9.0 boundary", () => {
    expect(severityFromCvss(9.0)).toBe("CRITICAL");
  });

  it("returns CRITICAL for score of 10.0", () => {
    expect(severityFromCvss(10.0)).toBe("CRITICAL");
  });

  it("returns CRITICAL for scores above 10 (edge case)", () => {
    expect(severityFromCvss(10.1)).toBe("CRITICAL");
  });

  it("covers the full range in order: NONE < LOW < MEDIUM < HIGH < CRITICAL", () => {
    const scores = [null, 0, 0.1, 4.0, 7.0, 9.0];
    const severities = scores.map(severityFromCvss);
    expect(severities).toEqual(["NONE", "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]);
  });
});
