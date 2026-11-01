import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getWeather,
  getCurrency,
  getCve,
  getIpReputation,
  checkBreach,
  dnsLookup,
  wikiSummary,
} from "../shadow_apis";
import type { Env } from "../index";

// ── helpers ───────────────────────────────────────────────────────────────────

const cors = { "Access-Control-Allow-Origin": "*" };

const testEnv = {
  ABUSEIPDB_KEY: "test-abuseipdb-key",
  HIBP_KEY: "test-hibp-key",
} as unknown as Env;

const noKeyEnv = {} as unknown as Env;

function makeRequest(path: string, params: Record<string, string> = {}): Request {
  const url = new URL(`https://api.shadowcypher.site${path}`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  return new Request(url.toString());
}

function mockFetch(status: number, body: unknown, ok = true): ReturnType<typeof vi.fn> {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

// ── getWeather ────────────────────────────────────────────────────────────────

describe("getWeather", () => {
  afterEach(() => vi.restoreAllMocks());

  it("returns 400 when q is missing", async () => {
    const resp = await getWeather(makeRequest("/v1/shadow/weather"), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(400);
    const body = await resp.json();
    expect(body.error).toBe("q is required");
  });

  it("returns 404 when city is not found", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { results: [] }));
    const resp = await getWeather(makeRequest("/v1/shadow/weather", { q: "XYZInvalidCity" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(404);
    const body = await resp.json();
    expect(body.error).toBe("city_not_found");
    vi.unstubAllGlobals();
  });

  it("returns 502 when geocoding upstream fails", async () => {
    vi.stubGlobal("fetch", mockFetch(503, {}, false));
    const resp = await getWeather(makeRequest("/v1/shadow/weather", { q: "London" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(502);
    vi.unstubAllGlobals();
  });

  it("returns weather data on success", async () => {
    const geoBody = { results: [{ name: "London", country: "GB", latitude: 51.5, longitude: -0.1, timezone: "Europe/London" }] };
    const wxBody = {
      current: { temperature_2m: 15, relative_humidity_2m: 70, apparent_temperature: 13, precipitation: 0, wind_speed_10m: 20, weather_code: 2 },
      daily: { time: ["2025-01-01"], weather_code: [1], temperature_2m_max: [17], temperature_2m_min: [10], precipitation_sum: [0] },
    };
    let call = 0;
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => {
      call++;
      return Promise.resolve({ ok: true, status: 200, json: async () => (call === 1 ? geoBody : wxBody) });
    }));
    const resp = await getWeather(makeRequest("/v1/shadow/weather", { q: "London" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json();
    expect(body.location.name).toBe("London");
    expect(body.current.temp_c).toBe(15);
    expect(body.current.temp_f).toBe(59); // 15 * 9/5 + 32
    expect(body.current.condition).toBe("Partly cloudy");
    expect(body.forecast_3day).toHaveLength(1);
    vi.unstubAllGlobals();
  });
});

// ── getCurrency ───────────────────────────────────────────────────────────────

describe("getCurrency", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns 400 for invalid amount", async () => {
    const resp = await getCurrency(makeRequest("/v1/shadow/currency", { from: "USD", to: "EUR", amount: "-5" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 400 for invalid currency code", async () => {
    const resp = await getCurrency(makeRequest("/v1/shadow/currency", { from: "US", to: "EUR", amount: "100" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(400);
  });

  it("returns conversion result on success", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { base: "USD", date: "2025-01-01", rates: { EUR: 93.0 } }));
    const resp = await getCurrency(makeRequest("/v1/shadow/currency", { from: "USD", to: "EUR", amount: "100" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json();
    expect(body.from).toBe("USD");
    expect(body.to).toBe("EUR");
    expect(body.result).toBe(93.0);
    expect(body.formatted).toContain("EUR");
  });

  it("defaults amount to 1 when not provided", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { base: "USD", date: "2025-01-01", rates: { EUR: 0.92 } }));
    const resp = await getCurrency(makeRequest("/v1/shadow/currency", { from: "USD", to: "EUR" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json();
    expect(body.amount).toBe(1);
  });
});

// ── getCve ────────────────────────────────────────────────────────────────────

describe("getCve", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns 400 when q is missing", async () => {
    const resp = await getCve(makeRequest("/v1/shadow/cve"), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(400);
  });

  it("fetches by cveId when q looks like a CVE ID", async () => {
    let capturedUrl = "";
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
      capturedUrl = url;
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ totalResults: 0, vulnerabilities: [] }) });
    }));
    await getCve(makeRequest("/v1/shadow/cve", { q: "CVE-2024-12345" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(capturedUrl).toContain("cveId=CVE-2024-12345");
    expect(capturedUrl).not.toContain("keywordSearch");
  });

  it("fetches by keyword when q is a plain term", async () => {
    let capturedUrl = "";
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
      capturedUrl = url;
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ totalResults: 0, vulnerabilities: [] }) });
    }));
    await getCve(makeRequest("/v1/shadow/cve", { q: "apache log4j" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(capturedUrl).toContain("keywordSearch=");
    expect(capturedUrl).not.toContain("cveId=");
  });

  it("caps limit at 20", async () => {
    let capturedUrl = "";
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
      capturedUrl = url;
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ totalResults: 0, vulnerabilities: [] }) });
    }));
    await getCve(makeRequest("/v1/shadow/cve", { q: "openssl", limit: "999" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(capturedUrl).toContain("resultsPerPage=20");
  });

  it("shapes results correctly from NVD response", async () => {
    const nvdBody = {
      totalResults: 1,
      vulnerabilities: [{
        cve: {
          id: "CVE-2024-0001",
          published: "2024-01-15T00:00:00.000",
          lastModified: "2024-01-16T00:00:00.000",
          descriptions: [{ lang: "en", value: "A test vulnerability in some software component." }],
          metrics: {
            cvssMetricV31: [{ cvssData: { baseScore: 9.8, baseSeverity: "CRITICAL", vectorString: "CVSS:3.1/AV:N/AC:L" } }],
          },
        },
      }],
    };
    vi.stubGlobal("fetch", mockFetch(200, nvdBody));
    const resp = await getCve(makeRequest("/v1/shadow/cve", { q: "CVE-2024-0001" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json();
    expect(body.total).toBe(1);
    expect(body.results[0].id).toBe("CVE-2024-0001");
    expect(body.results[0].score).toBe(9.8);
    expect(body.results[0].severity).toBe("CRITICAL");
    expect(body.results[0].published).toBe("2024-01-15");
    expect(body.results[0].nvd_url).toContain("CVE-2024-0001");
  });
});

// ── checkBreach ───────────────────────────────────────────────────────────────

describe("checkBreach", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns 400 when email is missing", async () => {
    const resp = await checkBreach(makeRequest("/v1/shadow/breach"), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 400 when email has no @", async () => {
    const resp = await checkBreach(makeRequest("/v1/shadow/breach", { email: "notanemail" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 503 when HIBP_KEY is not configured", async () => {
    const resp = await checkBreach(makeRequest("/v1/shadow/breach", { email: "test@example.com" }), noKeyEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(503);
  });

  it("returns not-breached when HIBP returns 404", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => null }));
    const resp = await checkBreach(makeRequest("/v1/shadow/breach", { email: "clean@example.com" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json();
    expect(body.breached).toBe(false);
    expect(body.count).toBe(0);
  });

  it("returns breach data on hit", async () => {
    const breachData = [{
      Name: "AcmeService", Title: "Acme Service", Domain: "acme.com",
      BreachDate: "2023-06-01", PwnCount: 500000, DataClasses: ["Email addresses", "Passwords"],
      IsVerified: true, IsSensitive: false,
    }];
    vi.stubGlobal("fetch", mockFetch(200, breachData));
    const resp = await checkBreach(makeRequest("/v1/shadow/breach", { email: "victim@example.com" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json();
    expect(body.breached).toBe(true);
    expect(body.count).toBe(1);
    expect(body.breaches[0].name).toBe("AcmeService");
    expect(body.breaches[0].pwn_count).toBe(500000);
    expect(body.email).toBe("victim@example.com");
  });

  it("normalizes email to lowercase before lookup", async () => {
    let capturedUrl = "";
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
      capturedUrl = url;
      return Promise.resolve({ ok: false, status: 404, json: async () => null });
    }));
    await checkBreach(makeRequest("/v1/shadow/breach", { email: "UPPER@Example.COM" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(capturedUrl).toContain("upper%40example.com");
  });
});

// ── dnsLookup ─────────────────────────────────────────────────────────────────

describe("dnsLookup", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns 400 when q is missing", async () => {
    const resp = await dnsLookup(makeRequest("/v1/shadow/dns"), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 400 for invalid record type", async () => {
    const resp = await dnsLookup(makeRequest("/v1/shadow/dns", { q: "example.com", type: "INVALID" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(400);
    const body = await resp.json();
    expect(body.error).toContain("invalid type");
  });

  it("defaults to A record type", async () => {
    let capturedUrl = "";
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
      capturedUrl = url;
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ Status: 0, TC: false, RD: true, RA: true, AD: false, CD: false, Question: [], Answer: [] }) });
    }));
    await dnsLookup(makeRequest("/v1/shadow/dns", { q: "example.com" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(capturedUrl).toContain("type=A");
  });

  it("accepts all valid DNS record types", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ Status: 0, TC: false, RD: true, RA: true, AD: false, CD: false, Question: [], Answer: [] }),
    }));
    const types = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA", "PTR", "SRV"];
    for (const type of types) {
      const resp = await dnsLookup(makeRequest("/v1/shadow/dns", { q: "example.com", type }), testEnv, { id: "u1", email: "x@x.com" }, cors);
      expect(resp.status).toBe(200);
    }
  });

  it("maps RCODE 0 to NOERROR", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { Status: 0, TC: false, RD: true, RA: true, AD: false, CD: false, Question: [], Answer: [{ name: "example.com.", type: 1, TTL: 300, data: "93.184.216.34" }] }));
    const resp = await dnsLookup(makeRequest("/v1/shadow/dns", { q: "example.com", type: "A" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("NOERROR");
    expect(body.records).toHaveLength(1);
    expect(body.records[0].value).toBe("93.184.216.34");
  });

  it("maps RCODE 3 to NXDOMAIN", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { Status: 3, TC: false, RD: true, RA: true, AD: false, CD: false, Question: [] }));
    const resp = await dnsLookup(makeRequest("/v1/shadow/dns", { q: "noexist.invalid", type: "A" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("NXDOMAIN");
  });
});

// ── wikiSummary ───────────────────────────────────────────────────────────────

describe("wikiSummary", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns 400 when q is missing", async () => {
    const resp = await wikiSummary(makeRequest("/v1/shadow/wiki"), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 502 on upstream error", async () => {
    vi.stubGlobal("fetch", mockFetch(500, {}, false));
    const resp = await wikiSummary(makeRequest("/v1/shadow/wiki", { q: "Linux" }), testEnv, { id: "u1", email: "x@x.com" }, cors);
    expect(resp.status).toBe(502);
  });
});
