"""Reporting engine — generates real HTML/text reports from scan results."""

import os
import json
import html
from datetime import datetime
from pathlib import Path
from typing import Optional

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


class Finding:
    """A single security finding."""

    SEVERITY_LEVELS = ["Critical", "High", "Medium", "Low", "Info"]

    def __init__(self, title: str, severity: str, description: str,
                 evidence: str = "", remediation: str = "",
                 module: str = "", target: str = ""):
        self.title = title
        self.severity = severity if severity in self.SEVERITY_LEVELS else "Info"
        self.description = description
        self.evidence = evidence
        self.remediation = remediation
        self.module = module
        self.target = target
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "module": self.module,
            "target": self.target,
            "timestamp": self.timestamp,
        }


class Report:
    """Collects findings and generates reports."""

    def __init__(self, project_name: str = "ShadowCypher Assessment",
                 target: str = "", scope: str = ""):
        self.project_name = project_name
        self.target = target
        self.scope = scope
        self.findings: list[Finding] = []
        self.raw_outputs: dict[str, str] = {}  # module_name -> raw output
        self.created = datetime.now()
        self.reports_dir = Path(config.project_root) / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    def add_finding(self, title: str, severity: str, description: str, **kwargs):
        """Add a finding to the report."""
        f = Finding(title, severity, description, **kwargs)
        self.findings.append(f)
        return f

    def add_raw_output(self, module: str, output: str):
        """Store raw command output for inclusion in report."""
        self.raw_outputs[module] = output

    def _severity_count(self) -> dict:
        counts = {s: 0 for s in Finding.SEVERITY_LEVELS}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts

    def _severity_color(self, severity: str) -> str:
        return {
            "Critical": "#ff0040",
            "High": "#ff4444",
            "Medium": "#ff8800",
            "Low": "#ffcc00",
            "Info": "#00aaff",
        }.get(severity, "#888888")

    # ──────────────────────────────────────────────────────────────────
    # Text report
    # ──────────────────────────────────────────────────────────────────

    def generate_text(self, filepath: str = None) -> str:
        """Generate a plain text report."""
        if filepath is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.reports_dir / f"report_{ts}.txt")

        counts = self._severity_count()
        lines = [
            "=" * 70,
            f"  SHADOWCYPHER SECURITY ASSESSMENT REPORT",
            f"  Project: {self.project_name}",
            f"  Target:  {self.target}",
            f"  Scope:   {self.scope}",
            f"  Date:    {self.created.strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 70,
            "",
            "EXECUTIVE SUMMARY",
            "-" * 40,
            f"Total findings: {len(self.findings)}",
        ]
        for sev in Finding.SEVERITY_LEVELS:
            if counts[sev] > 0:
                lines.append(f"  {sev}: {counts[sev]}")
        lines.append("")

        # Findings
        lines.append("DETAILED FINDINGS")
        lines.append("-" * 40)
        for i, f in enumerate(self.findings, 1):
            lines.append(f"\n[{f.severity.upper()}] Finding #{i}: {f.title}")
            lines.append(f"  Module:      {f.module}")
            lines.append(f"  Target:      {f.target}")
            lines.append(f"  Timestamp:   {f.timestamp}")
            lines.append(f"  Description: {f.description}")
            if f.evidence:
                lines.append(f"  Evidence:")
                for eline in f.evidence.split("\n"):
                    lines.append(f"    {eline}")
            if f.remediation:
                lines.append(f"  Remediation: {f.remediation}")

        # Raw outputs
        if self.raw_outputs:
            lines.append("\n" + "=" * 70)
            lines.append("RAW TOOL OUTPUT")
            lines.append("=" * 70)
            for module, output in self.raw_outputs.items():
                lines.append(f"\n--- {module} ---")
                lines.append(output)

        lines.append("\n" + "=" * 70)
        lines.append("END OF REPORT")
        lines.append("=" * 70)

        report_text = "\n".join(lines)
        with open(filepath, "w") as f:
            f.write(report_text)
        logger.info("report", f"Text report saved: {filepath}")
        return filepath

    # ──────────────────────────────────────────────────────────────────
    # HTML report
    # ──────────────────────────────────────────────────────────────────

    def generate_html(self, filepath: str = None) -> str:
        """Generate an HTML report."""
        if filepath is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.reports_dir / f"report_{ts}.html")

        counts = self._severity_count()

        findings_html = ""
        for i, f in enumerate(self.findings, 1):
            color = self._severity_color(f.severity)
            evidence_block = ""
            if f.evidence:
                evidence_block = f'<div class="evidence"><strong>Evidence:</strong><pre>{html.escape(f.evidence)}</pre></div>'
            remediation_block = ""
            if f.remediation:
                remediation_block = f'<div class="remediation"><strong>Remediation:</strong><p>{html.escape(f.remediation)}</p></div>'

            findings_html += f"""
            <div class="finding">
                <div class="finding-header">
                    <span class="severity" style="background:{color};">{f.severity.upper()}</span>
                    <span class="finding-title">#{i} — {html.escape(f.title)}</span>
                </div>
                <div class="finding-meta">
                    <span>Module: {html.escape(f.module)}</span>
                    <span>Target: {html.escape(f.target)}</span>
                    <span>Time: {f.timestamp}</span>
                </div>
                <p>{html.escape(f.description)}</p>
                {evidence_block}
                {remediation_block}
            </div>
            """

        raw_html = ""
        if self.raw_outputs:
            for module, output in self.raw_outputs.items():
                raw_html += f"""
                <div class="raw-output">
                    <h3>{html.escape(module)}</h3>
                    <pre>{html.escape(output)}</pre>
                </div>
                """

        summary_bars = ""
        for sev in Finding.SEVERITY_LEVELS:
            if counts[sev] > 0:
                color = self._severity_color(sev)
                summary_bars += f'<div class="summary-item"><span class="dot" style="background:{color};"></span>{sev}: {counts[sev]}</div>'

        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ShadowCypher Report — {html.escape(self.project_name)}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 40px; }}
    .header {{ border-bottom: 2px solid #00ff41; padding-bottom: 20px; margin-bottom: 30px; }}
    .header h1 {{ color: #00ff41; font-size: 28px; }}
    .header .meta {{ color: #888; margin-top: 8px; }}
    .summary {{ display: flex; gap: 20px; margin-bottom: 30px; padding: 20px; background: #111; border-radius: 8px; border: 1px solid #222; }}
    .summary-item {{ display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: bold; }}
    .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
    .finding {{ background: #111; border: 1px solid #222; border-radius: 8px; padding: 20px; margin-bottom: 16px; }}
    .finding-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
    .severity {{ padding: 4px 12px; border-radius: 4px; color: #fff; font-weight: bold; font-size: 12px; text-transform: uppercase; }}
    .finding-title {{ font-size: 18px; font-weight: bold; }}
    .finding-meta {{ display: flex; gap: 20px; color: #666; font-size: 13px; margin-bottom: 12px; }}
    .evidence pre {{ background: #0a0a0a; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 13px; margin-top: 8px; color: #00ff41; }}
    .remediation {{ margin-top: 12px; padding: 12px; background: #0a1a0a; border-left: 3px solid #00ff41; }}
    .raw-output {{ margin-top: 20px; }}
    .raw-output pre {{ background: #0a0a0a; padding: 16px; border-radius: 4px; overflow-x: auto; font-size: 12px; color: #ccc; max-height: 400px; overflow-y: auto; }}
    h2 {{ color: #00ff41; margin: 30px 0 15px; }}
    h3 {{ color: #00aaff; margin: 15px 0 10px; }}
</style>
</head>
<body>
<div class="header">
    <h1>&#x26a1; ShadowCypher Security Assessment</h1>
    <div class="meta">
        <div>Project: {html.escape(self.project_name)}</div>
        <div>Target: {html.escape(self.target)}</div>
        <div>Scope: {html.escape(self.scope)}</div>
        <div>Generated: {self.created.strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
</div>

<h2>Executive Summary</h2>
<div class="summary">
    <div class="summary-item"><strong>Total: {len(self.findings)}</strong></div>
    {summary_bars}
</div>

<h2>Findings</h2>
{findings_html if findings_html else '<p>No findings recorded.</p>'}

{"<h2>Raw Tool Output</h2>" + raw_html if raw_html else ""}

<div style="margin-top:40px;border-top:1px solid #222;padding-top:20px;color:#444;text-align:center;">
    Generated by ShadowCypher Security Suite
</div>
</body>
</html>"""

        with open(filepath, "w") as f:
            f.write(page_html)
        logger.info("report", f"HTML report saved: {filepath}")
        return filepath

    # ──────────────────────────────────────────────────────────────────
    # JSON export
    # ──────────────────────────────────────────────────────────────────

    def generate_json(self, filepath: str = None) -> str:
        """Export findings as JSON."""
        if filepath is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.reports_dir / f"report_{ts}.json")

        data = {
            "project": self.project_name,
            "target": self.target,
            "scope": self.scope,
            "created": self.created.isoformat(),
            "summary": self._severity_count(),
            "total_findings": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("report", f"JSON report saved: {filepath}")
        return filepath

    def save_all(self) -> dict:
        """Generate all report formats and return paths."""
        return {
            "text": self.generate_text(),
            "html": self.generate_html(),
            "json": self.generate_json(),
        }
