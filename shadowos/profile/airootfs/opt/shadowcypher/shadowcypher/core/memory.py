"""Dream System — Memory consolidation for engagement persistence.

Consolidates project findings, targets, and scan results into a
durable MEMORY.md file. Works with or without AI — raw fallback
writes structured markdown directly.
"""

import os
from datetime import datetime

from shadowcypher.core.logger import logger
from shadowcypher.core.session import session


class DreamSystem:
    """Consolidates project intelligence into persistent MEMORY.md files."""

    @staticmethod
    def dream() -> str:
        """Consolidate current project state into MEMORY.md.
        Returns the path to the memory file, or None on failure."""
        if not session.current_project:
            return None

        p = session.current_project

        logger.info("memory", f"Consolidating memory for: {p.name}")

        # Gather findings
        findings = []
        for f in p.report.findings:
            findings.append(f.to_dict())

        # Try AI-enhanced consolidation first
        memory_md = DreamSystem._ai_consolidate(p, findings)

        # Fall back to structured template
        if not memory_md:
            memory_md = DreamSystem._raw_consolidate(p, findings)

        # Write to disk
        try:
            report_dir = str(p.report.reports_dir)
            os.makedirs(report_dir, exist_ok=True)
            memory_path = os.path.join(report_dir, "MEMORY.md")

            with open(memory_path, "w") as f:
                f.write(memory_md)

            logger.info("memory", f"Memory consolidated: {memory_path}")
            return memory_path

        except Exception as e:
            logger.error("memory", f"Failed to write memory: {e}")
            return None

    @staticmethod
    def _raw_consolidate(project, findings: list[dict]) -> str:
        """Generate structured markdown without AI."""
        now = datetime.now().isoformat()

        lines = [
            "# ShadowCypher Engagement Memory",
            "",
            f"**Project:** {project.name}",
            f"**Last Updated:** {now}",
            f"**Targets:** {', '.join(project.targets) if project.targets else 'None defined'}",
            f"**Scope:** {', '.join(project.scope) if project.scope else 'Unrestricted'}",
            "",
        ]

        # Findings by severity
        if findings:
            lines.append("## Findings")
            lines.append("")

            by_sev = {}
            for f in findings:
                sev = f.get("severity", "Info")
                by_sev.setdefault(sev, []).append(f)

            for sev in ["Critical", "High", "Medium", "Low", "Info"]:
                if sev not in by_sev:
                    continue
                lines.append(f"### {sev}")
                for f in by_sev[sev]:
                    lines.append(f"- **{f.get('title', 'Untitled')}** ({f.get('module', 'unknown')})")
                    if f.get("description"):
                        lines.append(f"  - {f['description'][:200]}")
                    if f.get("evidence"):
                        lines.append(f"  - Evidence: `{f['evidence'][:100]}`")
                    if f.get("target"):
                        lines.append(f"  - Target: {f['target']}")
                lines.append("")
        else:
            lines.append("## Findings")
            lines.append("No findings recorded yet.")
            lines.append("")

        # Roadmap status
        roadmap = getattr(project, 'roadmap', None)
        if roadmap:
            lines.append("## Engagement Roadmap")
            lines.append("")
            for step in roadmap:
                status = step.get("status", "pending")
                marker = "x" if status == "completed" else " "
                lines.append(f"- [{marker}] **{step.get('phase', '?')}**: {step.get('objective', '')}")
            lines.append("")

        # Outstanding tasks
        lines.append("## Next Steps")
        lines.append("")
        if not findings:
            lines.append("- [ ] Run initial reconnaissance against defined targets")
            lines.append("- [ ] Identify live hosts and open services")
        else:
            critical_count = len(by_sev.get("Critical", []))
            high_count = len(by_sev.get("High", []))
            if critical_count > 0 or high_count > 0:
                lines.append(f"- [ ] Prioritize exploitation of {critical_count} critical + {high_count} high findings")
            lines.append("- [ ] Continue enumeration on discovered services")
            lines.append("- [ ] Generate professional report")

        return "\n".join(lines)

    @staticmethod
    def _ai_consolidate(project, findings: list[dict]) -> str:
        """Try AI-enhanced consolidation. Returns None on failure."""
        try:
            from shadowcypher.ai.engine import ai_engine
            if not ai_engine.is_loaded:
                return None

            raw_context = f"""PROJECT: {project.name}
TARGETS: {project.targets}
SCOPE: {project.scope}
FINDINGS: {findings[:20]}"""  # Limit to prevent context overflow

            prompt = f"""Analyze these security engagement results and produce a clean MEMORY.md document.
Include: Identified Targets, Discovered Vulnerabilities, Potential Attack Vectors, Outstanding Tasks.
Format as professional Markdown. Be precise.

{raw_context}"""

            result = ai_engine.generate(
                prompt,
                system_prompt="You are a security engagement analyst. Write concise, accurate Markdown.",
                max_tokens=1500,
            )

            if result and not result.startswith("[Error") and len(result) > 50:
                header = f"# ShadowCypher Engagement Memory\n\n**Last Consolidated:** {datetime.now().isoformat()}\n\n"
                return header + result

        except Exception as e:
            logger.info("memory", f"AI consolidation unavailable: {e}")

        return None

    @staticmethod
    def get_memory() -> str:
        """Read the latest consolidated memory for AI context injection."""
        if not session.current_project:
            return ""

        memory_path = os.path.join(str(session.current_project.report.reports_dir), "MEMORY.md")
        if os.path.exists(memory_path):
            try:
                with open(memory_path, "r") as f:
                    return f.read()
            except Exception:
                return ""
        return ""
