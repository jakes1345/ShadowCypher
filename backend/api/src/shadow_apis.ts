/**
 * Shadow structured API routes — no LLM needed for these queries.
 *
 * GET /v1/shadow/weather?q=<city>                     Open-Meteo (free, no key)
 * GET /v1/shadow/currency?from=USD&to=EUR&amount=100  Frankfurter (free, no key)
 * GET /v1/shadow/cve?q=<keyword>&limit=5              NVD API 2.0 (free)
 * GET /v1/shadow/ip?addr=<ip>                         AbuseIPDB (ABUSEIPDB_KEY env)
 * GET /v1/shadow/breach?email=<email>                 HaveIBeenPwned k-anon (HIBP_KEY env)
 * GET /v1/shadow/dns?q=<domain>&type=A                Cloudflare DoH
 */

import type { Env } from "./index";

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers ?? {}) },
  });

// ── Weather ──────────────────────────────────────────────────────────────────

export async function getWeather(
  req: Request,
  env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const q = (url.searchParams.get("q") ?? "").trim();
  if (!q) return json({ error: "q is required" }, { status: 400 }, cors);

  try {
    // Step 1: Geocode city → lat/lon via Open-Meteo geocoding
    const geoResp = await fetch(
      `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(q)}&count=1&language=en&format=json`,
      { headers: { "User-Agent": "ShadowCypher/1.0" } }
    );
    if (!geoResp.ok) return json({ error: "geocoding_failed" }, { status: 502 }, cors);
    const geo = (await geoResp.json()) as { results?: { name: string; country: string; latitude: number; longitude: number; timezone: string; }[] };

    const loc = geo.results?.[0];
    if (!loc) return json({ error: "city_not_found", query: q }, { status: 404 }, cors);

    // Step 2: Fetch current weather + forecast
    const wxResp = await fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${loc.latitude}&longitude=${loc.longitude}` +
      `&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code` +
      `&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum` +
      `&timezone=${encodeURIComponent(loc.timezone)}&forecast_days=3`,
      { headers: { "User-Agent": "ShadowCypher/1.0" } }
    );
    if (!wxResp.ok) return json({ error: "weather_fetch_failed" }, { status: 502 }, cors);
    const wx = (await wxResp.json()) as {
      current: {
        temperature_2m: number;
        relative_humidity_2m: number;
        apparent_temperature: number;
        precipitation: number;
        wind_speed_10m: number;
        weather_code: number;
      };
      daily: {
        time: string[];
        weather_code: number[];
        temperature_2m_max: number[];
        temperature_2m_min: number[];
        precipitation_sum: number[];
      };
    };

    const wmoDescription = wmoCode(wx.current.weather_code);

    return json({
      location: { name: loc.name, country: loc.country, lat: loc.latitude, lon: loc.longitude },
      current: {
        temp_c: wx.current.temperature_2m,
        temp_f: Math.round(wx.current.temperature_2m * 9 / 5 + 32),
        feels_like_c: wx.current.apparent_temperature,
        humidity_pct: wx.current.relative_humidity_2m,
        precipitation_mm: wx.current.precipitation,
        wind_kph: wx.current.wind_speed_10m,
        condition: wmoDescription,
        code: wx.current.weather_code,
      },
      forecast_3day: wx.daily.time.map((date, i) => ({
        date,
        condition: wmoCode(wx.daily.weather_code[i]),
        max_c: wx.daily.temperature_2m_max[i],
        min_c: wx.daily.temperature_2m_min[i],
        precipitation_mm: wx.daily.precipitation_sum[i],
      })),
    }, {}, cors);
  } catch (e) {
    return json({ error: "upstream_error", detail: String(e) }, { status: 502 }, cors);
  }
}

function wmoCode(code: number): string {
  const map: Record<number, string> = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icing fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
  };
  return map[code] ?? `Code ${code}`;
}

// ── Currency ─────────────────────────────────────────────────────────────────

export async function getCurrency(
  req: Request,
  env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const from = (url.searchParams.get("from") ?? "USD").toUpperCase().slice(0, 3);
  const to = (url.searchParams.get("to") ?? "EUR").toUpperCase().slice(0, 3);
  const amount = parseFloat(url.searchParams.get("amount") ?? "1");

  if (isNaN(amount) || amount <= 0) return json({ error: "invalid amount" }, { status: 400 }, cors);
  if (!/^[A-Z]{3}$/.test(from) || !/^[A-Z]{3}$/.test(to))
    return json({ error: "invalid currency code" }, { status: 400 }, cors);

  try {
    const resp = await fetch(
      `https://api.frankfurter.app/latest?amount=${amount}&from=${from}&to=${to}`,
      { headers: { "User-Agent": "ShadowCypher/1.0" } }
    );
    if (!resp.ok) {
      const txt = await resp.text();
      return json({ error: "conversion_failed", detail: txt }, { status: 502 }, cors);
    }
    const data = (await resp.json()) as { base: string; date: string; rates: Record<string, number> };
    const rate = data.rates[to];
    return json({
      from, to, amount, result: rate,
      rate: rate / amount,
      date: data.date,
      formatted: `${amount} ${from} = ${rate?.toFixed(4)} ${to}`,
    }, {}, cors);
  } catch (e) {
    return json({ error: "upstream_error", detail: String(e) }, { status: 502 }, cors);
  }
}

