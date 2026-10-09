import { describe, it, expect } from "vitest";
import { osKeywords, matchCveToDevice, type NvdCve, type DeviceRow } from "../cve_matcher";

// ── osKeywords ────────────────────────────────────────────────────────────────

describe("osKeywords", () => {
  it("returns empty array for null", () => {
    expect(osKeywords(null)).toEqual([]);
  });

  it("returns empty array for empty string", () => {
    expect(osKeywords("")).toEqual([]);
  });

  it("returns windows keywords for 'Windows 11'", () => {
    const kws = osKeywords("Windows 11");
    expect(kws).toContain("windows");
    expect(kws).toContain("microsoft");
  });

  it("returns linux keywords for 'Linux'", () => {
    const kws = osKeywords("Linux");
    expect(kws).toContain("linux");
    expect(kws).toContain("kernel");
  });

  it("returns ubuntu and linux keywords for 'Ubuntu 22.04'", () => {
    const kws = osKeywords("Ubuntu 22.04");
    expect(kws).toContain("ubuntu");
    expect(kws).toContain("linux");
  });

  it("returns debian and linux keywords for 'Debian 12'", () => {
    const kws = osKeywords("Debian 12");
    expect(kws).toContain("debian");
    expect(kws).toContain("linux");
  });

  it("returns android keyword for 'Android 14'", () => {
    const kws = osKeywords("Android 14");
    expect(kws).toContain("android");
  });

  it("returns ios and apple keywords for 'iOS 17'", () => {
    const kws = osKeywords("iOS 17");
    expect(kws).toContain("ios");
    expect(kws).toContain("apple");
  });

  it("returns macos and apple keywords for 'macOS Sonoma'", () => {
    const kws = osKeywords("macOS Sonoma");
    expect(kws).toContain("macos");
    expect(kws).toContain("apple");
  });

  it("returns macos keywords for 'OSX'", () => {
    const kws = osKeywords("OSX");
    expect(kws).toContain("macos");
    expect(kws).toContain("osx");
  });

  it("returns router keywords for 'Ubiquiti UniFi'", () => {
    const kws = osKeywords("Ubiquiti UniFi");
    expect(kws).toContain("ubiquiti");
    expect(kws).toContain("router");
  });

  it("returns cisco and router keywords for 'Cisco IOS'", () => {
    const kws = osKeywords("Cisco IOS");
    expect(kws).toContain("cisco");
    expect(kws).toContain("router");
  });

  it("returns openwrt and router and linux keywords for 'OpenWrt'", () => {
    const kws = osKeywords("OpenWrt");
    expect(kws).toContain("openwrt");
    expect(kws).toContain("router");
    expect(kws).toContain("linux");
  });

  it("is case-insensitive", () => {
    expect(osKeywords("WINDOWS")).toContain("windows");
    expect(osKeywords("linux")).toContain("linux");
    expect(osKeywords("MACOS")).toContain("macos");
  });

  it("returns combined keywords for a device matching multiple categories", () => {
    // 'router' and 'linux' (OpenWrt is both)
    const kws = osKeywords("OpenWrt Linux router");
    expect(kws).toContain("linux");
    expect(kws).toContain("router");
    expect(kws).toContain("openwrt");
  });
});

// ── matchCveToDevice ──────────────────────────────────────────────────────────

function makeCve(description: string, id = "CVE-2024-0001"): NvdCve {
  return { id, description, severity: "HIGH", cvss: 7.5, url: `https://nvd.nist.gov/vuln/detail/${id}` };
}

function makeDevice(overrides: Partial<DeviceRow> = {}): DeviceRow {
  return {
    id: "device-1",
    user_id: "user-1",
    hostname: null,
    ip: "192.168.1.1",
    open_ports: [],
    os_fingerprint: null,
    ...overrides,
  };
}

