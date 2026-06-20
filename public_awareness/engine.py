"""Threat briefing engine — standalone, no ShadowCypher app imports."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_PACKAGE_DIR = Path(__file__).resolve().parent
_DEFAULT_LIBRARY = _PACKAGE_DIR / "library.json"


@dataclass(frozen=True)
class ThreatBrief:
    id: str
    title: str
    severity: str
    category: str
    tags: list[str]
    summary: str
    how_it_works: list[str]
    real_world: list[str]
    red_flags: list[str]
    what_to_do: list[str]
    tell_others: str
    mitre: list[str]
    related_tools: list[str]

    @classmethod
    def from_dict(cls, d: dict) -> ThreatBrief:
        return cls(
            id=d["id"],
            title=d["title"],
            severity=d.get("severity", "medium"),
            category=d.get("category", "general"),
            tags=list(d.get("tags") or []),
            summary=d.get("summary", ""),
            how_it_works=list(d.get("how_it_works") or []),
            real_world=list(d.get("real_world") or []),
            red_flags=list(d.get("red_flags") or []),
            what_to_do=list(d.get("what_to_do") or []),
            tell_others=d.get("tell_others", ""),
            mitre=list(d.get("mitre") or []),
            related_tools=list(d.get("related_tools") or []),
        )


class ThreatBriefingEngine:
    """Load and present the public threat-awareness library."""

    _cache: dict | None = None
    _library_path: Path | None = None

    @classmethod
    def library_path(cls) -> Path:
        if cls._library_path is not None:
            return cls._library_path
        env = os.environ.get("PUBLIC_AWARENESS_LIBRARY")
        if env:
            return Path(env).expanduser().resolve()
        return _DEFAULT_LIBRARY

    @classmethod
    def set_library_path(cls, path: str | Path | None) -> None:
        cls._library_path = Path(path).expanduser().resolve() if path else None
        cls._cache = None

    @classmethod
    def load(cls) -> dict:
        if cls._cache is not None:
            return cls._cache
        path = cls.library_path()
        if not path.is_file():
            cls._cache = {"threats": [], "updated": None, "mission": ""}
            return cls._cache
        with open(path, encoding="utf-8") as f:
            cls._cache = json.load(f)
        return cls._cache

    @classmethod
    def reload(cls) -> dict:
        cls._cache = None
        return cls.load()

    @classmethod
    def list_threats(cls, category: str | None = None) -> list[ThreatBrief]:
        data = cls.load()
        out: list[ThreatBrief] = []
        for item in data.get("threats") or []:
            brief = ThreatBrief.from_dict(item)
            if category and brief.category != category:
                continue
            out.append(brief)
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        out.sort(key=lambda t: (order.get(t.severity, 9), t.title))
        return out

    @classmethod
    def get(cls, threat_id: str) -> ThreatBrief | None:
        for t in cls.list_threats():
            if t.id == threat_id:
                return t
        return None

    @classmethod
    def search(cls, query: str) -> list[ThreatBrief]:
        q = query.lower().strip()
        if not q:
            return cls.list_threats()
        hits: list[ThreatBrief] = []
        for t in cls.list_threats():
            blob = " ".join(
                [t.title, t.summary, t.category, " ".join(t.tags), t.tell_others]
            ).lower()
            if q in blob:
                hits.append(t)
        return hits

    @classmethod
    def categories(cls) -> list[str]:
        cats = {t.category for t in cls.list_threats()}
        return sorted(cats)

    @classmethod
    def format_brief(cls, threat: ThreatBrief) -> str:
        lines = [
            f"# {threat.title}",
            f"Severity: {threat.severity.upper()} | Category: {threat.category}",
            "",
            threat.summary,
            "",
            "## How it works",
            *[f"- {x}" for x in threat.how_it_works],
            "",
            "## Real-world examples",
            *[f"- {x}" for x in threat.real_world],
            "",
            "## Red flags",
            *[f"- {x}" for x in threat.red_flags],
            "",
            "## What to do",
            *[f"- {x}" for x in threat.what_to_do],
            "",
            "## Tell family & friends",
            threat.tell_others,
            "",
            f"MITRE ATT&CK: {', '.join(threat.mitre) or '—'}",
            f"Related tools: {', '.join(threat.related_tools) or '—'}",
        ]
        return "\n".join(lines)

    @classmethod
    def family_playbook(cls) -> str:
        lines = [
            "SHADOWCYPHER — FAMILY SCAM DEFENSE (share freely)",
            "=" * 50,
            "",
            "1. QR codes in email or on stickers → don't scan for banking or login.",
            "2. Never give 2FA codes to anyone who called or texted you.",
            "3. Google/Apple/bank links → type the site yourself; don't use email links.",
            "4. Phone lost service suddenly → call carrier fraud line (SIM swap).",
            "5. Package/toll texts → delete; track only on official apps.",
            "6. 'Move money to safe account' → hang up; call number on your card.",
            "7. Virus pop-up with phone number → force-quit browser; don't call.",
            "8. Social DMs about deals/verification → only change settings inside the app.",
            "",
            "Full briefings: python3 -m public_awareness",
            "",
        ]
        for t in cls.list_threats():
            lines.append(f"• {t.title}: {t.tell_others}")
            lines.append("")
        return "\n".join(lines)

    @classmethod
    def export_markdown(cls, path: str | Path, on_output: Callable[[str], None] | None = None) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        chunks = [cls.family_playbook(), "\n\n---\n\n"]
        for t in cls.list_threats():
            chunks.append(cls.format_brief(t))
            chunks.append("\n\n---\n\n")
        text = "\n".join(chunks)
        path.write_text(text, encoding="utf-8")
        msg = f"Exported {len(cls.list_threats())} briefings → {path}"
        if on_output:
            on_output(msg)
        return msg