// ── CVE Lookup ────────────────────────────────────────────────────────────────

export async function getCve(
  req: Request,
  env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const q = (url.searchParams.get("q") ?? "").trim();
  const limit = Math.min(parseInt(url.searchParams.get("limit") ?? "5"), 20);

  if (!q) return json({ error: "q is required" }, { status: 400 }, cors);

  try {
    // NVD API 2.0 — free, no key for basic usage (rate limit: 5 req/30s unauthenticated)
    let nvdUrl = `https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=${limit}`;

    // If q looks like a CVE ID, use cveId parameter
    if (/^CVE-\d{4}-\d+$/i.test(q)) {
      nvdUrl += `&cveId=${q.toUpperCase()}`;
    } else {
      // Keyword search
      nvdUrl += `&keywordSearch=${encodeURIComponent(q)}`;
    }

    const headers: Record<string, string> = { "User-Agent": "ShadowCypher/1.0" };
    // Add NVD API key if configured for higher rate limits (50 req/30s)
    const nvdKey = env.NVD_API_KEY;
    if (nvdKey) headers["apiKey"] = nvdKey;

    const resp = await fetch(nvdUrl, { headers });
    if (!resp.ok) {
      return json({ error: "nvd_error", status: resp.status }, { status: 502 }, cors);
    }
    const data = (await resp.json()) as {
      totalResults: number;
      vulnerabilities: {
        cve: {
          id: string;
          published: string;
          lastModified: string;
          descriptions: { lang: string; value: string }[];
          metrics?: {
            cvssMetricV31?: { cvssData: { baseScore: number; baseSeverity: string; vectorString: string } }[];
            cvssMetricV30?: { cvssData: { baseScore: number; baseSeverity: string } }[];
            cvssMetricV2?: { cvssData: { baseScore: number } }[];
          };
          references?: { url: string; tags?: string[] }[];
        };
      }[];
    };

    const results = (data.vulnerabilities ?? []).map(({ cve }) => {
      const desc = cve.descriptions.find(d => d.lang === "en")?.value ?? "";
      const cvss31 = cve.metrics?.cvssMetricV31?.[0]?.cvssData;
      const cvss30 = cve.metrics?.cvssMetricV30?.[0]?.cvssData;
      const cvssScore = cvss31?.baseScore ?? cvss30?.baseScore ?? null;
      const severity = cvss31?.baseSeverity ?? cvss30?.baseSeverity ?? null;
      return {
        id: cve.id,
        published: cve.published.split("T")[0],
        score: cvssScore,
        severity,
        description: desc.slice(0, 300) + (desc.length > 300 ? "…" : ""),
        nvd_url: `https://nvd.nist.gov/vuln/detail/${cve.id}`,
      };
    });

    return json({ total: data.totalResults, results }, {}, cors);
  } catch (e) {
    return json({ error: "upstream_error", detail: String(e) }, { status: 502 }, cors);
  }
}

// ── IP Reputation ─────────────────────────────────────────────────────────────

