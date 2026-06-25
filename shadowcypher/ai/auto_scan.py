"""
AutoScan — Adaptive Security Assessment Pipeline.

Runs an intelligent, results-driven security assessment that branches
based on what it actually finds. Not a static list of tools — each phase
informs the next.

Pipeline:
  1. Nmap service fingerprint  →  parse ports + versions
  2. Route to tools based on what's open:
       Web ports         → Nikto + Nuclei (parallel)
       SQL ports + web   → SQLmap (with confirm gate)
       Any domain        → Subdomain enum
       Services w/ver    → CVE correlation
  3. Threat intel on the IP (always)
  4. Security Assessor  →  instant triage
  5. Ingest everything into Knowledge Graph
  6. AI synthesis of all findings into a final report

Usage:
    from shadowcypher.ai.auto_scan import auto_scan
    result = auto_scan.run("192.168.1.100", on_output=print)

    # With confirmation callback for destructive tools:
    result = auto_scan.run("192.168.1.100",
                           on_output=print,
                           confirm_fn=lambda tool, t: input(f"Run {tool} on {t}? [y/N] ").lower() == 'y')
"""

from __future__ import annotations
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Callable
from shadowcypher.core.logger import logger

# ── Port classification ───────────────────────────────────────────────────────

WEB_PORTS     = {80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 4443, 9090, 9200, 7001, 7443}
DB_PORTS      = {3306, 5432, 1433, 1521, 27017, 5984, 6379, 9042}  # mysql,pg,mssql,oracle,mongo,couch,redis,cassandra
SSH_PORTS     = {22, 2222}
FTP_PORTS     = {21, 990}
SMB_PORTS     = {445, 139}
MAIL_PORTS    = {25, 465, 587, 110, 143, 993, 995}
TELNET_PORTS  = {23}
RDP_PORTS     = {3389}
LDAP_PORTS    = {389, 636}
DNS_PORTS     = {53}

# Services whose banner names suggest web apps even on non-standard ports
WEB_SERVICE_KEYWORDS = {"http", "https", "web", "www", "nginx", "apache", "iis",
                         "tomcat", "jetty", "flask", "django", "express", "spring"}

# DB service banners
DB_SERVICE_KEYWORDS = {"mysql", "postgresql", "mssql", "oracle", "mongodb",
                        "mariadb", "sqlite", "redis", "cassandra"}


# ── Discovery result ──────────────────────────────────────────────────────────

@dataclass
class PortInfo:
    port: int
    proto: str
    service: str
    version: str
    raw: str = ""

    @property
    def is_web(self) -> bool:
        if self.port in WEB_PORTS:
            return True
        return any(kw in self.service.lower() for kw in WEB_SERVICE_KEYWORDS)

    @property
    def is_db(self) -> bool:
        if self.port in DB_PORTS:
            return True
        return any(kw in self.service.lower() for kw in DB_SERVICE_KEYWORDS)

    def url(self, host: str) -> str:
        scheme = "https" if self.port in {443, 8443, 4443} else "http"
        if self.port in {80, 443}:
            return f"{scheme}://{host}"
        return f"{scheme}://{host}:{self.port}"

    def banner(self) -> str:
        return f"{self.service} {self.version}".strip()


@dataclass
class ScanResult:
    target: str
    ports: list[PortInfo] = field(default_factory=list)
    web_urls: list[str] = field(default_factory=list)
    subdomains: list[str] = field(default_factory=list)
    tool_outputs: dict[str, str] = field(default_factory=dict)
    cve_matches: list = field(default_factory=list)
    threat_intel: list = field(default_factory=list)
    assessment: str = ""
    report: str = ""
    duration_s: float = 0.0

    def summary(self) -> str:
        web = [p for p in self.ports if p.is_web]
        db  = [p for p in self.ports if p.is_db]
        return (
            f"Target: {self.target} | "
            f"Ports: {len(self.ports)} open | "
            f"Web: {len(web)} | DB: {len(db)} | "
            f"CVEs: {len(self.cve_matches)} | "
            f"Tools run: {list(self.tool_outputs.keys())}"
        )


