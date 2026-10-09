/**
 * Threat Feed — CVE + IOC ingestion from public feeds.
 *
 * Sources (all free, no API key):
 *   NVD NIST CVE 2.0 API  — https://services.nvd.nist.gov/rest/json/cves/2.0
 *   Cloudflare Edge Cache — 1-hour TTL so we don't hammer NVD
 *
 * Endpoints:
 *   GET /v1/threats        — recent CVEs (last 7 days), severity-filtered
 *   GET /v1/threats/stats  — counts by severity for the dashboard strip
 */

import type { Env } from "./index";

export interface CVEItem {
  id: string;
  description: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
  cvss: number | null;
  published: string;
  modified: string;
  url: string;
  cwe: string | null;
}

export interface ThreatStats {
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
  as_of: string;
}

const NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0";

export function severityFromCvss(score: number | null): CVEItem["severity"] {
  if (score === null) return "NONE";
  if (score >= 9.0) return "CRITICAL";
  if (score >= 7.0) return "HIGH";
  if (score >= 4.0) return "MEDIUM";
  if (score > 0) return "LOW";
  return "NONE";
}

async function fetchNvd(params: Record<string, string>): Promise<{ items: CVEItem[]; totalResults: number }> {
  const qs = new URLSearchParams(params).toString();
  const url = `${NVD_BASE}?${qs}`;

  const resp = await fetch(url, {
    headers: {
      "User-Agent": "ShadowCypher/1.0 (security dashboard; contact: hello@shadowcypher.site)",
    },
    // Cloudflare edge caches for 1 hour
    cf: { cacheTtl: 3600, cacheEverything: true } as RequestInitCfProperties,
  });

  if (!resp.ok) {
    throw new Error(`NVD API ${resp.status}: ${resp.statusText}`);
  }

  const data = (await resp.json()) as {
    totalResults?: number;
    vulnerabilities: Array<{
      cve: {
        id: string;
        published: string;
        lastModified: string;
        descriptions: Array<{ lang: string; value: string }>;
        metrics?: {
          cvssMetricV31?: Array<{ cvssData: { baseScore: number } }>;
          cvssMetricV30?: Array<{ cvssData: { baseScore: number } }>;
          cvssMetricV2?: Array<{ cvssData: { baseScore: number } }>;
        };
        weaknesses?: Array<{
          description: Array<{ lang: string; value: string }>;
        }>;
      };
    }>;
  };

  const items = (data.vulnerabilities || []).map((v) => {
    const cve = v.cve;
    const desc =
      cve.descriptions.find((d) => d.lang === "en")?.value || "No description available.";

    // Prefer CVSSv3.1 → v3.0 → v2
    const score =
      cve.metrics?.cvssMetricV31?.[0]?.cvssData.baseScore ??
      cve.metrics?.cvssMetricV30?.[0]?.cvssData.baseScore ??
      cve.metrics?.cvssMetricV2?.[0]?.cvssData.baseScore ??
      null;

    const cwe =
      cve.weaknesses?.[0]?.description.find((d) => d.lang === "en")?.value ?? null;

    return {
      id: cve.id,
      description: desc.length > 300 ? desc.slice(0, 297) + "..." : desc,
      severity: severityFromCvss(score),
      cvss: score,
      published: cve.published,
      modified: cve.lastModified,
      url: `https://nvd.nist.gov/vuln/detail/${cve.id}`,
      cwe,
    };
  });
  return { items, totalResults: data.totalResults ?? items.length };
}

function daysAgoIso(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().replace(/\.\d{3}Z$/, ".000Z");
}

export async function getThreats(
  _req: Request,
  _env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit = {}
): Promise<Response> {
  const url = new URL(_req.url);
  const severity = url.searchParams.get("severity")?.toUpperCase() || null;
  const days = Math.min(parseInt(url.searchParams.get("days") || "7", 10), 30);
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "25", 10), 100);
  const page = Math.max(1, parseInt(url.searchParams.get("page") || "1", 10));
  const q = url.searchParams.get("q")?.trim().slice(0, 100) || null;

  try {
    const params: Record<string, string> = {
      pubStartDate: daysAgoIso(days),
      resultsPerPage: String(limit),
      startIndex: String((page - 1) * limit),
    };

    if (severity && ["CRITICAL", "HIGH", "MEDIUM", "LOW"].includes(severity)) {
      params.cvssV3Severity = severity;
    }
    if (q) {
      params.keywordSearch = q;
    }

    const { items: cves, totalResults } = await fetchNvd(params);

    return new Response(JSON.stringify({ cves, total: cves.length, total_results: totalResults, page, days, as_of: new Date().toISOString() }), {
      headers: { "Content-Type": "application/json", "Cache-Control": "private, max-age=3600", ...cors },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return new Response(JSON.stringify({ error: "threat_feed_unavailable", detail: msg }), {
      status: 502,
      headers: { "Content-Type": "application/json", ...cors },
    });
  }
}

export async function getThreatStats(
  _req: Request,
  _env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit = {}
): Promise<Response> {
  try {
    const [cCount, hCount, mCount, lCount] = await Promise.all([
      fetchCount("CRITICAL"),
      fetchCount("HIGH"),
      fetchCount("MEDIUM"),
      fetchCount("LOW"),
    ]);

    const stats: ThreatStats = {
      critical: cCount,
      high: hCount,
      medium: mCount,
      low: lCount,
      total: cCount + hCount + mCount + lCount,
      as_of: new Date().toISOString(),
    };

    return new Response(JSON.stringify(stats), {
      headers: { "Content-Type": "application/json", "Cache-Control": "private, max-age=3600", ...cors },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return new Response(JSON.stringify({ error: "stats_unavailable", detail: msg }), {
      status: 502,
      headers: { "Content-Type": "application/json", ...cors },
    });
  }
}

async function fetchCount(severity: string): Promise<number> {
  const url = `${NVD_BASE}?pubStartDate=${daysAgoIso(7)}&cvssV3Severity=${severity}&resultsPerPage=1`;
  const resp = await fetch(url, {
    headers: { "User-Agent": "ShadowCypher/1.0 (contact: hello@shadowcypher.site)" },
    cf: { cacheTtl: 3600, cacheEverything: true } as RequestInitCfProperties,
  });
  if (!resp.ok) return 0;
  const data = (await resp.json()) as { totalResults?: number };
  return data.totalResults ?? 0;
}