export async function getIpReputation(
  req: Request,
  env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const addr = (url.searchParams.get("addr") ?? "").trim();
  if (!addr) return json({ error: "addr is required" }, { status: 400 }, cors);

  // Basic IP format validation
  const ipv4 = /^(\d{1,3}\.){3}\d{1,3}$/;
  const ipv6 = /^[0-9a-f:]+$/i;
  if (!ipv4.test(addr) && !ipv6.test(addr))
    return json({ error: "invalid ip address" }, { status: 400 }, cors);

  const abuseKey = env.ABUSEIPDB_KEY;
  if (!abuseKey) {
    // Fallback: return basic info from public sources
    return json({
      ip: addr,
      abuseipdb: null,
      note: "ABUSEIPDB_KEY not configured; limited data available",
      is_private: isPrivateIp(addr),
    }, {}, cors);
  }

  try {
    const resp = await fetch(
      `https://api.abuseipdb.com/api/v2/check?ipAddress=${encodeURIComponent(addr)}&maxAgeInDays=90&verbose`,
      {
        headers: {
          "Key": abuseKey,
          "Accept": "application/json",
          "User-Agent": "ShadowCypher/1.0",
        },
      }
    );
    if (!resp.ok) return json({ error: "abuseipdb_error", status: resp.status }, { status: 502 }, cors);

    const result = (await resp.json()) as {
      data: {
        ipAddress: string;
        isPublic: boolean;
        ipVersion: number;
        isWhitelisted: boolean;
        abuseConfidenceScore: number;
        countryCode: string;
        usageType: string;
        isp: string;
        domain: string;
        isTor: boolean;
        totalReports: number;
        numDistinctUsers: number;
        lastReportedAt: string | null;
        reports?: { reportedAt: string; comment: string; categories: number[] }[];
      };
    };

    const d = result.data;
    return json({
      ip: d.ipAddress,
      abuse_score: d.abuseConfidenceScore,
      risk_level: d.abuseConfidenceScore >= 75 ? "critical" : d.abuseConfidenceScore >= 25 ? "high" : d.abuseConfidenceScore > 0 ? "low" : "clean",
      is_tor: d.isTor,
      is_whitelisted: d.isWhitelisted,
      country: d.countryCode,
      isp: d.isp,
      domain: d.domain,
      usage_type: d.usageType,
      total_reports: d.totalReports,
      distinct_reporters: d.numDistinctUsers,
      last_reported: d.lastReportedAt,
      is_private: isPrivateIp(addr),
    }, {}, cors);
  } catch (e) {
    return json({ error: "upstream_error", detail: String(e) }, { status: 502 }, cors);
  }
}

function isPrivateIp(ip: string): boolean {
  const parts = ip.split(".").map(Number);
  if (parts.length !== 4) return false;
  return (
    parts[0] === 10 ||
    (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) ||
    (parts[0] === 192 && parts[1] === 168) ||
    parts[0] === 127 ||
    ip === "::1"
  );
}

// ── HaveIBeenPwned ────────────────────────────────────────────────────────────

export async function checkBreach(
  req: Request,
  env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const email = (url.searchParams.get("email") ?? "").trim().toLowerCase();
  if (!email || !email.includes("@"))
    return json({ error: "valid email required" }, { status: 400 }, cors);

  const hibpKey = env.HIBP_KEY;
  if (!hibpKey) {
    return json({ error: "HIBP_KEY not configured" }, { status: 503 }, cors);
  }

  try {
    const resp = await fetch(
      `https://haveibeenpwned.com/api/v3/breachedaccount/${encodeURIComponent(email)}?truncateResponse=false`,
      {
        headers: {
          "hibp-api-key": hibpKey,
          "User-Agent": "ShadowCypher/1.0",
        },
      }
    );

    if (resp.status === 404) {
      return json({ email, breached: false, count: 0, breaches: [] }, {}, cors);
    }
    if (!resp.ok) return json({ error: "hibp_error", status: resp.status }, { status: 502 }, cors);

    const breaches = (await resp.json()) as {
      Name: string;
      Title: string;
      Domain: string;
      BreachDate: string;
      PwnCount: number;
      DataClasses: string[];
      IsVerified: boolean;
      IsSensitive: boolean;
    }[];

    return json({
      email,
      breached: true,
      count: breaches.length,
      breaches: breaches.map(b => ({
        name: b.Name,
        title: b.Title,
        domain: b.Domain,
        date: b.BreachDate,
        pwn_count: b.PwnCount,
        data_classes: b.DataClasses,
        verified: b.IsVerified,
        sensitive: b.IsSensitive,
      })),
    }, {}, cors);
  } catch (e) {
    return json({ error: "upstream_error", detail: String(e) }, { status: 502 }, cors);
  }
}

// ── DNS Lookup ────────────────────────────────────────────────────────────────

