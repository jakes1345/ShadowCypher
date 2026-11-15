/**
 * Networks the assistant is asked about in the evaluation.
 *
 * Each one is the data a real account could hold. Incident categories,
 * severities and titles are the strings the Guardian agent and the API write
 * (agent/shadowcypher_agent.py, src/guardian.ts), and device types are the ones
 * the agent's fingerprinting returns, so models are judged on input shaped
 * like production.
 */

import type { DeviceRow, IncidentRow, ScanRow } from "../assistant";

export interface Scenario {
  devices: DeviceRow[];
  incidents: IncidentRow[];
  scans: ScanRow[];
}

const SEEN = "2026-11-14T09:30:00Z";

function device(
  name: string | null,
  type: string,
  ports: number[],
  trusted: boolean,
  ip: string | null = null,
  mac = "02:00:00:00:00:00",
): DeviceRow {
  return { mac, ip, hostname: name, vendor: null, device_type: type, open_ports: ports, last_seen_at: SEEN, trusted };
}

function incident(severity: string, category: string, title: string, acknowledged = false): IncidentRow {
  return { severity, category, title, created_at: "2026-11-14T09:12:00Z", acknowledged };
}

function scan(type: string, count: number | null): ScanRow {
  return { scan_type: type, device_count: count, started_at: "2026-11-14T09:00:00Z" };
}

export const SCENARIOS = {
  /** A new account: the agent has never run. */
  no_agent: { devices: [], incidents: [], scans: [] },

  /** A healthy home network with nothing to report. */
  quiet_home: {
    devices: [
      device("fritzbox", "router", [53, 80, 443], true),
      device("anna-laptop", "pc", [], true),
      device("pixel-8", "phone", [], true),
      device("living-room-tv", "tv", [8008, 8009], true),
      device("hue-bridge", "iot", [80, 443], true),
      device("printer-hp", "unknown", [80, 443, 631, 9100], true),
    ],
    incidents: [],
    scans: [scan("network", 6), scan("router", 1), scan("arp", 6)],
  },

  /** An unnamed device has just appeared. */
  new_device: {
    devices: [
      device("archer-ax55", "router", [53, 80, 443], true),
      device("desk-pc", "pc", [22], true),
      device("iphone-maya", "phone", [62078], true),
      device(null, "unknown", [], false, "192.168.1.87", "3c:22:fb:9a:10:4e"),
    ],
    incidents: [incident("info", "new_device", "New device on network: 192.168.1.87")],
    scans: [scan("network", 4)],
  },

  /** The agent's ARP check has fired. */
  arp_alert: {
    devices: [
      device("home-gw", "router", [53, 80, 443], true),
      device("work-laptop", "pc", [], true),
      device("galaxy-s23", "phone", [], true),
      device(null, "unknown", [80], false, "192.168.0.44", "9e:41:07:c2:5b:d0"),
    ],
    incidents: [incident("critical", "arp_spoof", "Possible ARP anomaly: duplicate_mac")],
    scans: [scan("arp", 4), scan("network", 4)],
  },

  /** The router audit found management services exposed. */
  router_exposed: {
    devices: [
      device("tplink-router", "router", [23, 53, 80, 1900, 7547], true),
      device("office-pc", "pc", [], true),
      device("oneplus-12", "phone", [], true),
    ],
    incidents: [
      incident("critical", "router_exposure", "Router exposes Telnet (port 23)"),
      incident("critical", "router_exposure", "Router exposes TR-069 (port 7547)"),
      incident("warning", "router_exposure", "Router exposes UPnP (port 1900)"),
    ],
    scans: [scan("router", 1), scan("network", 3)],
  },

  /** DNS and firewall checks on the machine running the agent. */
  dns_firewall: {
    devices: [
      device("ax3000", "router", [53, 80, 443], true),
      device("thinkpad-t14", "pc", [22], true),
      device("ipad-kids", "phone", [], true),
    ],
    incidents: [
      incident("warning", "dns_leak", "DNS leak detected — 2 unexpected resolver(s)"),
      incident("warning", "firewall_disabled", "No active firewall detected on this machine"),
    ],
    scans: [scan("dns", null), scan("firewall", null), scan("network", 3)],
  },

  /** Hardening findings from a Linux machine. */
  linux_hardening: {
    devices: [
      device("edge-router", "router", [53, 80, 443], true),
      device("ubuntu-server", "pc", [22, 80], true),
      device("macbook-air", "pc", [], true),
    ],
    incidents: [
      incident("critical", "hardening", "SSH allows root login"),
      incident("warning", "hardening", "SSH allows password auth (prefer keys)"),
      incident("warning", "hardening", "Core dumps enabled (limit: unlimited)"),
    ],
    scans: [scan("audit", null), scan("network", 3)],
  },

  /** Hardening findings from Windows and macOS machines. */
  endpoints: {
    devices: [
      device("nighthawk", "router", [53, 80, 443], true),
      device("win11-desktop", "pc", [135, 445], true),
      device("macbook-pro", "pc", [], true),
    ],
    incidents: [
      incident("critical", "hardening", "Windows Defender real-time protection is disabled"),
      incident("warning", "hardening", "BitLocker not enabled on system drive (C:)"),
      incident("warning", "hardening", "FileVault disk encryption is not enabled"),
      incident("warning", "hardening", "Gatekeeper is disabled — unsigned apps can run"),
    ],
    scans: [scan("audit", null), scan("network", 3)],
  },

  /** A small office with a mix of devices and incidents. */
  small_office: {
    devices: [
      device("ubnt-gateway", "router", [53, 80, 443], true),
      device("synology-nas", "pc", [139, 445, 5000, 5001], true),
      device("rdp-server", "pc", [135, 445, 3389], true),
      device("cam-front-door", "iot", [80, 554], false),
      device("reception-pc", "pc", [], true),
      device("accounts-pc", "pc", [], true),
      device("brother-mfc", "unknown", [80, 515, 631, 9100], true),
      device("iphone-sam", "phone", [62078], true),
      device("pixel-7a", "phone", [], true),
      device("meeting-room-tv", "tv", [8008, 8009], true),
      device(null, "unknown", [], false, "10.0.0.143", "b8:27:eb:5d:11:9a"),
      device("echo-kitchen", "iot", [], true),
    ],
    incidents: [
      incident("warning", "router_exposure", "Router exposes HTTP-alt (port 8080)"),
      incident("info", "new_device", "New device on network: 10.0.0.143"),
      incident("info", "new_device", "New device on network: cam-front-door", true),
    ],
    scans: [scan("network", 12), scan("router", 1), scan("arp", 12)],
  },
} satisfies Record<string, Scenario>;

export type ScenarioId = keyof typeof SCENARIOS;