# ── Nmap output parser ────────────────────────────────────────────────────────

_NMAP_PORT_RE = re.compile(
    r"(\d+)/(tcp|udp)\s+open\s+(\S+)\s*(.*)"
)

def _parse_nmap(output: str) -> list[PortInfo]:
    ports = []
    for line in output.splitlines():
        m = _NMAP_PORT_RE.match(line.strip())
        if m:
            ports.append(PortInfo(
                port=int(m.group(1)),
                proto=m.group(2),
                service=m.group(3).strip(),
                version=m.group(4).strip(),
                raw=line.strip(),
            ))
    return ports

def _extract_urls_from_nikto(output: str, fallback_url: str = "") -> list[str]:
    """Pull form action URLs and redirect targets from nikto output."""
    urls = []
    for line in output.splitlines():
        # Nikto lines with found URLs: "- /path?param=val"
        m = re.search(r'(https?://[^\s"\'<>]+)', line)
        if m:
            urls.append(m.group(1))
        # Path-only entries
        m2 = re.search(r'"(/[^\s"\']+\?[^\s"\']+)"', line)
        if m2 and fallback_url:
            urls.append(fallback_url.rstrip("/") + m2.group(1))
    return list(dict.fromkeys(urls))[:10]  # dedupe, max 10

def _is_domain(target: str) -> bool:
    return bool(re.match(r"^(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}$", target))


# ── AutoScan ──────────────────────────────────────────────────────────────────

