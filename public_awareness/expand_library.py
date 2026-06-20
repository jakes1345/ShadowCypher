#!/usr/bin/env python3
"""Merge extra threat briefings into library.json. Run after editing threats_extra.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARY = ROOT / "library.json"
EXTRA = ROOT / "threats_extra.json"


def main() -> None:
    base = json.loads(LIBRARY.read_text(encoding="utf-8"))
    extra = json.loads(EXTRA.read_text(encoding="utf-8"))
    seen = {t["id"] for t in base.get("threats", [])}
    for t in extra.get("threats", []):
        if t["id"] in seen:
            for i, existing in enumerate(base["threats"]):
                if existing["id"] == t["id"]:
                    base["threats"][i] = t
                    break
        else:
            base["threats"].append(t)
            seen.add(t["id"])
    # Normalize stale references
    for t in base["threats"]:
        t["related_tools"] = [
            x.replace("Threat Briefing", "Public Awareness app")
            for x in t.get("related_tools", [])
        ]
    base["updated"] = extra.get("updated", base.get("updated"))
    base["mission"] = (
        "Make real-world scams visible — including modern AI-enabled fraud — "
        "so people can defend themselves and warn others."
    )
    base["threats"].sort(key=lambda x: (x.get("category", ""), x.get("title", "")))
    LIBRARY.write_text(json.dumps(base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"library.json: {len(base['threats'])} threats")


if __name__ == "__main__":
    main()
