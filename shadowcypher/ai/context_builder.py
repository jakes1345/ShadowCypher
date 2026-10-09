"""Security context builder — injects live network state into AI prompts.

Gathers current Guardian device inventory, active incidents, and CVE alerts,
then formats them as a concise system-prompt prefix so every AI query is
automatically aware of what's on the network and what threats are active.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from shadowcypher.core.logger import logger

if TYPE_CHECKING:
    pass


def _get_guardian_context() -> str:
    """Collect live Guardian state: devices, incidents, CVE alerts."""
    try:
        from shadowcypher.core.guardian_service import GuardianService
        gs = GuardianService()

        devices = gs.get_recent_devices(limit_hours=48)
        incidents = gs.get_incidents(limit=20)
        cve_alerts = gs.get_cve_alerts(limit=10)

        lines: list[str] = []

        # ── Network inventory ─────────────────────────────────────────
        if devices:
            lines.append(f"NETWORK INVENTORY ({len(devices)} devices):")
            for d in devices[:12]:
                ip = d.get("ip", "?")
                host = d.get("hostname") or d.get("host", "")
                dtype = d.get("device_type") or d.get("type", "")
                vendor = d.get("vendor", "")
                risk = d.get("risk", "").upper()
                ports = d.get("open_ports") or d.get("ports", [])
                vulns = d.get("vulnerabilities", 0)

                parts = [ip]
                if host:
                    parts.append(f"({host})")
                attrs = []
                if dtype:
                    attrs.append(dtype)
                if vendor:
                    attrs.append(vendor)
                if risk and risk not in ("", "UNKNOWN"):
                    attrs.append(f"risk={risk}")
                if ports:
                    attrs.append(f"ports={','.join(str(p) for p in ports[:6])}")
                if vulns:
                    attrs.append(f"vulns={vulns}")
                if attrs:
                    parts.append(f"[{' | '.join(attrs)}]")
                lines.append("  " + " ".join(parts))

        # ── Active incidents ──────────────────────────────────────────
        if incidents:
            lines.append(f"\nACTIVE INCIDENTS ({len(incidents)}):")
            for inc in incidents[:8]:
                sev = str(inc.get("severity", "")).upper()
                title = inc.get("title") or inc.get("id", "")
                ack = inc.get("acknowledged", False)
                status = "ACK" if ack else "OPEN"
                lines.append(f"  [{sev}] {title} ({status})")

        # ── CVE alerts ────────────────────────────────────────────────
        if cve_alerts:
            lines.append(f"\nCVE ALERTS ({len(cve_alerts)}):")
            for alert in cve_alerts[:6]:
                cve_id = alert.get("cve_id", "")
                sev = str(alert.get("severity", "")).upper()
                desc = (alert.get("description") or "")[:80]
                affected = alert.get("affected_device", "")
                line = f"  {cve_id}"
                if sev:
                    line += f" [{sev}]"
                if affected:
                    line += f" → {affected}"
                if desc:
                    line += f": {desc}"
                lines.append(line)

        if lines:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            header = f"[LIVE NETWORK STATE — {ts}]"
            return header + "\n" + "\n".join(lines)

    except Exception as e:
        logger.debug("context_builder", f"Guardian context unavailable: {e}")

    return ""


def build_security_context(include_guardian: bool = True) -> str:
    """Build the security context block to prepend to AI system prompts.

    Returns an empty string if no context is available (AI works fine without it).
    """
    parts: list[str] = []

    if include_guardian:
        guardian_ctx = _get_guardian_context()
        if guardian_ctx:
            parts.append(guardian_ctx)

    if not parts:
        return ""

    return "\n\n".join(parts) + "\n\n---\n\n"


def enrich_system_prompt(base_prompt: str, user_query: str = "",
                         include_rag: bool = True) -> str:
    """Prepend live security context (and optionally RAG knowledge) to a system prompt.

    Args:
        base_prompt: The base system/team prompt from prompts.py.
        user_query:  The user's question — used for RAG retrieval.
        include_rag: Whether to query the local security knowledge base.

    Returns:
        Enriched system prompt with live context block at the top.
    """
    ctx = build_security_context()

    enriched = base_prompt
    if ctx:
        enriched = ctx + base_prompt

    if include_rag and user_query:
        try:
            from shadowcypher.ai import rag
            enriched = rag.augment_prompt(user_query, enriched)
        except Exception as e:
            logger.debug("context_builder", f"RAG augmentation skipped: {e}")

    return enriched
