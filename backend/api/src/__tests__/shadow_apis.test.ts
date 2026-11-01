import { describe, it, expect, vi, afterEach } from "vitest";
import {
  getWeather,
  getCurrency,
  getCve,
  getIpReputation,
  checkBreach,
  dnsLookup,
  webSearch,
  wikiSummary,
  ddgInstant,
} from "../shadow_apis";
import type { Env } from "../index";

// ── helpers ───────────────────────────────────────────────────────────────────

const cors = { "Access-Control-Allow-Origin": "*" };
const user = { id: "u1", email: "x@x.com" };

const testEnv = {
  ABUSEIPDB_KEY: "test-abuseipdb-key",
  HIBP_KEY: "test-hibp-key",
} as unknown as Env;

const noKeyEnv = {} as unknown as Env;

type ErrorBody = { error: string };

function makeRequest(path: string, params: Record<string, string> = {}): Request {
  const url = new URL(`https://api.shadowcypher.site${path}`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  return new Request(url.toString());
}

function fakeResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue(fakeResponse(status, body));
}

function calledUrl(fetchMock: ReturnType<typeof vi.fn>, call = 0): URL {
  return new URL(String(fetchMock.mock.calls[call][0]));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

// ── getWeather ────────────────────────────────────────────────────────────────

describe("getWeather", () => {
  it("returns 400 when q is missing", async () => {
    const resp = await getWeather(makeRequest("/v1/shadow/weather"), testEnv, user, cors);
    expect(resp.status).toBe(400);
    expect((await resp.json<ErrorBody>()).error).toBe("q is required");
  });

  it("returns 404 when city is not found", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { results: [] }));
    const resp = await getWeather(makeRequest("/v1/shadow/weather", { q: "XYZInvalidCity" }), testEnv, user, cors);
    expect(resp.status).toBe(404);
    expect((await resp.json<ErrorBody>()).error).toBe("city_not_found");
  });

  it("returns 502 when geocoding upstream fails", async () => {
    vi.stubGlobal("fetch", mockFetch(503, {}));
    const resp = await getWeather(makeRequest("/v1/shadow/weather", { q: "London" }), testEnv, user, cors);
    expect(resp.status).toBe(502);
  });

  it("returns current conditions and forecast on success", async () => {
    const geoBody = { results: [{ name: "London", country: "GB", latitude: 51.5, longitude: -0.1, timezone: "Europe/London" }] };
    const wxBody = {
      current: { temperature_2m: 15, relative_humidity_2m: 70, apparent_temperature: 13, precipitation: 0, wind_speed_10m: 20, weather_code: 2 },
      daily: { time: ["2025-01-01"], weather_code: [1], temperature_2m_max: [17], temperature_2m_min: [10], precipitation_sum: [0] },
    };
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(fakeResponse(200, geoBody))
      .mockResolvedValueOnce(fakeResponse(200, wxBody)));
    const resp = await getWeather(makeRequest("/v1/shadow/weather", { q: "London" }), testEnv, user, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<{
      location: { name: string };
      current: { temp_c: number; temp_f: number; condition: string };
      forecast_3day: unknown[];
    }>();
    expect(body.location.name).toBe("London");
    expect(body.current.temp_c).toBe(15);
    expect(body.current.temp_f).toBe(59);
    expect(body.current.condition).toBe("Partly cloudy");
    expect(body.forecast_3day).toHaveLength(1);
  });
});

// ── getCurrency ───────────────────────────────────────────────────────────────

describe("getCurrency", () => {
  it("returns 400 for a negative amount", async () => {
    const resp = await getCurrency(makeRequest("/v1/shadow/currency", { from: "USD", to: "EUR", amount: "-5" }), testEnv, user, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 400 for an invalid currency code", async () => {
    const resp = await getCurrency(makeRequest("/v1/shadow/currency", { from: "US", to: "EUR", amount: "100" }), testEnv, user, cors);
    expect(resp.status).toBe(400);
  });

  it("returns the converted amount on success", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { base: "USD", date: "2025-01-01", rates: { EUR: 93.0 } }));
    const resp = await getCurrency(makeRequest("/v1/shadow/currency", { from: "USD", to: "EUR", amount: "100" }), testEnv, user, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<{ from: string; to: string; result: number; formatted: string }>();
    expect(body.from).toBe("USD");
    expect(body.to).toBe("EUR");
    expect(body.result).toBe(93.0);
    expect(body.formatted).toContain("EUR");
  });

  it("defaults amount to 1 when not provided", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { base: "USD", date: "2025-01-01", rates: { EUR: 0.92 } }));
    const resp = await getCurrency(makeRequest("/v1/shadow/currency", { from: "USD", to: "EUR" }), testEnv, user, cors);
    expect(resp.status).toBe(200);
    expect((await resp.json<{ amount: number }>()).amount).toBe(1);
  });
});

