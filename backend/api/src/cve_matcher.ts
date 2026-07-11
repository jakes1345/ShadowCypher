/**
 * CVE Alert Matching — hourly cron handler.
 *
 * Fetches CVEs published in the last 2 hours from NVD, matches them against
 * each user's devices via port→service keyword map, and fires webhooks for
 * new matches. Uses cve_alerts_sent table to deduplicate.
 *
 * Scheduled: 0 * * * * (every hour, top of hour)
 */

import type { Env } from "./index";
import { dbSelect, dbInsert } from "./supabase";
import { dispatchCveWebhook, type CveMatchPayload } from "./webhooks";

// Port → service keywords for matching CVE descriptions
const PORT_KEYWORDS: Record<number, string[]> = {
  21:    ["ftp", "vsftpd", "proftpd", "filezilla"],
  22:    ["ssh", "openssh", "sshd"],
  23:    ["telnet"],
  25:    ["smtp", "postfix", "exim", "sendmail", "mail server"],
  53:    ["dns", "bind", "named", "resolver"],
  80:    ["apache", "nginx", "http", "web server", "iis"],
  110:   ["pop3", "mail"],
  139:   ["smb", "samba", "netbios"],
  143:   ["imap", "mail"],
  443:   ["apache", "nginx", "https", "tls", "ssl", "openssl", "web server"],
  445:   ["smb", "samba", "windows file sharing"],
  3306:  ["mysql", "mariadb"],
  3389:  ["rdp", "remote desktop", "terminal services", "windows"],
  5432:  ["postgres", "postgresql"],
  5900:  ["vnc", "remote desktop"],
  6379:  ["redis"],
  8080:  ["tomcat", "jetty", "http", "web server"],
  8443:  ["tomcat", "jetty", "https"],
  27017: ["mongodb", "mongo"],
};

function osKeywords(os: string | null): string[] {
  if (!os) return [];
  const lower = os.toLowerCase();
  const kws: string[] = [];
  if (lower.includes("windows"))                       kws.push("windows", "microsoft", "win32", "win64");
  if (lower.includes("linux"))                         kws.push("linux", "kernel");
  if (lower.includes("ubuntu"))                        kws.push("ubuntu", "linux");
  if (lower.includes("debian"))                        kws.push("debian", "linux");
  if (lower.includes("android"))                       kws.push("android");
  if (lower.includes("ios"))                           kws.push("ios", "apple");
  if (lower.includes("macos") || lower.includes("osx")) kws.push("macos", "apple", "osx");
  if (lower.includes("router") || lower.includes("ubiquiti")) kws.push("ubiquiti", "router", "unifi");
  if (lower.includes("cisco"))                         kws.push("cisco", "router");
  if (lower.includes("openwrt"))                       kws.push("openwrt", "router", "linux");
  return kws;
}

interface DeviceRow {
  id: string;
  user_id: string;
  hostname: string | null;
  ip: string;
  open_ports: number[];
  os_fingerprint: string | null;
}

interface NvdCve {
  id: string;
  description: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
  cvss: number | null;
  url: string;
}

function twoHoursAgoIso(): string {
  return new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString().replace(/\.\d{3}Z$/, ".000Z");
}

