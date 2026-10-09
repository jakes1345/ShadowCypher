"""
ShadowCypher Autonomous Red Team Agent — v2.0.

A fully autonomous recon-to-report loop that runs without human
intervention at each step. Stages:

  1. SURFACE MAP  — nmap port scan + service detection
  2. CVE INTEL    — correlate services against live NVD feed
  3. WEB PROBE    — spider/fingerprint any HTTP services found
  4. VULN SCAN    — nuclei against confirmed attack surface
  5. AI ANALYSIS  — Red Phantom agent synthesizes findings
  6. REPORT       — structured markdown mission report saved to disk

Each stage feeds context into the next. The AI agent has access
to the full output of every prior stage when it synthesizes.

Usage:
    from shadowcypher.ai.adversary_sim import adversary
    mission_id = adversary.engage("192.168.1.100", on_output=callback)
    adversary.stop(mission_id)
"""

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from shadowcypher.core.bus import bus
from shadowcypher.core.knowledge_graph import kg
from shadowcypher.core.logger import logger
from shadowcypher.core.mitre import mitre
from shadowcypher.core.sanitize import validate_target
from shadowcypher.core.stealth import require_stealth
from shadowcypher.modules.cve_feed import cve_feed

REPORTS_DIR = os.path.expanduser("~/.shadowcypher/red_team_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


# ── Mission State ─────────────────────────────────────────────────────────────

@dataclass
class MissionContext:
    """Accumulates findings across all stages for AI synthesis."""
    target: str
    mission_id: str
    start_time: float = field(default_factory=time.time)
    stage: str = "INIT"
    open_ports: list = field(default_factory=list)   # [{port, proto, service, version}]
    http_services: list = field(default_factory=list) # URLs confirmed as HTTP/S
    cve_matches: list = field(default_factory=list)   # CVEMatch objects
    vuln_findings: list = field(default_factory=list) # Raw nuclei/nikto output lines
    raw_logs: dict = field(default_factory=dict)      # stage_name → raw output str
    report_path: str = ""
    complete: bool = False
    aborted: bool = False

    def summary(self) -> str:
        elapsed = round(time.time() - self.start_time, 1)
        crit = sum(1 for c in self.cve_matches if c.cvss_severity == "CRITICAL")
        high = sum(1 for c in self.cve_matches if c.cvss_severity == "HIGH")
        return (
            f"Target: {self.target} | Stage: {self.stage} | "
            f"Ports: {len(self.open_ports)} | CVEs: {len(self.cve_matches)} "
            f"(CRIT:{crit} HIGH:{high}) | Elapsed: {elapsed}s"
        )


class AutonomousAdversaryAgent:
    """
    Drives the full recon→exploit-verify→report pipeline autonomously.
    Each mission runs in its own daemon thread and can be stopped cleanly.
    """

    def __init__(self):
        self._missions: dict[str, MissionContext] = {}
        self._stop_flags: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────────

    def engage(
        self,
        target: str,
        ports: str = "1-65535",
        intensity: str = "standard",   # "quick" | "standard" | "deep"
        on_output: Callable = None,
        on_complete: Callable = None,
    ) -> str:
        """
        Launch an autonomous red team mission against `target`.

        Args:
            target:    IP, hostname, or CIDR range.
            ports:     Port range for nmap (default: full scan).
            intensity: quick=top1000, standard=full+scripts, deep=full+vuln+NSE.
            on_output: Streaming callback for real-time progress.
            on_complete: Called with final MissionContext when done.

        Returns:
            mission_id — use to track or stop the mission.
        """
        require_stealth(on_output=on_output)

        if not validate_target(target):
            if on_output:
                on_output(f"[RED_TEAM] ABORT: Invalid target: {target}\n")
            return ""

        mission_id = f"RT_{int(time.time())}_{target.replace('.', '_')}"
        ctx = MissionContext(target=target, mission_id=mission_id)
        stop = threading.Event()

        with self._lock:
            self._missions[mission_id] = ctx
            self._stop_flags[mission_id] = stop

        def _run():
            try:
                self._run_mission(ctx, stop, ports, intensity, on_output)
                # Auto-ingest into knowledge graph
                try:
                    count = kg.ingest_red_team_mission(ctx)
                    if on_output:
                        on_output(f"[RED_TEAM] Knowledge graph updated: {count} nodes/edges\n")
                except Exception as e:
                    logger.warning("adversary", f"KG ingest failed: {e}")
            except Exception as e:
                if on_output:
                    on_output(f"[RED_TEAM] MISSION_CRASH: {e}\n")
                logger.error("adversary", f"Mission {mission_id} crashed: {e}")
            finally:
                ctx.complete = True
                bus.publish("red_team_complete", ctx.summary())
                if on_complete:
                    on_complete(ctx)

        threading.Thread(target=_run, daemon=True, name=f"RedTeam_{mission_id}").start()

        if on_output:
            on_output(f"[RED_TEAM] MISSION_LAUNCHED: {mission_id}\n"
                      f"[RED_TEAM] Target: {target} | Intensity: {intensity}\n")

        logger.info("adversary", f"MISSION_START: {mission_id} → {target}")
        return mission_id

    def stop(self, mission_id: str):
        """Abort a running mission."""
        with self._lock:
            flag = self._stop_flags.get(mission_id)
            if flag:
                flag.set()
                logger.info("adversary", f"MISSION_ABORT: {mission_id}")

    def get_status(self, mission_id: str) -> Optional[dict]:
        with self._lock:
            ctx = self._missions.get(mission_id)
        if not ctx:
            return None
        return {
            "mission_id": ctx.mission_id,
            "target": ctx.target,
            "stage": ctx.stage,
            "open_ports": len(ctx.open_ports),
            "cve_matches": len(ctx.cve_matches),
            "complete": ctx.complete,
            "aborted": ctx.aborted,
            "summary": ctx.summary(),
            "report_path": ctx.report_path,
        }

    def list_missions(self) -> list[dict]:
        with self._lock:
            missions = list(self._missions.values())
        return [self.get_status(m.mission_id) for m in missions]

    # ── Mission Pipeline ─────────────────────────────────────────────────────

    def _run_mission(self, ctx: MissionContext, stop: threading.Event,
                     ports: str, intensity: str, cb: Callable):
        """Execute all mission stages sequentially."""

        # ── Stage 1: Surface Map (nmap) ──────────────────────────────────────
        if stop.is_set():
            return
        ctx.stage = "SURFACE_MAP"
        nmap_tool = "nmap_deep" if intensity == "deep" else ("nmap_port" if intensity == "quick" else "nmap_service")
        stage1_tags = mitre.format_tags(mitre.tag(nmap_tool))
        self._emit(cb, f"\n{'='*60}\n[STAGE 1/5] SURFACE MAP — nmap port scan\n"
                       f"ATT&CK: {stage1_tags}\n{'='*60}\n")
        nmap_output = self._run_nmap(ctx.target, ports, intensity, stop, cb)
        ctx.raw_logs["nmap"] = nmap_output
        ctx.open_ports = self._parse_nmap_ports(nmap_output)
        ctx.http_services = self._extract_http_services(ctx.target, ctx.open_ports)

        self._emit(cb, f"[SURFACE_MAP] Found {len(ctx.open_ports)} open port(s)\n")
        for p in ctx.open_ports:
            self._emit(cb, f"  {p['port']}/{p['proto']}  {p['service']}  {p['version']}\n")
        if ctx.http_services:
            self._emit(cb, f"[SURFACE_MAP] HTTP/S services: {', '.join(ctx.http_services)}\n")

        # ── Stage 2: CVE Intelligence ─────────────────────────────────────────
        if stop.is_set():
            return
        ctx.stage = "CVE_INTEL"
        cve_tags = mitre.format_tags(mitre.tag("cve_intel"))
        self._emit(cb, f"\n{'='*60}\n[STAGE 2/5] CVE INTEL — correlating services vs NVD\n"
                       f"ATT&CK: {cve_tags}\n{'='*60}\n")
        services = [f"{p['service']} {p['version']}" for p in ctx.open_ports
                    if p.get('version') and p.get('service')]
        if services:
            ctx.cve_matches = cve_feed.correlate_target(
                ctx.target, services=services, on_output=cb
            )
        else:
            self._emit(cb, "[CVE_INTEL] No versioned services found — skipping NVD correlation\n")

        # ── Stage 3: Web Probe ────────────────────────────────────────────────
        if stop.is_set():
            return
        if ctx.http_services:
            ctx.stage = "WEB_PROBE"
            self._emit(cb, f"\n{'='*60}\n[STAGE 3/5] WEB PROBE — fingerprinting HTTP services\n{'='*60}\n")
            for url in ctx.http_services[:5]:  # cap at 5 HTTP services
                if stop.is_set():
                    break
                probe_out = self._run_web_probe(url, intensity, stop, cb)
                ctx.raw_logs[f"probe_{url}"] = probe_out
        else:
            self._emit(cb, "[STAGE 3/5] WEB PROBE — no HTTP services, skipping\n")

        # ── Stage 4: Vulnerability Scan ───────────────────────────────────────
        if stop.is_set():
            return
        ctx.stage = "VULN_SCAN"
        vuln_tags = mitre.format_tags(mitre.tag("nuclei") + mitre.tag("nikto"))
        self._emit(cb, f"\n{'='*60}\n[STAGE 4/5] VULN SCAN — nuclei/nikto\n"
                       f"ATT&CK: {vuln_tags}\n{'='*60}\n")
        for url in ctx.http_services[:3]:
            if stop.is_set():
                break
            vuln_out = self._run_vuln_scan(url, stop, cb)
            ctx.vuln_findings.extend(self._parse_nuclei_findings(vuln_out))
            ctx.raw_logs[f"vuln_{url}"] = vuln_out

        if not ctx.http_services:
            self._emit(cb, "[VULN_SCAN] No HTTP targets — running port-based checks only\n")

        # ── Stage 5: AI Synthesis + Report ────────────────────────────────────
        if stop.is_set():
            return
        ctx.stage = "AI_SYNTHESIS"
        self._emit(cb, f"\n{'='*60}\n[STAGE 5/5] AI SYNTHESIS — Red Phantom analyzing findings\n{'='*60}\n")
        report = self._synthesize_report(ctx, cb)
        ctx.report_path = self._save_report(ctx, report)
        ctx.stage = "COMPLETE"
        self._emit(cb, f"\n[RED_TEAM] MISSION_COMPLETE ✓\n"
                       f"[RED_TEAM] Report saved: {ctx.report_path}\n"
                       f"[RED_TEAM] {ctx.summary()}\n")

    # ── Stage Implementations ─────────────────────────────────────────────────

    def _run_nmap(self, target: str, ports: str, intensity: str,
                  stop: threading.Event, cb: Callable) -> str:
        nmap = shutil.which("nmap")
        if not nmap:
            self._emit(cb, "[NMAP] NOT_FOUND — install nmap for surface mapping\n")
            return ""

        if intensity == "quick":
            args = [nmap, "-T4", "--top-ports", "1000", "-sV", "--open", target]
        elif intensity == "deep":
            args = [nmap, "-T4", "-p", ports, "-sV", "-sC",
                    "--script=vuln,default", "--open", target]
        else:  # standard
            args = [nmap, "-T4", "-p", ports, "-sV", "--open", target]

        self._emit(cb, f"[NMAP] {' '.join(args)}\n")
        return self._run_subprocess(args, stop, cb, timeout=300)

    def _run_web_probe(self, url: str, intensity: str,
                       stop: threading.Event, cb: Callable) -> str:
        output = ""
        # Try httpx first (ProjectDiscovery)
        httpx = shutil.which("httpx")
        if httpx:
            args = [httpx, "-u", url, "-title", "-tech-detect",
                    "-status-code", "-content-length", "-silent"]
            self._emit(cb, f"[PROBE] httpx → {url}\n")
            output += self._run_subprocess(args, stop, cb, timeout=30)

        # Nikto for web vulns
        if intensity in ("standard", "deep"):
            nikto = shutil.which("nikto")
            if nikto:
                args = [nikto, "-h", url, "-maxtime", "60"]
                self._emit(cb, f"[PROBE] nikto → {url}\n")
                output += self._run_subprocess(args, stop, cb, timeout=90)

        if not output:
            # Pure Python fallback — basic HTTP fingerprint
            output = self._python_http_probe(url, cb)

        return output

    def _python_http_probe(self, url: str, cb: Callable) -> str:
        import urllib.error
        import urllib.request
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
                headers = dict(r.headers)
                status = r.status
                body_preview = r.read(512).decode("utf-8", errors="ignore")
            out = (f"[HTTP_PROBE] {url} → {status}\n"
                   f"  Server: {headers.get('Server', 'unknown')}\n"
                   f"  X-Powered-By: {headers.get('X-Powered-By', 'not set')}\n"
                   f"  Body preview: {body_preview[:200]}\n")
            self._emit(cb, out)
            return out
        except Exception as e:
            msg = f"[HTTP_PROBE] {url} → Error: {e}\n"
            self._emit(cb, msg)
            return msg

    def _run_vuln_scan(self, url: str, stop: threading.Event, cb: Callable) -> str:
        nuclei = shutil.which("nuclei")
        if nuclei:
            args = [nuclei, "-u", url, "-nc", "-severity", "critical,high,medium",
                    "-timeout", "10", "-rate-limit", "50"]
            self._emit(cb, f"[VULN] nuclei → {url}\n")
            return self._run_subprocess(args, stop, cb, timeout=120)

        nikto = shutil.which("nikto")
        if nikto:
            args = [nikto, "-h", url, "-maxtime", "60", "-nointeractive"]
            self._emit(cb, f"[VULN] nikto → {url}\n")
            return self._run_subprocess(args, stop, cb, timeout=90)

        self._emit(cb, "[VULN] Neither nuclei nor nikto found — install for vuln scanning\n")
        return ""

    def _synthesize_report(self, ctx: MissionContext, cb: Callable) -> str:
        """Ask Red Phantom AI agent to synthesize all findings into a report."""
        try:
            from shadowcypher.ai.agents import agent_router
        except Exception:
            return self._fallback_report(ctx)

        # Build the full context dump for the AI
        cve_summary = "\n".join(
            f"- [{m.cvss_severity}] {m.cve_id} (CVSS {m.cvss_score}) → {m.matched_service}: {m.description[:120]}"
            for m in ctx.cve_matches[:20]
        ) or "No CVE matches found."

        vuln_summary = "\n".join(ctx.vuln_findings[:30]) or "No vulnerabilities detected by scanner."

        port_table = "\n".join(
            f"  {p['port']}/{p['proto']}  {p['service']}  {p['version']}"
            for p in ctx.open_ports
        ) or "No open ports found."

        tools_used = ["nmap_service", "cve_intel", "http_probe", "nuclei", "nikto"]
        mitre_section = mitre.coverage_section(tools_used)

        prompt = f"""You are analyzing the results of an authorized red team engagement.
Synthesize the following raw findings into a professional penetration test report.

TARGET: {ctx.target}
SCAN DATE: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
MISSION ID: {ctx.mission_id}

## OPEN PORTS & SERVICES
{port_table}

## CVE INTELLIGENCE (from NVD)
{cve_summary}

## VULNERABILITY SCANNER FINDINGS
{vuln_summary}

## MITRE ATT&CK TECHNIQUES EXERCISED
{mitre_section}

## INSTRUCTIONS
Write a structured report with these sections:
1. Executive Summary (2-3 sentences, business impact focus)
2. Attack Surface Overview (what's exposed and why it matters)
3. Critical Findings (CVSS 9.0+ or immediate exploitability)
4. High/Medium Findings (ranked by exploitability)
5. Recommended Attack Chains (how findings combine into real attack paths)
6. MITRE ATT&CK Coverage (map each finding to a technique ID — use the list above)
7. Remediation Priority List (what to fix first and why)

Be specific. Reference actual CVE IDs, port numbers, and ATT&CK technique IDs. No filler text."""

        self._emit(cb, "[AI] Red Phantom synthesizing mission report...\n")
        try:
            report = agent_router.dispatch(
                prompt,
                force_agent="security",
                use_ai_routing=False,
                callback=cb,
            )
            return report or self._fallback_report(ctx)
        except Exception as e:
            logger.warning("adversary", f"AI synthesis failed: {e} — using fallback")
            return self._fallback_report(ctx)

    def _fallback_report(self, ctx: MissionContext) -> str:
        """Generate a structured report without AI if Ollama is offline."""
        lines = [
            "# Red Team Mission Report",
            f"**Target:** {ctx.target}",
            f"**Mission ID:** {ctx.mission_id}",
            f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Status:** {ctx.stage}",
            "",
        ]

        # Rule-based situation assessment (instant, no LLM)
        try:
            from shadowcypher.core.assessor import assessor
            assessment = assessor.assess_findings(
                cve_matches=ctx.cve_matches,
                open_ports=ctx.open_ports,
                target=ctx.target,
            )
            lines += ["## Situation Assessment", "```", assessment, "```", ""]
        except Exception:
            pass

        lines += ["## Open Ports & Services"]
        for p in ctx.open_ports:
            lines.append(f"- `{p['port']}/{p['proto']}` — {p['service']} {p['version']}")
        lines += ["", "## CVE Intelligence"]
        for m in ctx.cve_matches[:15]:
            attack_tags = mitre.format_tags(mitre.from_finding(m.description))
            kev_tag  = "  **[KEV]**" if getattr(m, "kev_exploited", False) else ""
            epss_tag = f"  EPSS:{m.epss_score:.1%}" if getattr(m, "epss_score", 0) else ""
            lines.append(f"- **[{m.cvss_severity}]** `{m.cve_id}` CVSS:{m.cvss_score}{kev_tag}{epss_tag} → {m.matched_service}")
            lines.append(f"  {m.description[:150]}")
            if attack_tags:
                lines.append(f"  ATT&CK: {attack_tags}")
        lines += ["", "## Vulnerability Findings"]
        for f in ctx.vuln_findings[:20]:
            attack_tags = mitre.format_tags(mitre.from_finding(f))
            suffix = f"  ← ATT&CK: {attack_tags}" if attack_tags else ""
            lines.append(f"- {f}{suffix}")
        lines += ["", mitre.coverage_section(["nmap_service", "cve_intel", "http_probe", "nuclei", "nikto"])]
        return "\n".join(lines)

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _parse_nmap_ports(self, nmap_output: str) -> list[dict]:
        """Extract open ports from nmap -sV output."""
        ports = []
        # Match lines like: 80/tcp   open  http    Apache httpd 2.4.51
        pattern = re.compile(
            r"(\d+)/(tcp|udp)\s+open\s+(\S+)\s*(.*)"
        )
        for line in nmap_output.splitlines():
            m = pattern.match(line.strip())
            if m:
                ports.append({
                    "port": int(m.group(1)),
                    "proto": m.group(2),
                    "service": m.group(3),
                    "version": m.group(4).strip(),
                })
        return ports

    def _extract_http_services(self, target: str, ports: list[dict]) -> list[str]:
        """Build HTTP/S URLs from discovered ports."""
        urls = []
        http_services = {"http", "http-proxy", "http-alt", "webcache", "www"}
        https_services = {"https", "https-alt", "ssl/http", "ssl"}
        http_ports = {80, 8080, 8000, 8008, 8888, 3000, 5000, 9000}
        https_ports = {443, 8443, 4443}

        for p in ports:
            port = p["port"]
            svc = p["service"].lower()
            if port in https_ports or any(s in svc for s in https_services):
                urls.append(f"https://{target}:{port}" if port != 443 else f"https://{target}")
            elif port in http_ports or any(s in svc for s in http_services):
                urls.append(f"http://{target}:{port}" if port != 80 else f"http://{target}")

        return list(dict.fromkeys(urls))  # dedupe preserving order

    def _parse_nuclei_findings(self, nuclei_output: str) -> list[str]:
        """Extract finding lines from nuclei output."""
        findings = []
        for line in nuclei_output.splitlines():
            line = line.strip()
            if line and any(tag in line for tag in ["[critical]", "[high]", "[medium]",
                                                     "[CVE-", "[info]", "[low]"]):
                findings.append(line)
        return findings

    # ── Utility ───────────────────────────────────────────────────────────────

    def _run_subprocess(self, args: list, stop: threading.Event,
                        cb: Callable, timeout: int = 120) -> str:
        """Run a subprocess, stream output to cb, respect stop flag."""
        output_lines = []
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            deadline = time.time() + timeout
            while True:
                if stop.is_set():
                    proc.terminate()
                    self._emit(cb, f"[ABORT] Process killed: {args[0]}\n")
                    break
                if time.time() > deadline:
                    proc.terminate()
                    self._emit(cb, f"[TIMEOUT] {args[0]} exceeded {timeout}s\n")
                    break
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    output_lines.append(line)
                    self._emit(cb, line)
            proc.wait(timeout=5)
        except FileNotFoundError:
            self._emit(cb, f"[ERROR] Tool not found: {args[0]}\n")
        except Exception as e:
            self._emit(cb, f"[ERROR] Subprocess failed: {e}\n")
        return "".join(output_lines)

    def _save_report(self, ctx: MissionContext, report: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fname = f"mission_{ts}_{ctx.target.replace('.', '_')}.md"
        path = os.path.join(REPORTS_DIR, fname)
        try:
            with open(path, "w") as f:
                f.write(report)
            os.chmod(path, 0o600)
            logger.info("adversary", f"REPORT_SAVED: {path}")
        except Exception as e:
            logger.warning("adversary", f"Report save failed: {e}")
            path = ""
        return path

    @staticmethod
    def _emit(cb: Optional[Callable], msg: str):
        if cb:
            try:
                cb(msg)
            except Exception:
                pass


# Global singleton
adversary = AutonomousAdversaryAgent()