// ── getCve ────────────────────────────────────────────────────────────────────

describe("getCve", () => {
  const emptyNvd = { totalResults: 0, vulnerabilities: [] };

  it("returns 400 when q is missing", async () => {
    const resp = await getCve(makeRequest("/v1/shadow/cve"), testEnv, user, cors);
    expect(resp.status).toBe(400);
  });

  it("looks up by cveId when q is a CVE ID", async () => {
    const fetchMock = mockFetch(200, emptyNvd);
    vi.stubGlobal("fetch", fetchMock);
    await getCve(makeRequest("/v1/shadow/cve", { q: "CVE-2024-12345" }), testEnv, user, cors);
    const url = calledUrl(fetchMock);
    expect(url.searchParams.get("cveId")).toBe("CVE-2024-12345");
    expect(url.searchParams.has("keywordSearch")).toBe(false);
  });

  it("searches by keyword when q is a plain term", async () => {
    const fetchMock = mockFetch(200, emptyNvd);
    vi.stubGlobal("fetch", fetchMock);
    await getCve(makeRequest("/v1/shadow/cve", { q: "apache log4j" }), testEnv, user, cors);
    const url = calledUrl(fetchMock);
    expect(url.searchParams.get("keywordSearch")).toBe("apache log4j");
    expect(url.searchParams.has("cveId")).toBe(false);
  });

  it("caps limit at 20", async () => {
    const fetchMock = mockFetch(200, emptyNvd);
    vi.stubGlobal("fetch", fetchMock);
    await getCve(makeRequest("/v1/shadow/cve", { q: "openssl", limit: "999" }), testEnv, user, cors);
    expect(calledUrl(fetchMock).searchParams.get("resultsPerPage")).toBe("20");
  });

  it("shapes results from the NVD response", async () => {
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
    const resp = await getCve(makeRequest("/v1/shadow/cve", { q: "CVE-2024-0001" }), testEnv, user, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<{
      total: number;
      results: { id: string; score: number; severity: string; published: string; nvd_url: string }[];
    }>();
    expect(body.total).toBe(1);
    expect(body.results[0].id).toBe("CVE-2024-0001");
    expect(body.results[0].score).toBe(9.8);
    expect(body.results[0].severity).toBe("CRITICAL");
    expect(body.results[0].published).toBe("2024-01-15");
    expect(body.results[0].nvd_url).toContain("CVE-2024-0001");
  });
});

// ── getIpReputation ───────────────────────────────────────────────────────────

describe("getIpReputation", () => {
  const abuseBody = (score: number) => ({
    data: {
      ipAddress: "203.0.113.7",
      isPublic: true,
      ipVersion: 4,
      isWhitelisted: false,
      abuseConfidenceScore: score,
      countryCode: "NL",
      usageType: "Data Center/Web Hosting/Transit",
      isp: "Example Hosting",
      domain: "example.net",
      isTor: false,
      totalReports: 12,
      numDistinctUsers: 4,
      lastReportedAt: "2026-10-30T12:00:00+00:00",
    },
  });

  it("returns 400 when addr is missing", async () => {
    const resp = await getIpReputation(makeRequest("/v1/shadow/ip"), testEnv, user, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 400 for a malformed address", async () => {
    const resp = await getIpReputation(makeRequest("/v1/shadow/ip", { addr: "not-an-ip" }), testEnv, user, cors);
    expect(resp.status).toBe(400);
    expect((await resp.json<ErrorBody>()).error).toBe("invalid ip address");
  });

  it("returns limited data without calling upstream when ABUSEIPDB_KEY is unset", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const resp = await getIpReputation(makeRequest("/v1/shadow/ip", { addr: "192.168.1.10" }), noKeyEnv, user, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<{ abuseipdb: null; is_private: boolean }>();
    expect(body.abuseipdb).toBeNull();
    expect(body.is_private).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends the AbuseIPDB key for the requested address", async () => {
    const fetchMock = mockFetch(200, abuseBody(0));
    vi.stubGlobal("fetch", fetchMock);
    await getIpReputation(makeRequest("/v1/shadow/ip", { addr: "203.0.113.7" }), testEnv, user, cors);
    expect(calledUrl(fetchMock).searchParams.get("ipAddress")).toBe("203.0.113.7");
    expect(fetchMock.mock.calls[0][1].headers.Key).toBe("test-abuseipdb-key");
  });

  it.each([
    { score: 75, level: "critical" },
    { score: 74, level: "high" },
    { score: 25, level: "high" },
    { score: 24, level: "low" },
    { score: 1, level: "low" },
    { score: 0, level: "clean" },
  ])("maps abuse score $score to risk level $level", async ({ score, level }) => {
    vi.stubGlobal("fetch", mockFetch(200, abuseBody(score)));
    const resp = await getIpReputation(makeRequest("/v1/shadow/ip", { addr: "203.0.113.7" }), testEnv, user, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<{ abuse_score: number; risk_level: string; is_private: boolean }>();
    expect(body.abuse_score).toBe(score);
    expect(body.risk_level).toBe(level);
    expect(body.is_private).toBe(false);
  });

  it("returns 502 when AbuseIPDB fails", async () => {
    vi.stubGlobal("fetch", mockFetch(429, {}));
    const resp = await getIpReputation(makeRequest("/v1/shadow/ip", { addr: "203.0.113.7" }), testEnv, user, cors);
    expect(resp.status).toBe(502);
  });
});

// ── checkBreach ───────────────────────────────────────────────────────────────

describe("checkBreach", () => {
  it("returns 400 when email is missing", async () => {
    const resp = await checkBreach(makeRequest("/v1/shadow/breach"), testEnv, user, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 400 when email has no @", async () => {
    const resp = await checkBreach(makeRequest("/v1/shadow/breach", { email: "notanemail" }), testEnv, user, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 503 when HIBP_KEY is not configured", async () => {
    const resp = await checkBreach(makeRequest("/v1/shadow/breach", { email: "test@example.com" }), noKeyEnv, user, cors);
    expect(resp.status).toBe(503);
  });

  it("returns not-breached when HIBP returns 404", async () => {
    vi.stubGlobal("fetch", mockFetch(404, null));
    const resp = await checkBreach(makeRequest("/v1/shadow/breach", { email: "clean@example.com" }), testEnv, user, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<{ breached: boolean; count: number }>();
    expect(body.breached).toBe(false);
    expect(body.count).toBe(0);
  });

  it("returns breach details on a hit", async () => {
    const breachData = [{
      Name: "AcmeService", Title: "Acme Service", Domain: "acme.com",
      BreachDate: "2023-06-01", PwnCount: 500000, DataClasses: ["Email addresses", "Passwords"],
      IsVerified: true, IsSensitive: false,
    }];
    vi.stubGlobal("fetch", mockFetch(200, breachData));
    const resp = await checkBreach(makeRequest("/v1/shadow/breach", { email: "victim@example.com" }), testEnv, user, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<{
      email: string;
      breached: boolean;
      count: number;
      breaches: { name: string; pwn_count: number }[];
    }>();
    expect(body.breached).toBe(true);
    expect(body.count).toBe(1);
    expect(body.breaches[0].name).toBe("AcmeService");
    expect(body.breaches[0].pwn_count).toBe(500000);
    expect(body.email).toBe("victim@example.com");
  });

  it("lowercases the email before lookup", async () => {
    const fetchMock = mockFetch(404, null);
    vi.stubGlobal("fetch", fetchMock);
    await checkBreach(makeRequest("/v1/shadow/breach", { email: "UPPER@Example.COM" }), testEnv, user, cors);
    expect(String(fetchMock.mock.calls[0][0])).toContain("upper%40example.com");
  });
});

// ── dnsLookup ─────────────────────────────────────────────────────────────────

describe("dnsLookup", () => {
  const dohBody = (status: number, answer: unknown[] = []) => ({
    Status: status, TC: false, RD: true, RA: true, AD: false, CD: false, Question: [], Answer: answer,
  });

  it("returns 400 when q is missing", async () => {
    const resp = await dnsLookup(makeRequest("/v1/shadow/dns"), testEnv, user, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 400 for an invalid record type", async () => {
    const resp = await dnsLookup(makeRequest("/v1/shadow/dns", { q: "example.com", type: "INVALID" }), testEnv, user, cors);
    expect(resp.status).toBe(400);
    expect((await resp.json<ErrorBody>()).error).toContain("invalid type");
  });

  it("defaults to an A record lookup", async () => {
    const fetchMock = mockFetch(200, dohBody(0));
    vi.stubGlobal("fetch", fetchMock);
    await dnsLookup(makeRequest("/v1/shadow/dns", { q: "example.com" }), testEnv, user, cors);
    expect(calledUrl(fetchMock).searchParams.get("type")).toBe("A");
  });

  it("accepts every supported record type", async () => {
    vi.stubGlobal("fetch", mockFetch(200, dohBody(0)));
    for (const type of ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA", "PTR", "SRV"]) {
      const resp = await dnsLookup(makeRequest("/v1/shadow/dns", { q: "example.com", type }), testEnv, user, cors);
      expect(resp.status).toBe(200);
    }
  });

  it("maps RCODE 0 to NOERROR and returns records", async () => {
    vi.stubGlobal("fetch", mockFetch(200, dohBody(0, [{ name: "example.com.", type: 1, TTL: 300, data: "93.184.216.34" }])));
    const resp = await dnsLookup(makeRequest("/v1/shadow/dns", { q: "example.com", type: "A" }), testEnv, user, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<{ status: string; records: { value: string }[] }>();
    expect(body.status).toBe("NOERROR");
    expect(body.records).toHaveLength(1);
    expect(body.records[0].value).toBe("93.184.216.34");
  });

  it("maps RCODE 3 to NXDOMAIN", async () => {
    vi.stubGlobal("fetch", mockFetch(200, dohBody(3)));
    const resp = await dnsLookup(makeRequest("/v1/shadow/dns", { q: "noexist.invalid", type: "A" }), testEnv, user, cors);
    expect(resp.status).toBe(200);
    expect((await resp.json<{ status: string }>()).status).toBe("NXDOMAIN");
  });
});

// ── webSearch ─────────────────────────────────────────────────────────────────

describe("webSearch", () => {
  const braveEnv = { BRAVE_SEARCH_KEY: "test-brave-key" } as unknown as Env;
  type SearchBody = { query: string; results: { title: string; url: string; snippet: string }[]; note?: string };

  it("returns 400 when q is missing", async () => {
    const resp = await webSearch(makeRequest("/v1/shadow/search"), braveEnv, user, cors);
    expect(resp.status).toBe(400);
  });

  it("uses Brave Search when BRAVE_SEARCH_KEY is set, capping limit at 10", async () => {
    const fetchMock = mockFetch(200, {
      web: { results: [{ title: "Tor Project", url: "https://www.torproject.org", description: "Browse privately." }] },
    });
    vi.stubGlobal("fetch", fetchMock);
    const resp = await webSearch(makeRequest("/v1/shadow/search", { q: "tor", limit: "50" }), braveEnv, user, cors);
    expect(resp.status).toBe(200);
    const url = calledUrl(fetchMock);
    expect(url.hostname).toBe("api.search.brave.com");
    expect(url.searchParams.get("count")).toBe("10");
    expect(fetchMock.mock.calls[0][1].headers["X-Subscription-Token"]).toBe("test-brave-key");
    const body = await resp.json<SearchBody>();
    expect(body.query).toBe("tor");
    expect(body.results).toEqual([{ title: "Tor Project", url: "https://www.torproject.org", snippet: "Browse privately." }]);
  });

  it("falls back to DuckDuckGo without a Brave key", async () => {
    const fetchMock = mockFetch(200, {
      AbstractText: "Tor is free software for anonymous communication.",
      AbstractURL: "https://en.wikipedia.org/wiki/Tor_(network)",
      AbstractSource: "Wikipedia",
      RelatedTopics: [
        { Text: "Onion routing - A technique for anonymous communication", FirstURL: "https://duckduckgo.com/Onion_routing" },
        { Text: "Topic without a URL" },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);
    const resp = await webSearch(makeRequest("/v1/shadow/search", { q: "tor" }), noKeyEnv, user, cors);
    expect(resp.status).toBe(200);
    expect(calledUrl(fetchMock).hostname).toBe("api.duckduckgo.com");
    const body = await resp.json<SearchBody>();
    expect(body.results.map(r => r.title)).toEqual(["Wikipedia", "Onion routing"]);
    expect(body.note).toBeUndefined();
  });

  it("points to BRAVE_SEARCH_KEY when DuckDuckGo has no answer", async () => {
    vi.stubGlobal("fetch", mockFetch(200, {}));
    const resp = await webSearch(makeRequest("/v1/shadow/search", { q: "zzqx" }), noKeyEnv, user, cors);
    const body = await resp.json<SearchBody>();
    expect(body.results).toEqual([]);
    expect(body.note).toContain("BRAVE_SEARCH_KEY");
  });

  it("returns 502 when Brave Search fails", async () => {
    vi.stubGlobal("fetch", mockFetch(500, {}));
    const resp = await webSearch(makeRequest("/v1/shadow/search", { q: "tor" }), braveEnv, user, cors);
    expect(resp.status).toBe(502);
  });
});

// ── wikiSummary ───────────────────────────────────────────────────────────────

describe("wikiSummary", () => {
  it("returns 400 when q is missing", async () => {
    const resp = await wikiSummary(makeRequest("/v1/shadow/wiki"), testEnv, cors);
    expect(resp.status).toBe(400);
  });

  it("returns 502 when the search request fails", async () => {
    vi.stubGlobal("fetch", mockFetch(500, {}));
    const resp = await wikiSummary(makeRequest("/v1/shadow/wiki", { q: "Linux" }), testEnv, cors);
    expect(resp.status).toBe(502);
  });

  it("returns found: false when no article matches", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { query: { search: [] } }));
    const resp = await wikiSummary(makeRequest("/v1/shadow/wiki", { q: "zzqx" }), testEnv, cors);
    expect(resp.status).toBe(200);
    expect(await resp.json<{ found: boolean; query: string }>()).toEqual({ found: false, query: "zzqx" });
  });

  it("returns the summary of the best-matching article", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(fakeResponse(200, { query: { search: [{ title: "Linux" }] } }))
      .mockResolvedValueOnce(fakeResponse(200, {
        title: "Linux",
        extract: "Linux is a family of open-source Unix-like operating systems.",
        content_urls: { desktop: { page: "https://en.wikipedia.org/wiki/Linux" } },
      })));
    const resp = await wikiSummary(makeRequest("/v1/shadow/wiki", { q: "linux kernel" }), testEnv, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<{ found: boolean; title: string; extract: string; url: string; thumbnail: string | null }>();
    expect(body.found).toBe(true);
    expect(body.title).toBe("Linux");
    expect(body.extract).toContain("Unix-like");
    expect(body.url).toBe("https://en.wikipedia.org/wiki/Linux");
    expect(body.thumbnail).toBeNull();
  });
});

// ── ddgInstant ────────────────────────────────────────────────────────────────

describe("ddgInstant", () => {
  type InstantBody = {
    answer: string | null;
    abstract: string | null;
    definition: string | null;
    related: { text: string; url: string }[];
    has_result: boolean;
  };

  it("returns 400 when q is missing", async () => {
    const resp = await ddgInstant(makeRequest("/v1/shadow/instant"), testEnv, cors);
    expect(resp.status).toBe(400);
  });

  it("returns the answer, abstract, and linked related topics", async () => {
    vi.stubGlobal("fetch", mockFetch(200, {
      Answer: " 42 ",
      AbstractText: "An abstract.",
      AbstractSource: "Wikipedia",
      AbstractURL: "https://en.wikipedia.org/wiki/42_(number)",
      RelatedTopics: [
        { Text: "Topic one", FirstURL: "https://duckduckgo.com/Topic_one" },
        { Text: "Topic without a URL" },
      ],
    }));
    const resp = await ddgInstant(makeRequest("/v1/shadow/instant", { q: "answer" }), testEnv, cors);
    expect(resp.status).toBe(200);
    const body = await resp.json<InstantBody>();
    expect(body.answer).toBe("42");
    expect(body.abstract).toBe("An abstract.");
    expect(body.definition).toBeNull();
    expect(body.related).toEqual([{ text: "Topic one", url: "https://duckduckgo.com/Topic_one" }]);
    expect(body.has_result).toBe(true);
  });

  it("reports has_result: false when DuckDuckGo returns nothing", async () => {
    vi.stubGlobal("fetch", mockFetch(200, {}));
    const resp = await ddgInstant(makeRequest("/v1/shadow/instant", { q: "zzqx" }), testEnv, cors);
    expect((await resp.json<InstantBody>()).has_result).toBe(false);
  });

  it("returns 502 when DuckDuckGo fails", async () => {
    vi.stubGlobal("fetch", mockFetch(503, {}));
    const resp = await ddgInstant(makeRequest("/v1/shadow/instant", { q: "x" }), testEnv, cors);
    expect(resp.status).toBe(502);
  });
});