async function fetchRecentCves(env: Env): Promise<NvdCve[]> {
  const pubStartDate = twoHoursAgoIso();
  // NVD cvssV3Severity is exact-match — "HIGH" does NOT include "CRITICAL".
  // Fetch both severities and merge deduplicated results.
  const severities = ["CRITICAL", "HIGH"] as const;
  const allCves = new Map<string, NvdCve>();

  await Promise.all(severities.map(async (severity) => {
    const qs = new URLSearchParams({ pubStartDate, cvssV3Severity: severity }).toString();
    const url = `https://services.nvd.nist.gov/rest/json/cves/2.0?${qs}`;

    let resp: Response;
    try {
      resp = await fetch(url, {
        headers: { "User-Agent": "ShadowCypher/1.0 (security dashboard; contact: hello@shadowcypher.site)" },
        cf: { cacheTtl: 3600, cacheEverything: true } as RequestInitCfProperties,
      });
    } catch {
      return;
    }

    if (!resp.ok) return;

    const data = (await resp.json()) as {
      vulnerabilities?: Array<{
        cve: {
          id: string;
          descriptions: Array<{ lang: string; value: string }>;
          metrics?: {
            cvssMetricV31?: Array<{ cvssData: { baseScore: number } }>;
            cvssMetricV30?: Array<{ cvssData: { baseScore: number } }>;
            cvssMetricV2?: Array<{ cvssData: { baseScore: number } }>;
          };
        };
      }>;
    };

    for (const v of data.vulnerabilities || []) {
      if (allCves.has(v.cve.id)) continue; // deduplicate
      const cve = v.cve;
      const desc = cve.descriptions.find((d) => d.lang === "en")?.value || "";
      const score =
        cve.metrics?.cvssMetricV31?.[0]?.cvssData.baseScore ??
        cve.metrics?.cvssMetricV30?.[0]?.cvssData.baseScore ??
        cve.metrics?.cvssMetricV2?.[0]?.cvssData.baseScore ??
        null;
      const sev: NvdCve["severity"] =
        score === null ? "NONE" :
        score >= 9.0   ? "CRITICAL" :
        score >= 7.0   ? "HIGH" :
        score >= 4.0   ? "MEDIUM" : "LOW";
      allCves.set(cve.id, {
        id: cve.id,
        description: desc.length > 300 ? desc.slice(0, 297) + "..." : desc,
        severity: sev,
        cvss: score,
        url: `https://nvd.nist.gov/vuln/detail/${cve.id}`,
      });
    }
  }));

  return [...allCves.values()];
}

function matchCveToDevice(cve: NvdCve, device: DeviceRow): string[] | null {
  const descLower = cve.description.toLowerCase();
  const keywords = new Set<string>();

  for (const port of (device.open_ports || [])) {
    for (const kw of (PORT_KEYWORDS[port] || [])) {
      keywords.add(kw);
    }
  }
  for (const kw of osKeywords(device.os_fingerprint)) {
    keywords.add(kw);
  }

  const matched = [...keywords].filter((kw) => descLower.includes(kw));
  return matched.length > 0 ? matched : null;
}

async function alreadySent(env: Env, userId: string, deviceId: string, cveId: string): Promise<boolean> {
  const rows = await dbSelect(env, "cve_alerts_sent", {
    select: "id",
    filters: {
      user_id: `eq.${userId}`,
      device_id: `eq.${deviceId}`,
      cve_id: `eq.${cveId}`,
    },
    limit: 1,
  });
  return rows.length > 0;
}

async function markSent(env: Env, userId: string, deviceId: string, cveId: string): Promise<void> {
  await dbInsert(env, "cve_alerts_sent", { user_id: userId, device_id: deviceId, cve_id: cveId });
}

export async function runCveMatchingCron(env: Env): Promise<void> {
  const cves = await fetchRecentCves(env);
  if (cves.length === 0) return;

  const devices = await dbSelect<DeviceRow>(env, "devices", {
    select: "id,user_id,hostname,ip,open_ports,os_fingerprint",
    limit: 10000,
  });
  if (devices.length === 0) return;

  const byUser = new Map<string, DeviceRow[]>();
  for (const d of devices) {
    if (!byUser.has(d.user_id)) byUser.set(d.user_id, []);
    byUser.get(d.user_id)!.push(d);
  }

  for (const [userId, userDevices] of byUser) {
    for (const device of userDevices) {
      for (const cve of cves) {
        const matched = matchCveToDevice(cve, device);
        if (!matched) continue;

        const sent = await alreadySent(env, userId, device.id, cve.id);
        if (sent) continue;

        const payload: CveMatchPayload = {
          cve_id: cve.id,
          severity: cve.severity,
          cvss: cve.cvss,
          description: cve.description,
          cve_url: cve.url,
          device_id: device.id,
          device_name: device.hostname || device.ip,
          device_ip: device.ip,
          matched_on: matched,
        };

        await dispatchCveWebhook(env, userId, payload);
        await markSent(env, userId, device.id, cve.id);
      }
    }
  }
}