describe("matchCveToDevice", () => {
  it("returns null when no ports and no OS match", () => {
    const cve = makeCve("Remote code execution in libpng version 1.6.44");
    const device = makeDevice({ open_ports: [], os_fingerprint: null });
    expect(matchCveToDevice(cve, device)).toBeNull();
  });

  it("matches via SSH port (22) when CVE mentions openssh", () => {
    const cve = makeCve("Critical vulnerability in OpenSSH allows remote code execution");
    const device = makeDevice({ open_ports: [22] });
    const result = matchCveToDevice(cve, device);
    expect(result).not.toBeNull();
    expect(result).toContain("openssh");
  });

  it("matches via SSH port (22) when CVE mentions 'ssh'", () => {
    const cve = makeCve("SSH authentication bypass in multiple products");
    const device = makeDevice({ open_ports: [22] });
    expect(matchCveToDevice(cve, device)).toContain("ssh");
  });

  it("matches via HTTP port (80) when CVE mentions apache", () => {
    const cve = makeCve("Apache HTTP Server path traversal vulnerability");
    const device = makeDevice({ open_ports: [80] });
    const result = matchCveToDevice(cve, device);
    expect(result).not.toBeNull();
    expect(result).toContain("apache");
  });

  it("matches via HTTPS port (443) when CVE mentions openssl", () => {
    const cve = makeCve("OpenSSL TLS handshake buffer overflow CVE-2024-9999");
    const device = makeDevice({ open_ports: [443] });
    const result = matchCveToDevice(cve, device);
    expect(result).not.toBeNull();
    expect(result).toContain("openssl");
  });

  it("matches via MySQL port (3306) when CVE mentions mysql", () => {
    const cve = makeCve("MySQL remote code execution in stored procedure handler");
    const device = makeDevice({ open_ports: [3306] });
    const result = matchCveToDevice(cve, device);
    expect(result).not.toBeNull();
    expect(result).toContain("mysql");
  });

  it("matches via Redis port (6379) when CVE mentions redis", () => {
    const cve = makeCve("Redis heap overflow in RESP3 parser allows RCE");
    const device = makeDevice({ open_ports: [6379] });
    expect(matchCveToDevice(cve, device)).toContain("redis");
  });

  it("matches via RDP port (3389) when CVE mentions remote desktop", () => {
    const cve = makeCve("Windows Remote Desktop Protocol pre-auth use-after-free");
    const device = makeDevice({ open_ports: [3389] });
    const result = matchCveToDevice(cve, device);
    expect(result).not.toBeNull();
    expect(result).toContain("remote desktop");
  });

  it("matches via OS fingerprint when CVE mentions windows", () => {
    const cve = makeCve("Microsoft Windows kernel privilege escalation via win32k.sys");
    const device = makeDevice({ open_ports: [], os_fingerprint: "Windows 11" });
    const result = matchCveToDevice(cve, device);
    expect(result).not.toBeNull();
    expect(result).toContain("windows");
  });

  it("matches via OS fingerprint when CVE mentions linux kernel", () => {
    const cve = makeCve("Linux kernel use-after-free in io_uring subsystem");
    const device = makeDevice({ open_ports: [], os_fingerprint: "Linux 5.15" });
    const result = matchCveToDevice(cve, device);
    expect(result).not.toBeNull();
    expect(result).toContain("linux");
  });

  it("returns null when device has port but CVE doesn't mention any related keyword", () => {
    const cve = makeCve("PHP deserialization remote code execution via getimagesize()");
    const device = makeDevice({ open_ports: [6379], os_fingerprint: "Windows 11" });
    // Redis keyword not in description; windows/microsoft not in description
    expect(matchCveToDevice(cve, device)).toBeNull();
  });

  it("matches via combined port and OS when CVE matches on OS only", () => {
    const cve = makeCve("Apple iOS and macOS arbitrary code execution in CoreGraphics");
    const device = makeDevice({ open_ports: [22], os_fingerprint: "iOS 17" });
    const result = matchCveToDevice(cve, device);
    expect(result).not.toBeNull();
    expect(result).toContain("ios");
  });

  it("handles device with open_ports undefined-ish (empty array)", () => {
    const cve = makeCve("Apache nginx web server reflected XSS");
    const device = makeDevice({ open_ports: [], os_fingerprint: null });
    expect(matchCveToDevice(cve, device)).toBeNull();
  });

  it("returns array of all matched keywords (not just first)", () => {
    const cve = makeCve("nginx apache web server path traversal");
    const device = makeDevice({ open_ports: [80, 443] });
    const result = matchCveToDevice(cve, device);
    // Both nginx and apache appear on ports 80/443
    expect(result).not.toBeNull();
    expect(result!.length).toBeGreaterThan(1);
    expect(result).toContain("nginx");
    expect(result).toContain("apache");
  });
});