class AutoScan:
    """
    Adaptive security assessment pipeline. Decisions are driven by findings,
    not a predetermined script.
    """

    def __init__(self):
        self._recon    = None
        self._vuln     = None
        self._cve_feed = None
        self._ti       = None

    def _lazy_load(self):
        if self._recon is None:
            from shadowcypher.modules.recon import Recon
            from shadowcypher.modules.vuln_scanner import VulnScanner
            from shadowcypher.modules.cve_feed import cve_feed
            from shadowcypher.modules.threat_intel import threat_intel
            self._recon    = Recon()
            self._vuln     = VulnScanner()
            self._cve_feed = cve_feed
            self._ti       = threat_intel

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(
        self,
        target: str,
        on_output: Callable = None,
        confirm_fn: Callable = None,
        phases: list[str] = None,
    ) -> ScanResult:
        """
        Run the full adaptive assessment pipeline on a target.

        Args:
            target:     IP, hostname, or CIDR range
            on_output:  Streaming output callback (each line as str)
            confirm_fn: fn(tool_name, target) → bool. Called before destructive
                        tools (sqlmap). If None, destructive tools are SKIPPED.
            phases:     Override which phases run. Default: all.
                        Options: ["nmap", "web", "vuln", "sqli", "subdomain",
                                  "cve", "threat_intel", "assess", "report"]
        """
        self._lazy_load()
        phases = set(phases or ["nmap", "web", "vuln", "sqli", "subdomain",
                                 "cve", "threat_intel", "assess", "report"])
        result = ScanResult(target=target)
        t0 = time.time()

        emit = lambda msg: on_output(msg) if on_output else None

        # ShinkaEvolver: use evolved scan configuration
        _evolved_config: dict = {}
        try:
            from shadowcypher.ai.shinka_evolver import shinka_evolver
            _evolved_config = shinka_evolver.best_scan_config()
            emit(f"[EVOLVE] Scan config: {_evolved_config}\n")
        except Exception:
            pass

        emit(f"\n{'='*62}\n")
        emit(f"  AutoScan starting: {target}\n")
        emit(f"{'='*62}\n\n")

        # ── Phase 1: Nmap ────────────────────────────────────────────────────
        if "nmap" in phases:
            emit("[AUTOSCAN] Phase 1/7 — Service Fingerprint (nmap -sV)\n")
            nmap_out = self._run_nmap(target, on_output)
            result.tool_outputs["nmap"] = nmap_out or ""
            result.ports = _parse_nmap(nmap_out or "")
            if result.ports:
                emit(f"[AUTOSCAN] Found {len(result.ports)} open port(s):\n")
                for p in result.ports:
                    tag = " [WEB]" if p.is_web else (" [DB]" if p.is_db else "")
                    emit(f"  {p.port}/{p.proto}  {p.service} {p.version}{tag}\n")
            else:
                emit("[AUTOSCAN] No open ports detected — host may be down or filtered\n")
        else:
            # If nmap skipped, build URLs from target directly
            result.ports = []

        # Derive web URLs from discovered ports
        for p in result.ports:
            if p.is_web:
                result.web_urls.append(p.url(target))

        web_ports  = [p for p in result.ports if p.is_web]
        db_ports   = [p for p in result.ports if p.is_db]
        has_web    = bool(web_ports) or bool(result.web_urls)
        has_db     = bool(db_ports)

        emit(f"\n[AUTOSCAN] Decision matrix:\n")
        emit(f"  Web surface: {'YES (' + ', '.join(p.url(target) for p in web_ports[:3]) + ')' if has_web else 'none'}\n")
        emit(f"  DB exposure: {'YES (' + ', '.join(str(p.port) for p in db_ports) + ')' if has_db else 'none'}\n")
        emit(f"  Domain target: {'YES' if _is_domain(target) else 'no'}\n\n")

        # ── Phase 2: Subdomain enumeration ───────────────────────────────────
        if "subdomain" in phases and _is_domain(target):
            emit("[AUTOSCAN] Phase 2/7 — Subdomain Enumeration\n")
            sub_out = self._collect(lambda cb: self._recon.subdomain_enum(target, on_output=cb))
            result.tool_outputs["subdomain_enum"] = sub_out
            subs = [l.strip() for l in sub_out.splitlines() if l.strip() and not l.startswith("[")]
            result.subdomains = subs
            if subs:
                emit(f"[AUTOSCAN] Discovered {len(subs)} subdomain(s)\n")
        else:
            emit("[AUTOSCAN] Phase 2/7 — Subdomain Enum: skipped (not a domain)\n")

        # ── Phase 3+4: Web scanning (parallel when both apply) ───────────────
        web_threads: list[threading.Thread] = []
        nikto_output_holder: list[str] = [""]
        nuclei_output_holder: list[str] = [""]

        if has_web:
            primary_url = result.web_urls[0] if result.web_urls else f"http://{target}"

            if "web" in phases:
                emit(f"[AUTOSCAN] Phase 3/7 — Nikto web scan → {primary_url}\n")
                def _nikto():
                    out = self._collect(lambda cb: self._vuln.nikto_scan(primary_url, on_output=cb))
                    nikto_output_holder[0] = out
                    result.tool_outputs["nikto"] = out
                t = threading.Thread(target=_nikto, daemon=True, name="AutoScan-Nikto")
                web_threads.append(t)
                t.start()

            if "vuln" in phases:
                emit(f"[AUTOSCAN] Phase 4/7 — Nuclei scan → {primary_url}\n")
                def _nuclei():
                    out = self._collect(lambda cb: self._vuln.nuclei_scan(primary_url, on_output=cb))
                    nuclei_output_holder[0] = out
                    result.tool_outputs["nuclei"] = out
                t = threading.Thread(target=_nuclei, daemon=True, name="AutoScan-Nuclei")
                web_threads.append(t)
                t.start()

            for t in web_threads:
                t.join(timeout=300)

            # Extract SQLi candidate URLs from nikto output
            sqli_urls = _extract_urls_from_nikto(nikto_output_holder[0], primary_url)
            if not sqli_urls and has_web:
                sqli_urls = [primary_url]
        else:
            emit("[AUTOSCAN] Phases 3+4 — Web scans: skipped (no web surface)\n")
            sqli_urls = []

        # ── Phase 5: SQL injection ────────────────────────────────────────────
        if "sqli" in phases and (has_db or sqli_urls):
            sqli_target = sqli_urls[0] if sqli_urls else (f"http://{target}" if has_web else None)
            if sqli_target:
                run_sqli = False
                if confirm_fn is not None:
                    run_sqli = confirm_fn("sqlmap", sqli_target)
                    if not run_sqli:
                        emit(f"[AUTOSCAN] Phase 5/7 — SQLi: operator declined\n")
                else:
                    emit(f"[AUTOSCAN] Phase 5/7 — SQLi: SKIPPED (no confirm_fn provided — call run() with confirm_fn to enable)\n")

                if run_sqli:
                    emit(f"[AUTOSCAN] Phase 5/7 — SQLmap → {sqli_target}\n")
                    out = self._collect(lambda cb: self._vuln.sqlmap_scan(sqli_target, on_output=cb))
                    result.tool_outputs["sqlmap"] = out
            else:
                emit("[AUTOSCAN] Phase 5/7 — SQLi: skipped (no viable URL target)\n")
        else:
            emit("[AUTOSCAN] Phase 5/7 — SQLi: skipped (no web/DB surface or not in phases)\n")

        # ── Phase 6: CVE correlation ──────────────────────────────────────────
        if "cve" in phases and result.ports:
            emit(f"[AUTOSCAN] Phase 6/7 — CVE correlation ({len(result.ports)} services)\n")
            banners = [p.banner() for p in result.ports if p.banner().strip()]
            if banners:
                result.cve_matches = self._cve_feed.correlate_target(
                    target, services=banners, on_output=on_output
                )
        else:
            emit("[AUTOSCAN] Phase 6/7 — CVE: skipped\n")

        # Threat intel (parallel with CVE correlation effectively since it's fast)
        if "threat_intel" in phases:
            emit(f"[AUTOSCAN] Threat intel → {target}\n")
            try:
                ti_result = self._ti.lookup(target, on_output=on_output)
                result.threat_intel = [ti_result]
            except Exception as e:
                emit(f"[AUTOSCAN] Threat intel error: {e}\n")

        # ── Phase 7: Assess + report ──────────────────────────────────────────
        if "assess" in phases:
            emit(f"\n[AUTOSCAN] Phase 7/7 — Security Assessment\n")
            try:
                from shadowcypher.core.assessor import assessor
                result.assessment = assessor.assess_findings(
                    cve_matches=result.cve_matches,
                    threat_results=result.threat_intel,
                    open_ports=[{"port": p.port} for p in result.ports],
                    target=target,
                )
                emit(f"\n{'─'*60}\n{result.assessment}\n{'─'*60}\n")
            except Exception as e:
                emit(f"[AUTOSCAN] Assessment error: {e}\n")

        # Ingest into knowledge graph
        self._ingest_kg(result)

        # AI report synthesis
        if "report" in phases:
            emit("\n[AUTOSCAN] Synthesizing AI report...\n")
            result.report = self._synthesize_report(result, on_output)

        result.duration_s = round(time.time() - t0, 1)
        emit(f"\n[AUTOSCAN] Complete in {result.duration_s}s — {result.summary()}\n")

        # Save structured report files
        saved = self._save_report(result)
        if saved and on_output:
            emit(f"\n[AUTOSCAN] Report saved → {saved.get('text', '')}\n")

        # ShinkaEvolver: record fitness of this scan config
        if _evolved_config:
            try:
                from shadowcypher.ai.shinka_evolver import shinka_evolver
                n_findings = len(result.ports) + len(result.cve_matches)
                fitness = min(1.0, n_findings / 20.0)
                shinka_evolver.record_scan_fitness(_evolved_config, fitness)
            except Exception:
                pass

        # EvoMemory: store scan result summary
        try:
            from shadowcypher.ai.evo_memory import evo_memory
            summary = result.summary() if hasattr(result, "summary") else str(result)[:500]
            evo_memory.add(f"AutoScan {target}: {summary}", source="scan",
                           tags=["scan", target])
        except Exception:
            pass

        return result

    # ── Phase helpers ─────────────────────────────────────────────────────────

    def _run_nmap(self, target: str, on_output: Callable) -> str:
        """Run nmap -sV and return full output."""
        return self._collect(
            lambda cb: self._recon.pulse_target(target, "Service Fingerprint", on_output=cb)
        )

    def _collect(self, fn: Callable) -> str:
        """Run a tool function that accepts on_output callback, collect all output."""
        lines: list[str] = []
        def _cb(line: str):
            lines.append(line)
        try:
            fn(_cb)
        except Exception as e:
            lines.append(f"[ERROR] {e}\n")
        return "".join(lines)

    def _ingest_kg(self, result: ScanResult):
        """Ingest scan result into the knowledge graph."""
        try:
            from shadowcypher.core.knowledge_graph import kg
            kg.add_target(result.target, tags=["autoscan"])
            for p in result.ports:
                svc_id = f"{result.target}:{p.port}/{p.proto}"
                kg.add_service(svc_id, port=p.port, proto=p.proto, version=p.version)
                kg.link(result.target, svc_id, "RUNS")
            for m in result.cve_matches:
                kg.add_cve(m.cve_id, score=m.cvss_score, severity=m.cvss_severity, desc=m.description)
                kg.link(result.target, m.cve_id, "VULNERABLE_TO", weight=m.cvss_score)
            for ti in result.threat_intel:
                kg.ingest_threat_intel(ti)
        except Exception as e:
            logger.warning("auto_scan", f"KG ingestion error: {e}")

    def _save_report(self, result: ScanResult) -> dict:
        """Write HTML, text, and JSON report files via core/reporting.py."""
        try:
            from shadowcypher.core.reporting import Report
            report = Report(project_name="AutoScan", target=result.target)

            # Port info as findings
            for p in result.ports:
                sev = "Info"
                if p.is_db:
                    sev = "Medium"
                if p.port in {445, 23, 21}:  # SMB, telnet, FTP
                    sev = "High"
                report.add_finding(
                    f"Open port: {p.port}/{p.proto} ({p.service})",
                    sev,
                    p.banner() or f"{p.service} on {p.port}",
                )

            # CVE matches
            for m in result.cve_matches:
                report.add_finding(
                    m.cve_id,
                    m.cvss_severity or "Medium",
                    m.description,
                    cvss=m.cvss_score,
                    kev=getattr(m, "kev_exploited", False),
                )

            # Raw tool outputs
            for tool, out in result.tool_outputs.items():
                report.add_raw_output(tool, out)

            # AI report text as raw output too
            if result.report:
                report.add_raw_output("ai_synthesis", result.report)

            return report.save_all()
        except Exception as e:
            logger.warning("auto_scan", f"Report save failed: {e}")
            return {}

    def _synthesize_report(self, result: ScanResult, on_output: Callable) -> str:
        """Ask the AI to synthesize all findings into a structured report."""
        try:
            from shadowcypher.ai.providers import provider_registry
            from shadowcypher.core.mitre import mitre

            # Build context for AI
            port_lines = "\n".join(f"  {p.port}/{p.proto}  {p.service} {p.version}" for p in result.ports[:20])
            cve_lines  = "\n".join(
                f"  {m.cve_id}  CVSS:{m.cvss_score}  [{m.cvss_severity}]"
                + ("  [KEV]" if getattr(m, "kev_exploited", False) else "")
                + f"  EPSS:{getattr(m, 'epss_score', 0):.1%}"
                for m in result.cve_matches[:15]
            )
            ti_lines = "\n".join(
                f"  {r.target}  malicious={r.malicious}  confidence={r.confidence}%  sources={r.sources}"
                for r in result.threat_intel
            )
            tool_summary = "\n".join(
                f"\n### {tool.upper()}\n{output[:1000]}"
                for tool, output in result.tool_outputs.items()
                if tool != "nmap"
            )
            # ATT&CK coverage
            tool_keys = []
            if "nmap" in result.tool_outputs:        tool_keys.append("nmap_service")
            if "nuclei" in result.tool_outputs:      tool_keys.append("nuclei")
            if "nikto" in result.tool_outputs:       tool_keys.append("nikto")
            if "sqlmap" in result.tool_outputs:      tool_keys.append("sqlmap")
            if "cve" in result.tool_outputs:         tool_keys.append("cve_intel")
            attack_coverage = mitre.coverage_section(tool_keys) if tool_keys else ""

            prompt = f"""You are writing a professional security assessment report.
All data below is from REAL tool output — not simulated.

## Target
{result.target}

## Open Ports / Services
{port_lines or '(none found)'}

## CVE Intelligence
{cve_lines or '(none)'}

## Threat Intelligence
{ti_lines or '(none)'}

## Situation Assessment
{result.assessment or '(not run)'}

## Tool Findings
{tool_summary or '(no secondary tools run)'}

## MITRE ATT&CK Coverage
{attack_coverage}

---
Write a concise professional report with these sections:
1. Executive Summary (3-5 sentences, threat level, most critical finding)
2. Critical Findings (bullet list — CVE IDs, EPSS scores, KEV status where relevant)
3. Attack Surface (what's exposed and why it matters)
4. Recommended Actions (numbered, most urgent first)
5. MITRE ATT&CK Summary (techniques detected, relevant tactics)

Be direct. Reference specific CVE IDs, port numbers, and service versions from the data.
Do not repeat raw output verbatim."""

            tokens: list[str] = []
            def _capture(tok: str):
                tokens.append(tok)
                if on_output:
                    on_output(tok)

            provider_registry.generate_stream(
                prompt,
                system_prompt="You are a senior security analyst writing a post-assessment report. Be concise, direct, and specific.",
                max_tokens=2000,
                temperature=0.2,
                on_token=_capture,
            )
            return "".join(tokens)
        except Exception as e:
            logger.warning("auto_scan", f"Report synthesis failed: {e}")
            return result.assessment  # fall back to rule-based assessment

    # ── Convenience shortcuts ─────────────────────────────────────────────────

    def run_async(self, target: str, on_output: Callable = None,
                  on_complete: Callable = None, confirm_fn: Callable = None,
                  phases: list[str] = None):
        """Non-blocking version — returns immediately, result delivered via on_complete."""
        def _worker():
            result = self.run(target, on_output=on_output,
                              confirm_fn=confirm_fn, phases=phases)
            if on_complete:
                on_complete(result)
        threading.Thread(target=_worker, daemon=True,
                         name=f"AutoScan-{target}").start()

    def quick_scan(self, target: str, on_output: Callable = None) -> ScanResult:
        """Fast scan — nmap + threat intel + CVE + assess only. No web/vuln tools."""
        return self.run(target, on_output=on_output,
                        phases=["nmap", "cve", "threat_intel", "assess"])

    def web_scan(self, target: str, on_output: Callable = None,
                 confirm_fn: Callable = None) -> ScanResult:
        """Web-focused scan — nmap + nikto + nuclei + sqli + CVE + assess."""
        return self.run(target, on_output=on_output, confirm_fn=confirm_fn,
                        phases=["nmap", "web", "vuln", "sqli", "cve", "threat_intel", "assess", "report"])


# Global singleton
auto_scan = AutoScan()