export async function dnsLookup(
  req: Request,
  env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const q = (url.searchParams.get("q") ?? "").trim();
  const type = (url.searchParams.get("type") ?? "A").toUpperCase();

  if (!q) return json({ error: "q is required" }, { status: 400 }, cors);

  const validTypes = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA", "PTR", "SRV"];
  if (!validTypes.includes(type))
    return json({ error: `invalid type; use one of: ${validTypes.join(", ")}` }, { status: 400 }, cors);

  try {
    // Use Cloudflare's DoH endpoint (JSON API)
    const resp = await fetch(
      `https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(q)}&type=${type}`,
      { headers: { "Accept": "application/dns-json", "User-Agent": "ShadowCypher/1.0" } }
    );
    if (!resp.ok) return json({ error: "dns_lookup_failed" }, { status: 502 }, cors);

    const data = (await resp.json()) as {
      Status: number;
      TC: boolean;
      RD: boolean;
      RA: boolean;
      AD: boolean;
      CD: boolean;
      Question: { name: string; type: number }[];
      Answer?: { name: string; type: number; TTL: number; data: string }[];
      Authority?: { name: string; type: number; TTL: number; data: string }[];
    };

    const rcodeMap: Record<number, string> = {
      0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN",
      4: "NOTIMP", 5: "REFUSED",
    };

    return json({
      query: q,
      type,
      status: rcodeMap[data.Status] ?? `RCODE${data.Status}`,
      records: (data.Answer ?? []).map(r => ({
        name: r.name, type: dnsTypeName(r.type), ttl: r.TTL, value: r.data,
      })),
      authority: (data.Authority ?? []).map(r => ({
        name: r.name, type: dnsTypeName(r.type), ttl: r.TTL, value: r.data,
      })),
    }, {}, cors);
  } catch (e) {
    return json({ error: "upstream_error", detail: String(e) }, { status: 502 }, cors);
  }
}

// ── Web Search ───────────────────────────────────────────────────────────────

export async function webSearch(
  req: Request,
  env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const q = (url.searchParams.get("q") ?? "").trim();
  const limit = Math.min(parseInt(url.searchParams.get("limit") ?? "5", 10), 10);
  if (!q) return json({ error: "q is required" }, { status: 400 }, cors);

  const braveKey = env.BRAVE_SEARCH_KEY;

  if (braveKey) {
    // Brave Search API (free tier: 2000 req/month)
    try {
      const resp = await fetch(
        `https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(q)}&count=${limit}&text_decorations=false&result_filter=web`,
        { headers: { "Accept": "application/json", "X-Subscription-Token": braveKey, "User-Agent": "ShadowCypher/1.0" } }
      );
      if (!resp.ok) return json({ error: "search_failed", status: resp.status }, { status: 502 }, cors);
      const data = await resp.json() as { web?: { results?: { title: string; url: string; description: string }[] } };
      const results = (data.web?.results ?? []).slice(0, limit).map(r => ({
        title: r.title,
        url: r.url,
        snippet: r.description,
      }));
      return json({ query: q, results }, {}, cors);
    } catch (e) {
      return json({ error: "search_error", detail: String(e) }, { status: 502 }, cors);
    }
  }

  // Fallback: DuckDuckGo instant answer API (no key, limited to instant answers)
  try {
    const resp = await fetch(
      `https://api.duckduckgo.com/?q=${encodeURIComponent(q)}&format=json&no_html=1&skip_disambig=1`,
      { headers: { "User-Agent": "ShadowCypher/1.0" } }
    );
    if (!resp.ok) return json({ error: "search_failed" }, { status: 502 }, cors);
    const data = await resp.json() as {
      AbstractText?: string;
      AbstractURL?: string;
      AbstractSource?: string;
      RelatedTopics?: { Text?: string; FirstURL?: string }[];
    };

    const results: { title: string; url: string; snippet: string }[] = [];
    if (data.AbstractText) {
      results.push({ title: data.AbstractSource ?? q, url: data.AbstractURL ?? "", snippet: data.AbstractText });
    }
    for (const t of (data.RelatedTopics ?? []).slice(0, limit - results.length)) {
      if (t.Text && t.FirstURL) results.push({ title: t.Text.split(" - ")[0], url: t.FirstURL, snippet: t.Text });
    }

    return json({
      query: q,
      results,
      note: results.length === 0 ? "No instant answer found. Set BRAVE_SEARCH_KEY for full web search." : undefined,
    }, {}, cors);
  } catch (e) {
    return json({ error: "search_error", detail: String(e) }, { status: 502 }, cors);
  }
}

function dnsTypeName(type: number): string {
  const map: Record<number, string> = {
    1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR",
    15: "MX", 16: "TXT", 28: "AAAA", 33: "SRV", 257: "CAA",
  };
  return map[type] ?? `TYPE${type}`;
}
